"""Matrix-styled Chat Interface with rich Markdown rendering"""
import customtkinter as ctk
from typing import List, Optional, Callable
from datetime import datetime
from pathlib import Path
import re
import tkinter as tk

# Optional clipboard support
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

from .theme import COLORS, DECORATIONS, RADIUS
from .widgets import (
    MatrixFrame, MatrixScrollableFrame, MatrixButton,
    MatrixTextbox, MatrixLabel, TerminalHeader, MatrixTooltip
)
from ..utils.logger import get_logger
log = get_logger("chat_panel")

# Max messages to send to the API (sliding window)
MAX_CONTEXT_MESSAGES = 40  # 20 user/assistant pairs

# Max visible message widgets before oldest are destroyed (memory cap).
# The full message *data* list is always kept for saving/export.
MAX_VISIBLE_WIDGETS = 100

# Input textbox height limits
INPUT_MIN_HEIGHT = 44
INPUT_MAX_HEIGHT = 160
INPUT_LINE_HEIGHT = 20


# ── Markdown parser ────────────────────────────────────────────────
# Produces a list of "segments" that the RichMessageContent widget
# renders with appropriate formatting.  Each segment is a dict:
#   {"type": "text"|"bold"|"code"|"codeblock"|"header"|"bullet"|"numbered",
#    "text": str, "lang": str (for codeblock)}

def parse_markdown_segments(text: str) -> list:
    """Parse markdown text into styled segments for rich rendering."""
    segments = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Code block (``` ... ```)
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # skip closing ```
            segments.append({
                "type": "codeblock",
                "text": "\n".join(code_lines),
                "lang": lang or ""
            })
            continue

        # Header (# ... )
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if header_match:
            level = len(header_match.group(1))
            segments.append({
                "type": "header",
                "text": header_match.group(2),
                "level": level
            })
            i += 1
            continue

        # Bullet list
        bullet_match = re.match(r'^(\s*)[-*]\s+(.+)$', line)
        if bullet_match:
            segments.append({
                "type": "bullet",
                "text": bullet_match.group(2),
                "indent": len(bullet_match.group(1))
            })
            i += 1
            continue

        # Numbered list
        num_match = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
        if num_match:
            segments.append({
                "type": "numbered",
                "text": num_match.group(2),
                "indent": len(num_match.group(1))
            })
            i += 1
            continue

        # Regular text line (may contain inline formatting)
        if line.strip():
            segments.append({"type": "text", "text": line})
        else:
            segments.append({"type": "text", "text": ""})

        i += 1

    return segments


def parse_markdown_simple(text: str) -> str:
    """Fallback: convert markdown to plain text with visual indicators"""
    text = re.sub(r'```[\w]*\n?(.*?)```', r'[\1]', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'[\1]', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'\1', text)
    text = re.sub(r'^#{1,6}\s*(.+)$', r'>>> \1', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*]\s+', '  \u2022 ', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '  \u2192 ', text, flags=re.MULTILINE)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    return text.strip()


# ── Rich message content widget ────────────────────────────────────

