"""Custom Matrix-styled widgets"""
import customtkinter as ctk
from typing import Optional, Callable, List
import time
import threading

from .theme import COLORS, FONTS, DECORATIONS, BUTTON_STYLE, BUTTON_PRIMARY_STYLE, ENTRY_STYLE, RADIUS
from ..utils.logger import get_logger

log = get_logger("widgets")


class MatrixButton(ctk.CTkButton):
    """Matrix-styled button with glow effect"""

    def __init__(self, parent, text: str = "", primary: bool = False, **kwargs):
        style = BUTTON_PRIMARY_STYLE if primary else BUTTON_STYLE

        # Remove conflicting kwargs
        for key in list(style.keys()):
            if key in kwargs:
                del kwargs[key]

        super().__init__(
            parent,
            text=text,
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            **style,
            **kwargs
        )


class MatrixIconButton(ctk.CTkButton):
    """Compact icon button for navigation tabs"""

    def __init__(self, parent, icon: str = "", label: str = "", active: bool = False, **kwargs):
        fg = COLORS["bg_active_nav"] if active else COLORS["bg_secondary"]
        border = COLORS["matrix_green"] if active else COLORS["border_green"]
        text_c = COLORS["matrix_green_bright"] if active else COLORS["matrix_green_dim"]

        kwargs.setdefault("width", 50)
        kwargs.setdefault("height", 44)
        kwargs.setdefault("corner_radius", RADIUS["md"])
        kwargs.setdefault("border_width", 1)

        display = f"{icon}\n{label}" if label else icon

        super().__init__(
            parent,
            text=display,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=fg,
            hover_color=COLORS["bg_hover"],
            border_color=border,
            text_color=text_c,
            **kwargs
        )
        self._is_active = active

    def set_active(self, active: bool):
        self._is_active = active
        if active:
            self.configure(
                fg_color=COLORS["bg_active_nav"],
                border_color=COLORS["matrix_green"],
                text_color=COLORS["matrix_green_bright"]
            )
        else:
            self.configure(
                fg_color=COLORS["bg_secondary"],
                border_color=COLORS["border_green"],
                text_color=COLORS["matrix_green_dim"]
            )


class MatrixEntry(ctk.CTkEntry):
    """Matrix-styled entry field"""

    def __init__(self, parent, **kwargs):
        # Apply Matrix style
        for key, value in ENTRY_STYLE.items():
            if key not in kwargs:
                kwargs[key] = value

        super().__init__(
            parent,
            font=ctk.CTkFont(family="Consolas", size=13),
            **kwargs
        )


class MatrixTextbox(ctk.CTkTextbox):
    """Matrix-styled textbox"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_input"])
        kwargs.setdefault("border_color", COLORS["border_green"])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("text_color", COLORS["matrix_green"])
        kwargs.setdefault("corner_radius", 4)
        kwargs.setdefault("font", ctk.CTkFont(family="Consolas", size=13))

        super().__init__(parent, **kwargs)


class MatrixLabel(ctk.CTkLabel):
    """Matrix-styled label"""

    def __init__(self, parent, text: str = "", size: str = "md", bright: bool = False, **kwargs):
        sizes = {
            "xs": FONTS["size_xs"],
            "sm": FONTS["size_sm"],
            "md": FONTS["size_md"],
            "lg": FONTS["size_lg"],
            "xl": FONTS["size_xl"],
            "xxl": FONTS["size_xxl"],
            "title": FONTS["size_title"],
        }

        color = COLORS["matrix_green_bright"] if bright else COLORS["matrix_green"]
        kwargs.setdefault("text_color", color)

        super().__init__(
            parent,
            text=text,
            font=ctk.CTkFont(family="Consolas", size=sizes.get(size, FONTS["size_md"])),
            **kwargs
        )


class MatrixFrame(ctk.CTkFrame):
    """Matrix-styled frame with border"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_card"])
        kwargs.setdefault("border_color", COLORS["border_green"])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("corner_radius", 6)

        super().__init__(parent, **kwargs)


