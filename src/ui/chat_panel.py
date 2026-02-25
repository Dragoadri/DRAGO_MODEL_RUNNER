"""Matrix-styled Chat Interface with Markdown support"""
import customtkinter as ctk
from typing import List, Optional, Callable
from datetime import datetime
import re

# Optional clipboard support
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

from .theme import COLORS, DECORATIONS
from .widgets import (
    MatrixFrame, MatrixScrollableFrame, MatrixButton,
    MatrixTextbox, MatrixLabel, TerminalHeader
)

# Max messages to send to the API (sliding window)
MAX_CONTEXT_MESSAGES = 40  # 20 user/assistant pairs


def parse_markdown_simple(text: str) -> str:
    """Convert markdown to plain text with visual indicators"""
    # Remove code blocks but keep content
    text = re.sub(r'```[\w]*\n?(.*?)```', r'[\1]', text, flags=re.DOTALL)
    # Inline code
    text = re.sub(r'`([^`]+)`', r'[\1]', text)
    # Bold **text** or __text__
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    # Italic *text* or _text_
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'\1', text)
    # Headers
    text = re.sub(r'^#{1,6}\s*(.+)$', r'>>> \1', text, flags=re.MULTILINE)
    # Lists
    text = re.sub(r'^\s*[-*]\s+', '  \u2022 ', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '  \u2192 ', text, flags=re.MULTILINE)
    # Links [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    return text.strip()


class ChatMessage(ctk.CTkFrame):
    """Matrix-styled chat message bubble with copy button and selectable text"""

    def __init__(self, parent, role: str, content: str, **kwargs):
        self.role = role
        self.raw_content = content
        is_user = role == "user"

        if is_user:
            bg_color = COLORS["bg_tertiary"]
            border_color = COLORS["accent_cyan"]
            text_color = COLORS["accent_cyan"]
            prefix = f"{DECORATIONS['prompt']} USER"
            self._content_color = COLORS["text_white"]
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
            corner_radius=4,
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

        time_str = datetime.now().strftime("%H:%M:%S")
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

        # Separator
        sep = ctk.CTkFrame(self, fg_color=border_color, height=1)
        sep.grid(row=1, column=0, sticky="ew", padx=12, pady=2)

        # Content - selectable textbox instead of label
        display_content = parse_markdown_simple(content) if not is_user else content

        self.content_textbox = MatrixTextbox(
            self,
            height=10,
            wrap="word",
            fg_color=bg_color,
            border_width=0,
            text_color=self._content_color,
            font=ctk.CTkFont(family="Consolas", size=14),
        )
        self.content_textbox.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 12))

        # Hide the internal scrollbar completely
        try:
            self.content_textbox._scrollbar.grid_forget()
        except Exception:
            pass

        self.content_textbox.insert("1.0", display_content)
        self.content_textbox.configure(state="disabled")

        # Auto-resize textbox height based on content
        self.after(50, self._auto_resize)
        self.bind("<Configure>", lambda e: self.after(50, self._auto_resize), add="+")

    def _auto_resize(self):
        """Auto-resize the textbox to fit all content (no internal scroll)"""
        try:
            self.content_textbox.configure(state="normal")
            # Use the underlying tk.Text widget to count display lines (includes wrapping)
            inner = self.content_textbox._textbox
            display_lines = inner.count("1.0", "end", "displaylines")
            if display_lines:
                num_lines = display_lines[0] if isinstance(display_lines, tuple) else display_lines
            else:
                # Fallback: count logical lines
                num_lines = int(self.content_textbox.index("end-1c").split(".")[0])
            line_height = 24
            new_height = max(40, num_lines * line_height + 10)
            self.content_textbox.configure(height=new_height, state="disabled")
        except Exception:
            # Ultimate fallback: use logical line count
            try:
                num_lines = int(self.content_textbox.index("end-1c").split(".")[0])
                new_height = max(40, num_lines * 24 + 10)
                self.content_textbox.configure(height=new_height, state="disabled")
            except Exception:
                pass

    def _copy_content(self):
        """Copy message content to clipboard"""
        try:
            # Always use tkinter root clipboard (works on X11/Wayland without extras)
            root = self.winfo_toplevel()
            root.clipboard_clear()
            root.clipboard_append(self.raw_content)
            root.update()  # Keep clipboard after widget loses focus
            self.copy_btn.configure(text="OK!")
            self.after(1500, lambda: self.copy_btn.configure(text="COPY"))
        except Exception:
            # Last resort: try pyperclip
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
        self.raw_content = content
        display = parse_markdown_simple(content) if self.role != "user" else content
        self.content_textbox.configure(state="normal")
        self.content_textbox.delete("1.0", "end")
        self.content_textbox.insert("1.0", display + DECORATIONS["cursor"])
        self.content_textbox.configure(state="disabled")
        self.after(10, self._auto_resize)

    def finish_content(self, content: str):
        """Finalize content (remove cursor)"""
        self.raw_content = content
        display = parse_markdown_simple(content) if self.role != "user" else content
        self.content_textbox.configure(state="normal")
        self.content_textbox.delete("1.0", "end")
        self.content_textbox.insert("1.0", display)
        self.content_textbox.configure(state="disabled")
        self.after(10, self._auto_resize)