class RichMessageContent(ctk.CTkFrame):
    """Renders markdown segments as styled widgets inside a frame.
    Uses CTkTextbox in disabled state for code blocks with a distinct
    background, CTkLabel for text with bold/normal formatting, etc."""

    def __init__(self, parent, content: str, text_color: str, is_user: bool = False, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._text_color = text_color
        self._is_user = is_user
        self._widgets = []
        self._content = content

        if is_user:
            # User messages: plain text, no markdown parsing
            self._render_plain(content)
        else:
            self._render_rich(content)

    def _render_plain(self, content: str):
        """Render as plain text label."""
        lbl = ctk.CTkLabel(
            self,
            text=content,
            font=ctk.CTkFont(family="Consolas", size=14),
            text_color=self._text_color,
            anchor="nw",
            justify="left",
            wraplength=1,
        )
        lbl.grid(row=0, column=0, sticky="ew")
        self._widgets.append(lbl)
        self._setup_wrap(lbl)

    def _render_rich(self, content: str):
        """Render markdown segments as individual widgets."""
        segments = parse_markdown_segments(content)
        row = 0
        for seg in segments:
            stype = seg["type"]

            if stype == "codeblock":
                w = self._make_codeblock(seg["text"], seg.get("lang", ""))
                w.grid(row=row, column=0, sticky="ew", pady=(4, 4))
                self._widgets.append(w)
                row += 1

            elif stype == "header":
                level = seg.get("level", 1)
                size = max(14, 22 - (level * 2))
                lbl = ctk.CTkLabel(
                    self,
                    text=seg["text"],
                    font=ctk.CTkFont(family="Consolas", size=size, weight="bold"),
                    text_color=COLORS["matrix_green_bright"],
                    anchor="nw",
                    justify="left",
                    wraplength=1,
                )
                lbl.grid(row=row, column=0, sticky="ew", pady=(6, 2))
                self._widgets.append(lbl)
                self._setup_wrap(lbl)
                row += 1

            elif stype == "bullet":
                indent = seg.get("indent", 0) // 2
                prefix = "  " * indent + "\u2022 "
                lbl = self._make_inline_label(prefix + seg["text"])
                lbl.grid(row=row, column=0, sticky="ew", pady=(1, 1))
                self._widgets.append(lbl)
                row += 1

            elif stype == "numbered":
                indent = seg.get("indent", 0) // 2
                prefix = "  " * indent + "\u2192 "
                lbl = self._make_inline_label(prefix + seg["text"])
                lbl.grid(row=row, column=0, sticky="ew", pady=(1, 1))
                self._widgets.append(lbl)
                row += 1

            elif stype == "text":
                if not seg["text"]:
                    # Empty line spacer
                    spacer = ctk.CTkFrame(self, fg_color="transparent", height=6)
                    spacer.grid(row=row, column=0, sticky="ew")
                    self._widgets.append(spacer)
                    row += 1
                else:
                    lbl = self._make_inline_label(seg["text"])
                    lbl.grid(row=row, column=0, sticky="ew", pady=(1, 1))
                    self._widgets.append(lbl)
                    row += 1

    def _make_inline_label(self, text: str) -> ctk.CTkLabel:
        """Create a label that handles inline bold and code styling.
        Since CTkLabel doesn't support mixed fonts, we use text markers
        and render the full text with the dominant style."""
        # Strip inline markdown for display in CTkLabel
        clean = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        clean = re.sub(r'`([^`]+)`', r'\1', clean)
        # Remove link markdown
        clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
        # Remove italic markdown
        clean = re.sub(r'\*([^*]+)\*', r'\1', clean)
        clean = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'\1', clean)

        # Detect if the line is mostly bold
        has_bold = "**" in text
        weight = "bold" if has_bold else "normal"

        lbl = ctk.CTkLabel(
            self,
            text=clean,
            font=ctk.CTkFont(family="Consolas", size=14, weight=weight),
            text_color=self._text_color,
            anchor="nw",
            justify="left",
            wraplength=1,
        )
        self._setup_wrap(lbl)
        return lbl

    def _make_codeblock(self, code: str, lang: str) -> ctk.CTkFrame:
        """Create a styled code block with dark background."""
        frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_code"],
            border_color=COLORS["border_code"],
            border_width=1,
            corner_radius=4,
        )
        frame.grid_columnconfigure(0, weight=1)

        # Language label + copy button header
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 0))
        header.grid_columnconfigure(0, weight=1)

        lang_text = lang.upper() if lang else "CODE"
        ctk.CTkLabel(
            header,
            text=lang_text,
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        copy_btn = ctk.CTkButton(
            header,
            text="COPY",
            font=ctk.CTkFont(family="Consolas", size=9),
            width=40,
            height=18,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["border_code"],
            border_width=1,
            text_color=COLORS["text_muted"],
            command=lambda: None,
        )
        copy_btn.grid(row=0, column=1, sticky="e")
        # Wire up with reference to self
        copy_btn.configure(command=lambda c=code, b=copy_btn: self._copy_code(c, b))

        # Code content
        code_tb = ctk.CTkTextbox(
            frame,
            fg_color=COLORS["bg_code"],
            text_color=COLORS["matrix_green_dim"],
            border_width=0,
            font=ctk.CTkFont(family="Consolas", size=13),
            wrap="none",
            height=10,
            activate_scrollbars=False,
        )
        code_tb.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 8))
        code_tb.insert("1.0", code)
        code_tb.configure(state="disabled")

        # Auto-size height
        def _resize_code():
            try:
                n_lines = code.count("\n") + 1
                new_h = min(300, max(26, n_lines * 20 + 8))
                code_tb.configure(height=new_h)
            except Exception:
                pass
        self.after(30, _resize_code)

        return frame

    def _copy_code(self, code: str, btn):
        """Copy code block to clipboard."""
        try:
            root = self.winfo_toplevel()
            root.clipboard_clear()
            root.clipboard_append(code)
            root.update()
            if btn:
                btn.configure(text="OK!")
                self.after(1500, lambda: btn.configure(text="COPY"))
        except Exception:
            if btn:
                btn.configure(text="ERR")
                self.after(1500, lambda: btn.configure(text="COPY"))

    def _setup_wrap(self, label: ctk.CTkLabel):
        """Set up dynamic wraplength for a label."""
        def _update_wrap(event=None):
            try:
                p = self.master
                while p and not isinstance(p, MatrixScrollableFrame):
                    p = p.master
                if p:
                    available = p.winfo_width() - 80
                else:
                    available = self.winfo_width() - 40
                label.configure(wraplength=max(200, available))
            except Exception:
                pass
        self.bind("<Configure>", _update_wrap, add="+")
        self.after(50, _update_wrap)

    def update_text(self, content: str, streaming: bool = False):
        """Update content (for streaming). Rebuild widgets."""
        self._content = content
        # During streaming, use simple text to avoid constant widget rebuilds
        if streaming:
            # Clear widgets and show plain text with cursor
            for w in self._widgets:
                try:
                    w.destroy()
                except Exception:
                    pass
            self._widgets.clear()
            display = parse_markdown_simple(content) + DECORATIONS["cursor"]
            lbl = ctk.CTkLabel(
                self,
                text=display,
                font=ctk.CTkFont(family="Consolas", size=14),
                text_color=self._text_color,
                anchor="nw",
                justify="left",
                wraplength=1,
            )
            lbl.grid(row=0, column=0, sticky="ew")
            self._widgets.append(lbl)
            self._setup_wrap(lbl)
        else:
            # Final render: full rich rendering
            for w in self._widgets:
                try:
                    w.destroy()
                except Exception:
                    pass
            self._widgets.clear()
            if self._is_user:
                self._render_plain(content)
            else:
                self._render_rich(content)


# ── Typing indicator ───────────────────────────────────────────────