class MatrixScrollableFrame(ctk.CTkScrollableFrame):
    """Matrix-styled scrollable frame with Linux mousewheel support"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_secondary"])
        kwargs.setdefault("border_color", COLORS["border_green"])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("corner_radius", 4)
        kwargs.setdefault("scrollbar_button_color", COLORS["matrix_green_dark"])
        kwargs.setdefault("scrollbar_button_hover_color", COLORS["matrix_green_dim"])

        super().__init__(parent, **kwargs)

        # Bind mousewheel ONCE on the canvas only — no recursive child binding,
        # no <Configure> re-binding.  This avoids the previous memory leak where
        # duplicate handlers accumulated on every resize event.
        canvas = self._parent_canvas
        canvas.bind("<Button-4>", self._on_mousewheel, add="+")   # Linux scroll up
        canvas.bind("<Button-5>", self._on_mousewheel, add="+")   # Linux scroll down
        canvas.bind("<MouseWheel>", self._on_mousewheel, add="+") # Windows/Mac
        log.debug("MatrixScrollableFrame: mousewheel bound once on canvas")

    def _on_mousewheel(self, event):
        """Handle mousewheel scroll across platforms"""
        try:
            canvas = self._parent_canvas
            # Check if content is taller than visible area
            if canvas.bbox("all") is None:
                return
            content_height = canvas.bbox("all")[3]
            visible_height = canvas.winfo_height()
            if content_height <= visible_height:
                return

            if event.num == 4:  # Linux scroll up
                canvas.yview_scroll(-3, "units")
            elif event.num == 5:  # Linux scroll down
                canvas.yview_scroll(3, "units")
            elif hasattr(event, 'delta'):  # Windows/Mac
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass


class MatrixComboBox(ctk.CTkComboBox):
    """Matrix-styled combobox"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_input"])
        kwargs.setdefault("border_color", COLORS["border_green"])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("button_color", COLORS["matrix_green_dark"])
        kwargs.setdefault("button_hover_color", COLORS["matrix_green_dim"])
        kwargs.setdefault("dropdown_fg_color", COLORS["bg_secondary"])
        kwargs.setdefault("dropdown_hover_color", COLORS["bg_hover"])
        kwargs.setdefault("dropdown_text_color", COLORS["matrix_green"])
        kwargs.setdefault("text_color", COLORS["matrix_green"])
        kwargs.setdefault("corner_radius", 4)

        super().__init__(
            parent,
            font=ctk.CTkFont(family="Consolas", size=13),
            dropdown_font=ctk.CTkFont(family="Consolas", size=12),
            **kwargs
        )


class MatrixSlider(ctk.CTkSlider):
    """Matrix-styled slider"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_tertiary"])
        kwargs.setdefault("progress_color", COLORS["matrix_green_dark"])
        kwargs.setdefault("button_color", COLORS["matrix_green"])
        kwargs.setdefault("button_hover_color", COLORS["matrix_green_bright"])

        super().__init__(parent, **kwargs)


class MatrixProgressBar(ctk.CTkProgressBar):
    """Matrix-styled progress bar"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_tertiary"])
        kwargs.setdefault("progress_color", COLORS["matrix_green"])
        kwargs.setdefault("border_color", COLORS["border_green"])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("corner_radius", 4)

        super().__init__(parent, **kwargs)