class ChatPanel(ctk.CTkFrame):
    """Matrix-styled chat interface"""

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
        self._system_prompt: Optional[str] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup chat UI"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = TerminalHeader(self, "NEURAL INTERFACE", "chat.session")
        header.grid(row=0, column=0, sticky="ew")

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
        prompt_label.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="w")

        # Text input
        self.input_text = MatrixTextbox(
            self.input_frame,
            height=80,
            wrap="word",
            border_color=COLORS["matrix_green_dim"],
            fg_color=COLORS["bg_input"]
        )
        self.input_text.grid(row=0, column=1, sticky="ew", padx=5, pady=10)
        self.input_text.bind("<Return>", self._on_enter)
        self.input_text.bind("<Shift-Return>", lambda e: None)

        # Buttons container
        btn_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=15, pady=10)

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

        # Status bar
        self.status_bar = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], height=28)
        self.status_bar.grid(row=3, column=0, sticky="ew")

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

    def _show_welcome(self):
        """Show welcome message"""
        welcome_frame = ctk.CTkFrame(
            self.messages_frame,
            fg_color=COLORS["bg_card"],
            border_color=COLORS["matrix_green_dim"],
            border_width=1
        )
        welcome_frame.pack(fill="x", pady=20, padx=20)

        welcome_text = f"""
{DECORATIONS['block']} DRAGO MODEL RUNNER v1.0
{DECORATIONS['h_line'] * 40}

Sistema de inferencia local inicializado.
Selecciona un modelo en el panel lateral para comenzar.

Comandos:
  {DECORATIONS['prompt']} Escribe tu mensaje y presiona ENTER
  {DECORATIONS['prompt']} SHIFT+ENTER para nueva linea
  {DECORATIONS['prompt']} Boton CLEAR para reiniciar sesion
  {DECORATIONS['prompt']} Boton COPY para copiar mensajes

{DECORATIONS['h_line'] * 40}
        """

        welcome_label = ctk.CTkLabel(
            welcome_frame,
            text=welcome_text,
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=COLORS["matrix_green_dim"],
            justify="left",
            anchor="w",
            wraplength=600
        )
        welcome_label.pack(fill="x", padx=20, pady=15)

        def _update_welcome_wrap(event=None):
            try:
                welcome_label.configure(wraplength=max(200, welcome_frame.winfo_width() - 60))
            except Exception:
                pass

        welcome_frame.bind("<Configure>", _update_welcome_wrap, add="+")

        self._welcome_widget = welcome_frame

    def _on_enter(self, event):
        """Handle Enter key"""
        if not event.state & 0x1:
            self._send_message()
            return "break"

    def _send_message(self):
        """Send user message"""
        if self.is_generating:
            return

        content = self.input_text.get("1.0", "end-1c").strip()
        if not content:
            return

        if hasattr(self, '_welcome_widget') and self._welcome_widget.winfo_exists():
            self._welcome_widget.destroy()

        self.input_text.delete("1.0", "end")
        self.add_message("user", content)
        self._set_status("processing", "Processing query...")

        if self.on_send:
            self.on_send(content)

    def _stop_generation(self):
        """Stop generation - finalize partial response and notify parent"""
        # Finalize the partial response if any
        if self.current_response and self.current_assistant_widget:
            self.messages.append({"role": "assistant", "content": self.current_response})
            self.current_assistant_widget.finish_content(self.current_response)

        self.current_assistant_widget = None
        self.current_response = ""
        self.is_generating = False
        self._toggle_generating(False)
        self._set_status("ready", "Generation stopped")
        self._update_token_count()

        # Notify parent to cancel the backend thread
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

    def add_message(self, role: str, content: str) -> ChatMessage:
        """Add message to chat"""
        self.messages.append({"role": role, "content": content})

        widget = ChatMessage(self.messages_frame, role, content)
        widget.pack(fill="x", pady=8, padx=5)
        self.message_widgets.append(widget)

        self.after(50, self._scroll_to_bottom)
        self._update_token_count()

        return widget

    def start_assistant_message(self):
        """Start streaming assistant message"""
        self._toggle_generating(True)
        self._set_status("streaming", "Receiving response...")

        self.current_response = ""
        self.current_assistant_widget = ChatMessage(
            self.messages_frame, "assistant", DECORATIONS["cursor"]
        )
        self.current_assistant_widget.pack(fill="x", pady=8, padx=5)
        self.message_widgets.append(self.current_assistant_widget)
        self._scroll_to_bottom()

    def append_to_assistant(self, token: str):
        """Append token to streaming message"""
        if not self.is_generating:
            return

        self.current_response += token
        if self.current_assistant_widget:
            self.current_assistant_widget.update_content(self.current_response)

        if len(self.current_response) % 50 == 0:
            self._scroll_to_bottom()

    def finish_assistant_message(self):
        """Finish streaming"""
        if self.current_response:
            self.messages.append({"role": "assistant", "content": self.current_response})
            if self.current_assistant_widget:
                self.current_assistant_widget.finish_content(self.current_response)

        self.current_assistant_widget = None
        self.current_response = ""
        self._toggle_generating(False)
        self._set_status("ready", "Ready")
        self._update_token_count()
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """Scroll to bottom"""
        self.messages_frame._parent_canvas.yview_moveto(1.0)

    def _update_token_count(self):
        """Update token count estimate with sliding window info"""
        total_msgs = len(self.messages)
        total_chars = sum(len(m["content"]) for m in self.messages)
        estimated_tokens = total_chars // 4

        if total_msgs > MAX_CONTEXT_MESSAGES:
            self.token_count.configure(
                text=f"~{estimated_tokens} tok | {total_msgs} msgs (window: {MAX_CONTEXT_MESSAGES})"
            )
        else:
            self.token_count.configure(text=f"~{estimated_tokens} tok | {total_msgs} msgs")

    def clear_chat(self):
        """Clear all messages"""
        for widget in self.message_widgets:
            widget.destroy()
        self.message_widgets.clear()
        self.messages.clear()
        self.current_response = ""
        self.current_assistant_widget = None
        self._set_status("ready", "Session cleared")
        self._update_token_count()
        self._show_welcome()

    def set_system_prompt(self, prompt: str):
        """Set the system prompt for this chat session"""
        self._system_prompt = prompt if prompt and prompt.strip() else None

    def get_messages(self) -> List[dict]:
        """Get messages for API with sliding window and optional system prompt"""
        msgs = self.messages.copy()

        # Apply sliding window
        if len(msgs) > MAX_CONTEXT_MESSAGES:
            msgs = msgs[-MAX_CONTEXT_MESSAGES:]

        # Prepend system prompt if set
        if self._system_prompt:
            msgs = [{"role": "system", "content": self._system_prompt}] + msgs

        return msgs