class TypingIndicator(ctk.CTkFrame):
    """Animated typing indicator with bouncing dots"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self._running = True
        self._idx = 0

        self._dots = ctk.CTkLabel(
            self,
            text=f"{DECORATIONS['circle_filled']}  {DECORATIONS['circle']}  {DECORATIONS['circle']}",
            font=ctk.CTkFont(family="Consolas", size=14),
            text_color=COLORS["matrix_green"],
            anchor="w",
        )
        self._dots.pack(side="left")

        self._text = ctk.CTkLabel(
            self,
            text="  pensando...",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self._text.pack(side="left", padx=(6, 0))

        self._animate()

    def _animate(self):
        if not self._running:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        f = DECORATIONS["circle_filled"]
        o = DECORATIONS["circle"]
        frames = [f"{f}  {o}  {o}", f"{o}  {f}  {o}", f"{o}  {o}  {f}"]
        self._dots.configure(text=frames[self._idx % len(frames)])
        self._idx += 1
        self.after(350, self._animate)

    def stop(self):
        self._running = False


# ── Chat message bubble ────────────────────────────────────────────

class ChatMessage(ctk.CTkFrame):
    """Matrix-styled chat message bubble with rich content, copy, and translate"""

    def __init__(self, parent, role: str, content: str, timestamp: str = None, **kwargs):
        self.role = role
        self.raw_content = content
        is_user = role == "user"

        if is_user:
            bg_color = COLORS["bg_tertiary"]
            border_color = COLORS["accent_cyan"]
            text_color = COLORS["accent_cyan"]
            prefix = f"{DECORATIONS['prompt']} USER"
            self._content_color = COLORS["text_white"]
        elif role == "error":
            bg_color = "#1a0a0a"
            border_color = COLORS["error"]
            text_color = COLORS["error"]
            prefix = f"{DECORATIONS['cross']} ERROR"
            self._content_color = COLORS["error"]
        else:
            bg_color = COLORS["bg_secondary"]
            border_color = COLORS["matrix_green_dim"]
            text_color = COLORS["matrix_green"]
            prefix = f"{DECORATIONS['block']} DRAGO"
            self._content_color = COLORS["matrix_green"]

        super().__init__(
            parent,
            fg_color=bg_color,
            border_color=border_color,
            border_width=1,
            corner_radius=RADIUS["lg"],
            **kwargs
        )

        self.grid_columnconfigure(0, weight=1)

        # Header with role, timestamp and copy button
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        header.grid_columnconfigure(1, weight=1)

        role_label = ctk.CTkLabel(
            header,
            text=prefix,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=text_color
        )
        role_label.grid(row=0, column=0, sticky="w")

        # Timestamp
        time_str = timestamp or datetime.now().strftime("%H:%M:%S")
        time_label = ctk.CTkLabel(
            header,
            text=time_str,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"]
        )
        time_label.grid(row=0, column=1, sticky="e", padx=(10, 5))

        # Copy button
        self.copy_btn = ctk.CTkButton(
            header,
            text="COPY",
            font=ctk.CTkFont(family="Consolas", size=10),
            width=50,
            height=22,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=border_color,
            border_width=1,
            text_color=text_color,
            command=self._copy_content
        )
        self.copy_btn.grid(row=0, column=2, sticky="e")

        # Translate button (assistant messages only)
        self._translation_frame = None
        self._showing_translation = False
        self._translated_text = None
        self._translator = None
        self._translate_source = "es"
        self._translate_target = "en"
        self._typing = None

        if role == "assistant":
            self.translate_btn = ctk.CTkButton(
                header,
                text="TRADUCIR",
                font=ctk.CTkFont(family="Consolas", size=10),
                width=70,
                height=22,
                fg_color=COLORS["bg_tertiary"],
                hover_color=COLORS["bg_hover"],
                border_color=COLORS["accent_orange"],
                border_width=1,
                text_color=COLORS["accent_orange"],
                command=self._toggle_translation
            )
            self.translate_btn.grid(row=0, column=2, sticky="e", padx=(0, 5))
            # Move copy button to column 3
            self.copy_btn.grid(row=0, column=3, sticky="e")
        else:
            self.translate_btn = None

        # Separator
        sep = ctk.CTkFrame(self, fg_color=COLORS["border_dim"], height=1)
        sep.grid(row=1, column=0, sticky="ew", padx=12, pady=2)

        # Rich content area
        self.content_widget = RichMessageContent(
            self,
            content=content,
            text_color=self._content_color,
            is_user=is_user,
        )
        self.content_widget.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 8))

    def show_typing(self):
        """Show animated typing indicator, hide content"""
        self.content_widget.grid_remove()
        self._typing = TypingIndicator(self)
        self._typing.grid(row=2, column=0, sticky="w", padx=12, pady=(4, 8))

    def hide_typing(self):
        """Remove typing indicator and restore content"""
        if self._typing:
            self._typing.stop()
            try:
                self._typing.destroy()
            except Exception:
                pass
            self._typing = None
        self.content_widget.grid()

    def _copy_content(self):
        """Copy message content to clipboard"""
        try:
            root = self.winfo_toplevel()
            root.clipboard_clear()
            root.clipboard_append(self.raw_content)
            root.update()
            self.copy_btn.configure(text="OK!")
            self.after(1500, lambda: self.copy_btn.configure(text="COPY"))
        except Exception:
            try:
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(self.raw_content)
                    self.copy_btn.configure(text="OK!")
                    self.after(1500, lambda: self.copy_btn.configure(text="COPY"))
                    return
            except Exception:
                pass
            self.copy_btn.configure(text="ERR")
            self.after(1500, lambda: self.copy_btn.configure(text="COPY"))

    def update_content(self, content: str):
        """Update message content (for streaming)"""
        if self._typing:
            self.hide_typing()
        self.raw_content = content
        self.content_widget.update_text(content, streaming=True)

    def finish_content(self, content: str):
        """Finalize content (remove cursor, render rich markdown)"""
        if self._typing:
            self.hide_typing()
        self.raw_content = content
        self.content_widget.update_text(content, streaming=False)

    def _refresh_scroll_region(self):
        """Force parent scrollable frame to recalculate"""
        def _do():
            try:
                p = self.master
                while p and not isinstance(p, MatrixScrollableFrame):
                    p = p.master
                if not p:
                    return
                canvas = p._parent_canvas
                canvas.update_idletasks()
                canvas.configure(scrollregion=canvas.bbox("all"))
            except Exception:
                pass
        self.after(80, _do)

    def _toggle_translation(self):
        """Toggle translation display"""
        if self._showing_translation:
            if self._translation_frame:
                self._translation_frame.destroy()
                self._translation_frame = None
            self.translate_btn.configure(text="TRADUCIR")
            self._showing_translation = False
            self._refresh_scroll_region()
        else:
            self.translate_btn.configure(text="...", state="disabled")
            self._do_translate()

    def _do_translate(self):
        """Perform translation in background thread"""
        import threading

        if not self._translator or not self._translator.is_ready():
            self.translate_btn.configure(text="N/A", state="normal")
            self.after(1500, lambda: self.translate_btn.configure(text="TRADUCIR"))
            return

        def work():
            translated = self._translator.translate(
                self.raw_content, self._translate_target, self._translate_source
            )

            def show():
                if not self.winfo_exists():
                    return
                self._translated_text = translated
                self._show_translation(translated)
                self.translate_btn.configure(text="ORIGINAL", state="normal")
                self._showing_translation = True

            self.after(0, show)

        threading.Thread(target=work, daemon=True).start()

    def _show_translation(self, text: str):
        """Display translated text below original"""
        self._translation_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["accent_orange"],
            border_width=1,
            corner_radius=4
        )
        self._translation_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 6))

        trans_header = ctk.CTkFrame(self._translation_frame, fg_color="transparent")
        trans_header.pack(fill="x", padx=10, pady=(8, 4))
        trans_header.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            trans_header,
            text=f" {DECORATIONS['h_line']*3} TRANSLATION {DECORATIONS['h_line']*3}",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["accent_orange"]
        ).grid(row=0, column=0, sticky="w")

        self._trans_copy_btn = ctk.CTkButton(
            trans_header,
            text="COPY",
            font=ctk.CTkFont(family="Consolas", size=10),
            width=50,
            height=20,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["accent_orange"],
            border_width=1,
            text_color=COLORS["accent_orange"],
            command=lambda: self._copy_translation(text)
        )
        self._trans_copy_btn.grid(row=0, column=2, sticky="e")

        trans_textbox = MatrixTextbox(
            self._translation_frame,
            height=10,
            wrap="word",
            fg_color=COLORS["bg_tertiary"],
            border_width=0,
            text_color=COLORS["accent_orange"],
            font=ctk.CTkFont(family="Consolas", size=13),
        )
        trans_textbox.pack(fill="x", padx=8, pady=(0, 8))

        try:
            trans_textbox._scrollbar.grid_forget()
        except Exception:
            pass

        display = parse_markdown_simple(text)
        trans_textbox.insert("1.0", display)
        trans_textbox.configure(state="disabled")

        def resize():
            try:
                trans_textbox.configure(state="normal")
                inner = trans_textbox._textbox
                inner.update_idletasks()
                last_index = inner.index("end-1c")
                bbox = inner.dlineinfo(last_index)
                if bbox:
                    new_h = bbox[1] + bbox[3] + 4
                    trans_textbox.configure(height=max(26, new_h), state="disabled")
                else:
                    dl = inner.count("1.0", "end", "displaylines")
                    if dl:
                        n = dl[0] if isinstance(dl, tuple) else dl
                    else:
                        n = int(trans_textbox.index("end-1c").split(".")[0])
                    trans_textbox.configure(height=max(26, n * 20 + 4), state="disabled")
            except Exception:
                pass

        self.after(50, resize)
        self.after(120, self._refresh_scroll_region)

    def _copy_translation(self, text: str):
        """Copy translated text to clipboard"""
        try:
            root = self.winfo_toplevel()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            self._trans_copy_btn.configure(text="OK!")
            self.after(1500, lambda: self._trans_copy_btn.configure(text="COPY"))
        except Exception:
            try:
                if PYPERCLIP_AVAILABLE:
                    pyperclip.copy(text)
                    self._trans_copy_btn.configure(text="OK!")
                    self.after(1500, lambda: self._trans_copy_btn.configure(text="COPY"))
                    return
            except Exception:
                pass
            self._trans_copy_btn.configure(text="ERR")
            self.after(1500, lambda: self._trans_copy_btn.configure(text="COPY"))


# ── Main Chat Panel ────────────────────────────────────────────────

class ChatPanel(ctk.CTkFrame):
    """Matrix-styled chat interface with rich rendering and keyboard shortcuts"""

    def __init__(
        self,
        parent,
        on_send: Callable[[str], None],
        on_stop: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        kwargs.setdefault("fg_color", COLORS["bg_primary"])
        kwargs.setdefault("corner_radius", 0)

        super().__init__(parent, **kwargs)

        self.on_send = on_send
        self.on_stop = on_stop
        self.messages: List[dict] = []
        self.message_widgets: List[ChatMessage] = []
        self.is_generating = False
        self.current_assistant_widget: Optional[ChatMessage] = None
        self.current_response = ""
        self._first_token_received = False
        self._system_prompt: Optional[str] = None
        self._translator = None
        self._translate_source = "es"
        self._translate_target = "en"
        self._auto_translate = False
        self._current_chat: Optional[dict] = None
        self._on_chat_updated: Optional[Callable[[dict], None]] = None
        self._context_badge = None
        self._stream_update_pending = False
        self.max_context_messages = MAX_CONTEXT_MESSAGES

        self._setup_ui()

    def _setup_ui(self):
        """Setup chat UI"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header with context indicator and export button
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        header = TerminalHeader(header_frame, "NEURAL INTERFACE", "chat.session")
        header.grid(row=0, column=0, sticky="ew")

        # Context indicator (messages in context: X/40)
        self.context_label = ctk.CTkLabel(
            header_frame,
            text=f"CTX: 0/{self.max_context_messages}",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"],
        )
        self.context_label.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="e")

        self.export_btn = ctk.CTkButton(
            header_frame,
            text=f"{DECORATIONS['arrow_r']} EXPORT",
            font=ctk.CTkFont(family="Consolas", size=10),
            width=70,
            height=24,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["matrix_green_dim"],
            border_width=1,
            text_color=COLORS["matrix_green"],
            command=self._export_chat,
        )
        self.export_btn.grid(row=0, column=2, padx=10, pady=5, sticky="e")
        MatrixTooltip(self.export_btn, "Export chat as Markdown file")

        # Messages container
        self.messages_container = ctk.CTkFrame(self, fg_color=COLORS["bg_primary"])
        self.messages_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.messages_container.grid_columnconfigure(0, weight=1)
        self.messages_container.grid_rowconfigure(0, weight=1)

        self.messages_frame = MatrixScrollableFrame(
            self.messages_container,
            fg_color=COLORS["bg_primary"],
            border_width=0
        )
        self.messages_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.messages_frame.grid_columnconfigure(0, weight=1)

        # Welcome message
        self._show_welcome()

        # Input area
        self.input_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_tertiary"])
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        self.input_frame.grid_columnconfigure(1, weight=1)

        # Input decoration
        prompt_label = ctk.CTkLabel(
            self.input_frame,
            text=f" {DECORATIONS['prompt']} INPUT:",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLORS["matrix_green"]
        )
        prompt_label.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="nw")

        # Text input with auto-resize
        self.input_text = MatrixTextbox(
            self.input_frame,
            height=INPUT_MIN_HEIGHT,
            wrap="word",
            border_color=COLORS["matrix_green_dim"],
            fg_color=COLORS["bg_input"]
        )
        self.input_text.grid(row=0, column=1, sticky="ew", padx=5, pady=10)

        # Keyboard shortcuts
        self.input_text.bind("<Return>", self._on_enter)
        self.input_text.bind("<Shift-Return>", self._on_shift_enter)
        self.input_text.bind("<KeyRelease>", self._on_input_change)
        # Escape to stop generation (bind on root window via tkinter, not CTk)
        self.winfo_toplevel().bind("<Escape>", self._on_escape)

        # Focus glow effect
        self.input_text.bind("<FocusIn>", lambda e: self.input_text.configure(
            border_color=COLORS["matrix_green"]
        ))
        self.input_text.bind("<FocusOut>", lambda e: self.input_text.configure(
            border_color=COLORS["matrix_green_dim"]
        ))

        # Buttons container
        btn_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=15, pady=10, sticky="n")

        # Send button
        self.send_button = ctk.CTkButton(
            btn_frame,
            text=f"{DECORATIONS['arrow_r']} SEND",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            width=110,
            height=40,
            fg_color=COLORS["matrix_green_dark"],
            hover_color=COLORS["matrix_green_dim"],
            border_color=COLORS["matrix_green"],
            border_width=1,
            text_color=COLORS["bg_dark"],
            command=self._send_message
        )
        self.send_button.pack(pady=(0, 5))
        MatrixTooltip(self.send_button, "Send message (Enter)")

        # Stop button (hidden initially)
        self.stop_button = ctk.CTkButton(
            btn_frame,
            text=f"{DECORATIONS['cross']} STOP",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            width=110,
            height=40,
            fg_color="#330011",
            hover_color="#550022",
            border_color=COLORS["error"],
            border_width=1,
            text_color=COLORS["error"],
            command=self._stop_generation
        )
        MatrixTooltip(self.stop_button, "Stop generation (Escape)")

        # Clear button
        self.clear_button = ctk.CTkButton(
            btn_frame,
            text="CLEAR",
            font=ctk.CTkFont(family="Consolas", size=12),
            width=110,
            height=32,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["matrix_green_dim"],
            border_width=1,
            text_color=COLORS["matrix_green"],
            command=self.clear_chat
        )
        self.clear_button.pack(pady=(5, 0))
        MatrixTooltip(self.clear_button, "Clear all messages and start fresh")

        # Translation toggle row
        self.translate_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.translate_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=15, pady=(0, 8))

        self.translate_label = ctk.CTkLabel(
            self.translate_frame,
            text=f" {DECORATIONS['block_med']} AUTO-TRANSLATE: ES {DECORATIONS['arrow_r']} EN",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"]
        )
        self.translate_label.pack(side="left", padx=(0, 10))

        self.translate_switch = ctk.CTkSwitch(
            self.translate_frame,
            text="",
            width=40,
            height=20,
            fg_color=COLORS["bg_tertiary"],
            progress_color=COLORS["matrix_green_dark"],
            button_color=COLORS["matrix_green"],
            button_hover_color=COLORS["matrix_green_bright"],
            command=self._update_translate_label
        )
        self.translate_switch.pack(side="left")

        self.translate_status = ctk.CTkLabel(
            self.translate_frame,
            text="OFF",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"]
        )
        self.translate_status.pack(side="left", padx=(8, 0))

        # Shortcut hints
        shortcut_label = ctk.CTkLabel(
            self.translate_frame,
            text="Enter=Send  Shift+Enter=Newline  Esc=Stop",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_dim"],
        )
        shortcut_label.pack(side="right", padx=(10, 0))

        # Status bar separator
        status_sep = ctk.CTkFrame(self, fg_color=COLORS["border_green"], height=1)
        status_sep.grid(row=3, column=0, sticky="ew")

        # Status bar
        self.status_bar = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], height=28)
        self.status_bar.grid(row=4, column=0, sticky="ew")

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text=f"  {DECORATIONS['circle']} Ready",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        self.status_label.pack(side="left", padx=10, pady=3)

        self.token_count = ctk.CTkLabel(
            self.status_bar,
            text="Tokens: 0",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"]
        )
        self.token_count.pack(side="right", padx=10, pady=3)

    # ── Welcome empty state ────────────────────────────────────────

    def _show_welcome(self):
        """Show a welcoming empty state message"""
        if hasattr(self, '_welcome_widget') and self._welcome_widget and self._welcome_widget.winfo_exists():
            self._welcome_widget.destroy()

        welcome_frame = ctk.CTkFrame(
            self.messages_frame,
            fg_color=COLORS["bg_card"],
            border_color=COLORS["matrix_green_dim"],
            border_width=1,
            corner_radius=8,
        )
        welcome_frame.pack(fill="x", pady=40, padx=30)

        # Logo / title area
        logo_label = ctk.CTkLabel(
            welcome_frame,
            text=f"\n{DECORATIONS['block_dark']*2} {DECORATIONS['block']*2} {DECORATIONS['block_dark']*2}",
            font=ctk.CTkFont(family="Consolas", size=18),
            text_color=COLORS["matrix_green_dark"],
        )
        logo_label.pack(pady=(20, 0))

        title_label = ctk.CTkLabel(
            welcome_frame,
            text="DRAGO MODEL RUNNER",
            font=ctk.CTkFont(family="Consolas", size=20, weight="bold"),
            text_color=COLORS["matrix_green_bright"],
        )
        title_label.pack(pady=(8, 4))

        subtitle_label = ctk.CTkLabel(
            welcome_frame,
            text="Sistema de inferencia local",
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=COLORS["matrix_green_dim"],
        )
        subtitle_label.pack(pady=(0, 12))

        # Separator
        sep = ctk.CTkFrame(welcome_frame, fg_color=COLORS["border_green"], height=1)
        sep.pack(fill="x", padx=30, pady=(0, 12))

        # Shortcut hints in a styled area
        hints_frame = ctk.CTkFrame(welcome_frame, fg_color=COLORS["bg_secondary"], corner_radius=4)
        hints_frame.pack(fill="x", padx=20, pady=(0, 8))

        hints = [
            (f"{DECORATIONS['prompt']} ENTER", "Enviar mensaje"),
            (f"{DECORATIONS['prompt']} SHIFT+ENTER", "Nueva linea"),
            (f"{DECORATIONS['prompt']} ESCAPE", "Detener generacion"),
            (f"{DECORATIONS['prompt']} CLEAR", "Reiniciar sesion"),
            (f"{DECORATIONS['prompt']} COPY", "Copiar mensajes"),
        ]
        for key, desc in hints:
            row_frame = ctk.CTkFrame(hints_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=12, pady=3)

            ctk.CTkLabel(
                row_frame,
                text=key,
                font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                text_color=COLORS["matrix_green"],
                width=160,
                anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                row_frame,
                text=desc,
                font=ctk.CTkFont(family="Consolas", size=12),
                text_color=COLORS["text_muted"],
                anchor="w",
            ).pack(side="left")

        # Bottom hint
        bottom_label = ctk.CTkLabel(
            welcome_frame,
            text="Selecciona un modelo para comenzar.",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=COLORS["text_muted"],
        )
        bottom_label.pack(pady=(8, 20))

        self._welcome_widget = welcome_frame

    # ── Keyboard handlers ──────────────────────────────────────────

    def _on_enter(self, event):
        """Enter key sends message (unless Shift is held)"""
        if event.state & 0x1:  # Shift held
            return  # Let default behavior insert newline
        self._send_message()
        return "break"

    def _on_shift_enter(self, event):
        """Shift+Enter inserts a newline"""
        return None

    def _on_escape(self, event):
        """Escape stops generation"""
        if self.is_generating:
            self._stop_generation()

    def _on_input_change(self, event=None):
        """Auto-resize input box based on content"""
        try:
            content = self.input_text.get("1.0", "end-1c")
            if not content.strip():
                self.input_text.configure(height=INPUT_MIN_HEIGHT)
                return

            lines = content.count("\n") + 1
            needed = max(INPUT_MIN_HEIGHT, min(INPUT_MAX_HEIGHT, lines * INPUT_LINE_HEIGHT + 8))
            self.input_text.configure(height=int(needed))
        except Exception:
            pass

    # ── Send / Stop ────────────────────────────────────────────────

    def _send_message(self):
        """Send user message"""
        if self.is_generating:
            return

        content = self.input_text.get("1.0", "end-1c").strip()
        if not content:
            return

        # Clear input immediately for snappy feel
        self.input_text.delete("1.0", "end")
        self.input_text.configure(height=INPUT_MIN_HEIGHT)

        if hasattr(self, '_welcome_widget') and self._welcome_widget.winfo_exists():
            self._welcome_widget.destroy()

        self.add_message("user", content)
        self._set_status("processing", "Enviando...")

        # Force UI render so user message appears instantly before API call
        self.update_idletasks()

        if self.on_send:
            self.on_send(content)

    def _stop_generation(self):
        """Stop generation - finalize partial response and notify parent"""
        if self.current_assistant_widget:
            if self.current_response:
                self.messages.append({"role": "assistant", "content": self.current_response})
                self.current_assistant_widget.finish_content(self.current_response)
            else:
                self.current_assistant_widget.destroy()
                if self.current_assistant_widget in self.message_widgets:
                    self.message_widgets.remove(self.current_assistant_widget)

        self.current_assistant_widget = None
        self.current_response = ""
        self.is_generating = False
        self._toggle_generating(False)
        self._set_status("ready", "Generacion detenida")
        self._update_token_count()

        if self.on_stop:
            self.on_stop()

    def _toggle_generating(self, generating: bool):
        """Toggle UI state"""
        self.is_generating = generating

        if generating:
            self.send_button.pack_forget()
            self.stop_button.pack(pady=(0, 5))
            self.input_text.configure(state="disabled", border_color=COLORS["text_muted"])
        else:
            self.stop_button.pack_forget()
            self.send_button.pack(pady=(0, 5))
            self.input_text.configure(state="normal", border_color=COLORS["matrix_green_dim"])
            # Refocus input after generation
            self.after(100, lambda: self.input_text.focus_set())

    def _set_status(self, status: str, text: str):
        """Update status bar"""
        colors = {
            "ready": COLORS["matrix_green_dim"],
            "processing": COLORS["warning"],
            "error": COLORS["error"],
            "streaming": COLORS["matrix_green"],
        }
        symbols = {
            "ready": DECORATIONS["circle"],
            "processing": DECORATIONS["block_med"],
            "error": DECORATIONS["cross"],
            "streaming": DECORATIONS["block"],
        }
        self.status_label.configure(
            text=f"  {symbols.get(status, DECORATIONS['circle'])} {text}",
            text_color=colors.get(status, COLORS["text_muted"])
        )

    # ── Message management ─────────────────────────────────────────

    def _trim_old_widgets(self):
        """Destroy the oldest message widgets when count exceeds MAX_VISIBLE_WIDGETS.

        Prevents unbounded Tk widget accumulation in long chat sessions.
        The underlying self.messages list is never trimmed, only the UI widgets.
        """
        excess = len(self.message_widgets) - MAX_VISIBLE_WIDGETS
        if excess <= 0:
            return
        for _ in range(excess):
            old = self.message_widgets.pop(0)
            try:
                old.destroy()
            except Exception:
                pass

    def add_message(self, role: str, content: str, timestamp: str = None) -> ChatMessage:
        """Add message to chat"""
        self.messages.append({"role": role, "content": content})

        widget = ChatMessage(self.messages_frame, role, content, timestamp=timestamp)
        if role == "assistant" and self._translator:
            widget._translator = self._translator
            widget._translate_source = self._translate_source
            widget._translate_target = self._translate_target
        widget.pack(fill="x", pady=8, padx=5)
        self.message_widgets.append(widget)
        self._trim_old_widgets()

        self.after(50, self._scroll_to_bottom)
        self._update_token_count()
        self._notify_chat_updated()

        return widget

    def add_error_message(self, content: str):
        """Add a styled error message bubble"""
        widget = ChatMessage(self.messages_frame, "error", content)
        widget.pack(fill="x", pady=8, padx=5)
        self.message_widgets.append(widget)
        self.after(50, self._scroll_to_bottom)

    def start_assistant_message(self):
        """Start streaming assistant message with typing indicator"""
        self._toggle_generating(True)
        self._set_status("processing", "Pensando...")
        self._first_token_received = False

        self.current_response = ""
        self.current_assistant_widget = ChatMessage(
            self.messages_frame, "assistant", ""
        )
        if self._translator:
            self.current_assistant_widget._translator = self._translator
            self.current_assistant_widget._translate_source = self._translate_source
            self.current_assistant_widget._translate_target = self._translate_target
        self.current_assistant_widget.pack(fill="x", pady=8, padx=5)
        self.current_assistant_widget.show_typing()
        self.message_widgets.append(self.current_assistant_widget)
        self._scroll_to_bottom()

    def append_to_assistant(self, token: str):
        """Append token to streaming message"""
        if not self.is_generating:
            return

        self.current_response += token

        # First token: transition from typing indicator to streaming
        if not self._first_token_received:
            self._first_token_received = True
            self._set_status("streaming", "Generando respuesta...")

        # Throttle UI updates -- batch tokens, update every 50ms
        if not self._stream_update_pending:
            self._stream_update_pending = True
            self.after(50, self._flush_stream_update)

    def _flush_stream_update(self):
        """Batch-flush streamed tokens to the UI"""
        self._stream_update_pending = False
        if self.current_assistant_widget and self.current_response:
            self.current_assistant_widget.update_content(self.current_response)
        # Auto-scroll during streaming
        self._scroll_to_bottom()

    def finish_assistant_message(self):
        """Finish streaming"""
        self._stream_update_pending = False
        if self.current_assistant_widget:
            if self.current_response:
                self.messages.append({"role": "assistant", "content": self.current_response})
                self.current_assistant_widget.finish_content(self.current_response)
            else:
                self.current_assistant_widget.destroy()
                if self.current_assistant_widget in self.message_widgets:
                    self.message_widgets.remove(self.current_assistant_widget)

        self.current_assistant_widget = None
        self.current_response = ""
        self._trim_old_widgets()
        self._toggle_generating(False)
        self._set_status("ready", "Listo")
        self._update_token_count()
        self._notify_chat_updated()
        self._scroll_to_bottom()

    # ── Scroll ─────────────────────────────────────────────────────

    def _scroll_to_bottom(self):
        """Reliably scroll to bottom of messages.
        Uses update_idletasks + scroll region recalc for reliability."""
        try:
            canvas = self.messages_frame._parent_canvas
            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.yview_moveto(1.0)
        except Exception:
            pass

    # ── Token/context count ────────────────────────────────────────

    def _update_token_count(self):
        """Update token count estimate with sliding window info"""
        total_msgs = len(self.messages)
        total_chars = sum(len(m["content"]) for m in self.messages)
        estimated_tokens = total_chars // 4

        # Update context indicator in header
        context_msgs = min(total_msgs, self.max_context_messages)
        try:
            self.context_label.configure(
                text=f"CTX: {context_msgs}/{self.max_context_messages}",
                text_color=COLORS["warning"] if total_msgs > self.max_context_messages else COLORS["text_muted"]
            )
        except Exception:
            pass

        if total_msgs > self.max_context_messages:
            self.token_count.configure(
                text=f"~{estimated_tokens} tok | {total_msgs} msgs (window: {self.max_context_messages})"
            )
            dropped = total_msgs - self.max_context_messages
            if self._context_badge is None:
                self._context_badge = ctk.CTkLabel(
                    self.messages_frame,
                    text=f"  \u26a0 Contexto limitado: {dropped} mensajes anteriores no se env\u00edan al modelo",
                    font=ctk.CTkFont(family="Consolas", size=11),
                    text_color=COLORS["warning"],
                    fg_color=COLORS["bg_tertiary"],
                    corner_radius=4,
                    anchor="w",
                )
                self._context_badge.pack(fill="x", pady=(0, 6), padx=5, before=self.message_widgets[0] if self.message_widgets else None)
            else:
                self._context_badge.configure(text=f"  \u26a0 Contexto limitado: {dropped} mensajes anteriores no se env\u00edan al modelo")
        else:
            self.token_count.configure(text=f"~{estimated_tokens} tok | {total_msgs} msgs")
            if self._context_badge is not None:
                self._context_badge.destroy()
                self._context_badge = None

    # ── Clear / Lifecycle ──────────────────────────────────────────

    def clear_chat(self, _from_parent: bool = False):
        """Clear all messages."""
        for widget in self.message_widgets:
            widget.destroy()
        self.message_widgets.clear()
        self.messages.clear()
        self.current_response = ""
        self.current_assistant_widget = None
        if self._context_badge is not None:
            self._context_badge.destroy()
            self._context_badge = None
        self._set_status("ready", "Session cleared")
        self._update_token_count()
        self._show_welcome()
        if not _from_parent:
            self._current_chat = None
            if self._on_chat_updated:
                self._on_chat_updated(None)

    def set_system_prompt(self, prompt: str):
        """Set the system prompt for this chat session"""
        self._system_prompt = prompt if prompt and prompt.strip() else None

    def get_messages(self) -> List[dict]:
        """Get messages for API with sliding window and optional system prompt"""
        msgs = self.messages.copy()

        if len(msgs) > self.max_context_messages:
            msgs = msgs[-self.max_context_messages:]

        if self._system_prompt:
            msgs = [{"role": "system", "content": self._system_prompt}] + msgs

        return msgs

    def set_translator(self, translator, source_lang: str, target_lang: str, auto_translate: bool):
        """Set the translation service and update toggle state"""
        self._translator = translator
        self._translate_source = source_lang
        self._translate_target = target_lang
        self._auto_translate = auto_translate

        for widget in self.message_widgets:
            if hasattr(widget, 'role') and widget.role == "assistant":
                widget._translator = translator
                widget._translate_source = source_lang
                widget._translate_target = target_lang

        if hasattr(self, 'translate_switch'):
            if auto_translate:
                self.translate_switch.select()
            else:
                self.translate_switch.deselect()
            self._update_translate_label()

    def translate_toggle_on(self) -> bool:
        """Check if the translate toggle is active"""
        if hasattr(self, 'translate_switch'):
            return self.translate_switch.get() == 1
        return False

    def _update_translate_label(self):
        """Update translation toggle label based on state"""
        if self.translate_switch.get() == 1:
            self.translate_status.configure(
                text="ON",
                text_color=COLORS["matrix_green"]
            )
            self.translate_label.configure(text_color=COLORS["matrix_green"])
        else:
            self.translate_status.configure(
                text="OFF",
                text_color=COLORS["text_muted"]
            )
            self.translate_label.configure(text_color=COLORS["text_muted"])

    # ── Chat lifecycle methods ─────────────────────────────────────

    def set_chat_callback(self, callback: Callable[[dict], None]):
        """Set callback for when chat data changes (for auto-save)."""
        self._on_chat_updated = callback

    def load_chat(self, chat_data: dict):
        """Load a chat session into the panel."""
        for widget in self.message_widgets:
            widget.destroy()
        self.message_widgets.clear()
        self.messages.clear()

        if hasattr(self, '_welcome_widget') and self._welcome_widget.winfo_exists():
            self._welcome_widget.destroy()

        self._current_chat = chat_data

        for msg in chat_data.get("messages", []):
            widget = ChatMessage(self.messages_frame, msg["role"], msg["content"])
            widget.pack(fill="x", pady=8, padx=5)
            self.message_widgets.append(widget)
            self.messages.append(msg)
            if msg["role"] == "assistant" and self._translator:
                widget._translator = self._translator
                widget._translate_source = self._translate_source
                widget._translate_target = self._translate_target

        if not chat_data.get("messages"):
            self._show_welcome()

        if chat_data.get("system_prompt"):
            self._system_prompt = chat_data["system_prompt"]

        self._set_status("ready", "Chat loaded")
        self._update_token_count()
        self.after(50, self._scroll_to_bottom)

    def get_current_chat(self) -> Optional[dict]:
        """Get current chat data with latest messages."""
        if self._current_chat:
            self._current_chat["messages"] = self.messages.copy()
            if self._system_prompt:
                self._current_chat["system_prompt"] = self._system_prompt
        return self._current_chat

    def set_current_chat(self, chat_data: dict):
        """Set current chat reference (used when creating new chat)."""
        self._current_chat = chat_data

    def _notify_chat_updated(self):
        """Notify parent that chat data changed (for auto-save)."""
        if self._on_chat_updated and self._current_chat:
            self._current_chat["messages"] = self.messages.copy()
            self._on_chat_updated(self._current_chat)

    def _export_chat(self):
        """Export current chat as Markdown file."""
        from tkinter import filedialog

        if not self._current_chat or not self.messages:
            return

        title = self._current_chat.get("title", "chat")
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:50].strip()

        path = filedialog.asksaveasfilename(
            title="Export Chat",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")],
            initialfile=f"{safe_title}.md",
        )
        if not path:
            return

        lines = [
            f"# {title}",
            f"**Model:** {self._current_chat.get('model', 'N/A')} | "
            f"**Date:** {self._current_chat.get('created_at', '')[:10]}",
            "",
            "---",
            "",
        ]
        for msg in self.messages:
            role = "User" if msg["role"] == "user" else "DRAGO"
            lines.append(f"**{role}:** {msg['content']}")
            lines.append("")
            lines.append("---")
            lines.append("")

        Path(path).write_text("\n".join(lines), encoding="utf-8")
        self._set_status("ready", f"Exported to {Path(path).name}")