class TerminalHeader(ctk.CTkFrame):
    """Terminal-style header with decorations"""

    def __init__(self, parent, title: str, subtitle: str = "", **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_tertiary"])
        kwargs.setdefault("border_color", COLORS["matrix_green_dim"])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("corner_radius", 0)

        super().__init__(parent, **kwargs)

        self.grid_columnconfigure(1, weight=1)

        # Decorative dots (like terminal window)
        dots_frame = ctk.CTkFrame(self, fg_color="transparent")
        dots_frame.grid(row=0, column=0, padx=10, pady=8)

        for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
            dot = ctk.CTkLabel(
                dots_frame,
                text="●",
                text_color=color,
                font=ctk.CTkFont(size=10),
                width=15
            )
            dot.pack(side="left", padx=2)

        # Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=1, sticky="w", padx=10)

        MatrixLabel(
            title_frame,
            text=f"[ {title} ]",
            size="md",
            bright=True
        ).pack(side="left")

        if subtitle:
            MatrixLabel(
                title_frame,
                text=f" // {subtitle}",
                size="sm",
                text_color=COLORS["text_muted"]
            ).pack(side="left", padx=(10, 0))

        # Accent line at bottom
        accent = ctk.CTkFrame(self, fg_color=COLORS["matrix_green_dark"], height=1)
        accent.grid(row=1, column=0, columnspan=3, sticky="ew")


class StatusIndicator(ctk.CTkFrame):
    """Animated status indicator"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self.status = "disconnected"
        self.animating = False

        self.indicator = ctk.CTkLabel(
            self,
            text="○",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["error"]
        )
        self.indicator.pack(side="left", padx=(0, 5))

        self.label = MatrixLabel(self, text="OFFLINE", size="sm")
        self.label.pack(side="left")

    def set_status(self, status: str, text: str = ""):
        """Set status: connected, disconnected, loading"""
        self.status = status

        colors = {
            "connected": COLORS["success"],
            "disconnected": COLORS["error"],
            "loading": COLORS["warning"],
        }

        symbols = {
            "connected": "●",
            "disconnected": "○",
            "loading": "◐",
        }

        default_texts = {
            "connected": "ONLINE",
            "disconnected": "OFFLINE",
            "loading": "CONNECTING...",
        }

        self.indicator.configure(
            text=symbols.get(status, "○"),
            text_color=colors.get(status, COLORS["text_muted"])
        )
        self.label.configure(text=text or default_texts.get(status, status.upper()))

        if status == "loading" and not self.animating:
            self._start_animation()
        else:
            self.animating = False

    def _start_animation(self):
        """Animate loading indicator"""
        self.animating = True
        frames = ["◐", "◓", "◑", "◒"]
        idx = [0]

        def animate():
            if not self.animating:
                return
            self.indicator.configure(text=frames[idx[0] % len(frames)])
            idx[0] += 1
            self.after(150, animate)

        animate()


class GlowingTitle(ctk.CTkFrame):
    """Title with Matrix glow effect"""

    def __init__(self, parent, text: str, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        # Shadow/glow layer (behind)
        self.shadow = ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(family="Consolas", size=32, weight="bold"),
            text_color=COLORS["matrix_green_dark"]
        )
        self.shadow.place(x=2, y=2)

        # Main text
        self.main = ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(family="Consolas", size=32, weight="bold"),
            text_color=COLORS["matrix_green_bright"]
        )
        self.main.pack()


class MatrixSeparator(ctk.CTkFrame):
    """Decorative separator line"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLORS["border_green"])
        kwargs.setdefault("height", 1)

        super().__init__(parent, **kwargs)


class TypewriterLabel(ctk.CTkLabel):
    """Label with typewriter animation effect"""

    def __init__(self, parent, text: str = "", speed: int = 30, **kwargs):
        kwargs.setdefault("text_color", COLORS["matrix_green"])
        kwargs.setdefault("font", ctk.CTkFont(family="Consolas", size=13))

        super().__init__(parent, text="", **kwargs)

        self.full_text = text
        self.speed = speed
        self.current_idx = 0

        if text:
            self.start_typing()

    def start_typing(self, text: str = None):
        """Start typewriter animation"""
        if text:
            self.full_text = text
        self.current_idx = 0
        self._type_next()

    def _type_next(self):
        if self.current_idx <= len(self.full_text):
            self.configure(text=self.full_text[:self.current_idx] + "▌")
            self.current_idx += 1
            self.after(self.speed, self._type_next)
        else:
            self.configure(text=self.full_text)
