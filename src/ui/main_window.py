"""Matrix-styled Main Application Window"""
import customtkinter as ctk
from tkinter import messagebox
from typing import Optional
from pathlib import Path
import threading
import random
from PIL import Image, ImageTk

from .widgets import (
    MatrixFrame, MatrixButton, MatrixLabel, MatrixComboBox,
    StatusIndicator, GlowingTitle, MatrixScrollableFrame, MatrixEntry,
    MatrixIconButton
)
from .theme import COLORS, DECORATIONS, ASCII_LOGO, NAV_ICONS, RADIUS
from .chat_panel import ChatPanel
from .model_manager import ModelManagerPanel
from .settings_panel import SettingsPanel
from .help_panel import HelpPanel
from .system_panel import SystemPanel
from ..core import OllamaClient, GGUFManager, TranslationService, ChatStorage


class MatrixRain(ctk.CTkCanvas):
    """Matrix rain effect background"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("bg", COLORS["bg_dark"])
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)

        self.chars = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789"
        self.drops = []
        self.running = False

    def start(self):
        """Start the rain animation"""
        self.running = True
        self.update_idletasks()
        width = self.winfo_width()
        cols = width // 15
        self.drops = [random.randint(-20, 0) for _ in range(cols)]
        self._animate()

    def stop(self):
        """Stop the animation"""
        self.running = False

    def _animate(self):
        if not self.running:
            return

        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()

        for i, drop in enumerate(self.drops):
            x = i * 15
            char = random.choice(self.chars)

            # Bright leading character
            self.create_text(
                x, drop * 15,
                text=char,
                fill=COLORS["matrix_green_bright"],
                font=("Consolas", 12)
            )

            # Trail
            for j in range(1, 8):
                trail_y = (drop - j) * 15
                if trail_y > 0:
                    alpha_color = COLORS["matrix_green_dark"]
                    self.create_text(
                        x, trail_y,
                        text=random.choice(self.chars),
                        fill=alpha_color,
                        font=("Consolas", 10)
                    )

            self.drops[i] += 1
            if self.drops[i] * 15 > height + 100:
                self.drops[i] = random.randint(-10, 0)

        self.after(80, self._animate)


class Sidebar(ctk.CTkFrame):
    """Matrix-styled sidebar"""

    def __init__(self, parent, on_nav: callable, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_secondary"])
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", COLORS["border_green"])

        super().__init__(parent, **kwargs)

        self.on_nav = on_nav
        self.current_panel = "chat"

        self._setup_ui()

    def _setup_ui(self):
        """Setup sidebar UI"""
        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Compact Logo + Status ──
        logo_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        logo_frame.grid(row=0, column=0, sticky="ew")
        logo_frame.grid_columnconfigure(0, weight=1)

        logo_row = ctk.CTkFrame(logo_frame, fg_color="transparent")
        logo_row.pack(fill="x", padx=12, pady=10)
        logo_row.grid_columnconfigure(1, weight=1)

        logo_text = f"{DECORATIONS['block_dark']}{DECORATIONS['block']}{DECORATIONS['block_dark']}"
        ctk.CTkLabel(
            logo_row,
            text=logo_text,
            font=ctk.CTkFont(family="Consolas", size=16),
            text_color=COLORS["matrix_green"],
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkLabel(
            logo_row,
            text="DRAGO RUNNER",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLORS["matrix_green_bright"],
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        self.status_indicator = StatusIndicator(logo_row)
        self.status_indicator.grid(row=0, column=2, padx=(4, 0))

        self.gpu_label = ctk.CTkLabel(
            logo_frame,
            text=f"  {DECORATIONS['arrow_r']} GPU: Detecting...",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.gpu_label.pack(fill="x", padx=12, pady=(0, 6))

        # ── Model Selector ──
        model_frame = ctk.CTkFrame(self, fg_color="transparent")
        model_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(8, 4))
        model_frame.grid_columnconfigure(0, weight=1)

        MatrixLabel(
            model_frame,
            text=f"{DECORATIONS['block']} MODELO",
            size="xs",
            bright=True,
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.model_combo = MatrixComboBox(model_frame, values=["Loading..."])
        self.model_combo.grid(row=1, column=0, sticky="ew")

        refresh_btn = MatrixButton(
            model_frame,
            text=f"{DECORATIONS['block_med']} Refresh",
            height=26,
            command=lambda: self.on_nav("refresh_models"),
        )
        refresh_btn.grid(row=2, column=0, sticky="ew", pady=(4, 0))

        # ── Horizontal Nav Tabs ──
        nav_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        nav_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=(8, 0))

        nav_inner = ctk.CTkFrame(nav_frame, fg_color="transparent")
        nav_inner.pack(fill="x", padx=6, pady=6)
        for i in range(5):
            nav_inner.grid_columnconfigure(i, weight=1)

        self.nav_buttons = {}
        nav_items = [
            ("chat", NAV_ICONS["chat"], "CHAT"),
            ("models", NAV_ICONS["models"], "FORGE"),
            ("system", NAV_ICONS["system"], "SYS"),
            ("help", NAV_ICONS["help"], "HELP"),
            ("settings", NAV_ICONS["settings"], "CFG"),
        ]

        for idx, (name, icon, label) in enumerate(nav_items):
            is_active = (name == "chat")
            btn = MatrixIconButton(
                nav_inner,
                icon=icon,
                label=label,
                active=is_active,
                command=lambda n=name: self._on_nav_click(n),
            )
            btn.grid(row=0, column=idx, padx=2, sticky="ew")
            self.nav_buttons[name] = btn

        # ── Separator ──
        sep = ctk.CTkFrame(self, fg_color=COLORS["border_green"], height=1)
        sep.grid(row=3, column=0, sticky="ew", padx=10, pady=6)

        # ── Chat List Section ──
        chats_frame = ctk.CTkFrame(self, fg_color="transparent")
        chats_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))
        chats_frame.grid_rowconfigure(2, weight=1)
        chats_frame.grid_columnconfigure(0, weight=1)

        chats_header = ctk.CTkFrame(chats_frame, fg_color="transparent")
        chats_header.grid(row=0, column=0, sticky="ew")
        chats_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            chats_header,
            text=f" {DECORATIONS['h_line']*3} CHATS {DECORATIONS['h_line']*3}",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"],
        ).grid(row=0, column=0, sticky="w")

        new_chat_btn = MatrixButton(
            chats_header,
            text=f"{DECORATIONS['prompt']} NEW",
            height=24,
            width=60,
            command=lambda: self.on_nav("new_chat"),
        )
        new_chat_btn.grid(row=0, column=1, sticky="e")

        self.chat_search = MatrixEntry(
            chats_frame,
            placeholder_text="Search chats...",
            height=28,
        )
        self.chat_search.grid(row=1, column=0, sticky="ew", pady=(6, 4))
        self.chat_search.bind("<KeyRelease>", lambda e: self.on_nav("search_chats"))

        self.chat_list_frame = MatrixScrollableFrame(
            chats_frame,
            fg_color=COLORS["bg_dark"],
            border_width=1,
            border_color=COLORS["border_green"],
        )
        self.chat_list_frame.grid(row=2, column=0, sticky="nsew")
        self.chat_list_frame.grid_columnconfigure(0, weight=1)

    def _on_nav_click(self, panel_name: str):
        """Handle navigation click"""
        self.current_panel = panel_name

        for name, btn in self.nav_buttons.items():
            btn.set_active(name == panel_name)

        self.on_nav(panel_name)

    def set_status(self, status: str, text: str = ""):
        """Update status indicator"""
        self.status_indicator.set_status(status, text)

    def set_gpu_info(self, info: str):
        """Update GPU info"""
        self.gpu_label.configure(text=f"  {DECORATIONS['arrow_r']} GPU: {info}")

    def update_models(self, models: list, current: str = None):
        """Update model list"""
        if models:
            self.model_combo.configure(values=models)
            if current:
                self.model_combo.set(current)
            elif models:
                self.model_combo.set(models[0])
        else:
            self.model_combo.configure(values=["No models"])
            self.model_combo.set("No models")

    def get_selected_model(self) -> str:
        """Get selected model name"""
        return self.model_combo.get()

    def set_model_callback(self, callback):
        """Set callback for model selection"""
        self.model_combo.configure(command=callback)

    def update_chat_list(self, chats: list, active_id: str = None):
        """Update the chat list display.

        Args:
            chats: List of dicts with id, title, updated_at
            active_id: ID of the currently active chat
        """
        # Clear existing items
        for widget in self.chat_list_frame.winfo_children():
            widget.destroy()

        self._chat_items = {}

        for chat in chats:
            item = self._create_chat_item(chat, is_active=(chat["id"] == active_id))
            item.pack(fill="x", pady=2, padx=4)
            self._chat_items[chat["id"]] = item

    def _create_chat_item(self, chat: dict, is_active: bool = False) -> ctk.CTkFrame:
        """Create a single chat list item."""
        bg = COLORS["bg_tertiary"] if is_active else COLORS["bg_dark"]
        border = COLORS["matrix_green"] if is_active else COLORS["border_green"]

        item = ctk.CTkFrame(
            self.chat_list_frame,
            fg_color=bg,
            border_color=border,
            border_width=1,
            corner_radius=4,
            height=40,
        )
        item.grid_columnconfigure(0, weight=1)
        item.grid_propagate(False)

        # Title
        title = chat.get("title", "Untitled")
        if len(title) > 22:
            title = title[:22] + "..."
        title_label = ctk.CTkLabel(
            item,
            text=title,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["matrix_green"] if is_active else COLORS["matrix_green_dim"],
            anchor="w",
        )
        title_label.grid(row=0, column=0, sticky="w", padx=8, pady=(4, 0))

        # Date
        date_str = chat.get("updated_at", "")[:10]
        ctk.CTkLabel(
            item,
            text=date_str,
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 4))

        # Delete button
        del_btn = ctk.CTkButton(
            item,
            text=DECORATIONS["cross"],
            font=ctk.CTkFont(family="Consolas", size=11),
            width=24,
            height=24,
            fg_color="transparent",
            hover_color="#330011",
            text_color=COLORS["text_muted"],
            command=lambda cid=chat["id"]: self.on_nav(f"delete_chat:{cid}"),
        )
        del_btn.grid(row=0, column=1, rowspan=2, sticky="e", padx=4)

        # Click to load chat
        chat_id = chat["id"]
        for widget in [item, title_label]:
            widget.bind("<Button-1>", lambda e, cid=chat_id: self.on_nav(f"load_chat:{cid}"))

        return item

    def get_search_query(self) -> str:
        """Get current search text."""
        return self.chat_search.get().strip()


class MainWindow(ctk.CTk):
    """Matrix-styled main application window"""

    def __init__(self, config_path: Path):
        super().__init__()

        # Set WM_CLASS to match .desktop StartupWMClass for dock icon
        self.tk.call('tk', 'appname', 'drago-model-runner')

        # Set window icon
        icon_path = Path(__file__).parent.parent.parent / "icon.png"
        if icon_path.exists():
            icon_image = Image.open(icon_path)
            self._icon_photo = ImageTk.PhotoImage(icon_image)
            self.iconphoto(True, self._icon_photo)

        self.config_path = config_path
        self.current_model: Optional[str] = None

        # Debounce timer for chat list refresh
        self._refresh_timer: Optional[str] = None

        # Initialize core
        self._init_core()

        # Window setup
        self.title("DRAGO Model Runner // Matrix Edition")
        self.geometry("1600x1000")
        self.minsize(1200, 800)
        self.configure(fg_color=COLORS["bg_dark"])

        # Scale UI based on system DPI (96 = standard, 144 = 150%, 192 = 200%)
        dpi_scale = self._detect_system_scale()
        ctk.set_widget_scaling(dpi_scale)
        ctk.set_window_scaling(dpi_scale)

        # Setup UI
        self._setup_ui()

        # Initial checks
        self.after(100, self._startup_sequence)

    def _detect_system_scale(self) -> float:
        """Detect system DPI/scaling and return a customtkinter scale factor.

        On GNOME fractional scaling (X11), the system renders at 2x DPI (192)
        and then xrandr downscales the framebuffer.  We detect the real
        physical resolution vs the virtual resolution to find the actual
        user-facing scale factor.
        """
        import subprocess as sp, os, re

        dpi = 96  # default

        # 1. Try Xft.dpi from X resources
        try:
            result = sp.run(
                ["xrdb", "-query"], capture_output=True, text=True, timeout=3
            )
            for line in result.stdout.splitlines():
                if "Xft.dpi" in line:
                    dpi = int(line.split(":")[-1].strip())
                    break
        except Exception:
            pass

        # 2. Fallback: GDK_SCALE env var
        if dpi == 96:
            gdk = os.environ.get("GDK_SCALE", "")
            if gdk.isdigit() and int(gdk) > 1:
                dpi = 96 * int(gdk)

        system_factor = dpi / 96.0  # e.g. 2.0 for 192 dpi

        # 3. On GNOME fractional scaling, detect xrandr downscale
        #    (physical res vs virtual res gives the framebuffer transform)
        xrandr_correction = 1.0
        try:
            result = sp.run(
                ["xrandr", "--query"], capture_output=True, text=True, timeout=3
            )
            # Find connected primary: virtual resolution and native mode
            virtual_w = None
            native_w = None
            lines = result.stdout.splitlines()
            for i, line in enumerate(lines):
                if "connected primary" in line:
                    # e.g. "eDP-1-1 connected primary 3408x2130+0+0 ..."
                    m = re.search(r'(\d+)x(\d+)\+', line)
                    if m:
                        virtual_w = int(m.group(1))
                    # Next line has native resolution: "  2560x1600  240.00*+"
                    for j in range(i + 1, min(i + 5, len(lines))):
                        m2 = re.search(r'^\s+(\d+)x(\d+)\s+.*\*', lines[j])
                        if m2:
                            native_w = int(m2.group(1))
                            break
                    break

            if virtual_w and native_w and virtual_w > native_w:
                # Framebuffer is upscaled: transform = virtual / native
                # Real user scale = dpi_factor / transform
                transform = virtual_w / native_w
                xrandr_correction = 1.0 / transform
        except Exception:
            pass

        # Final scale: system DPI factor corrected by xrandr transform
        # e.g. 150%: dpi=192 → factor=2.0, transform=1.33 → 2.0/1.33 = 1.5
        scale = round(system_factor * xrandr_correction, 2)

        # Clamp to reasonable range
        return max(1.0, min(scale, 3.5))

    def _init_core(self):
        """Initialize core components"""
        import json
        settings = {}
        try:
            if self.config_path.exists():
                settings = json.loads(self.config_path.read_text())
        except Exception:
            pass

        ollama_config = settings.get("ollama", {})
        self.ollama = OllamaClient(
            host=ollama_config.get("host", "http://localhost:11434"),
            timeout=ollama_config.get("timeout", 120)
        )

        paths_config = settings.get("paths", {})
        models_dir = paths_config.get("models_dir", "~/ai-models")
        self.gguf_manager = GGUFManager([models_dir])

        # Translation
        translation_config = settings.get("translation", {})
        self.translation_enabled = translation_config.get("enabled", True)
        self.translation_source = translation_config.get("source_lang", "es")
        self.translation_target = translation_config.get("target_lang", "en")
        self.auto_translate_input = translation_config.get("auto_translate_input", True)
        self.translator = TranslationService.get_instance()

        # Chat storage
        self.chat_storage = ChatStorage()
        self.active_chat_id: Optional[str] = None

    def _setup_ui(self):
        """Setup main UI"""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = Sidebar(self, on_nav=self._on_nav, width=280)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.set_model_callback(self._on_model_selected)

        # Main content area
        self.content_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_primary"],
            corner_radius=0
        )
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Cancel event and generation tracking for STOP button
        self._chat_cancel_event: Optional[threading.Event] = None
        self._generation_id: int = 0

        # Create panels
        self.chat_panel = ChatPanel(
            self.content_frame,
            on_send=self._on_chat_send,
            on_stop=self._on_chat_stop
        )
        self.chat_panel.set_chat_callback(self._on_chat_data_updated)

        self.models_panel = ModelManagerPanel(
            self.content_frame,
            self.ollama,
            self.gguf_manager,
            on_model_created=self._on_model_created
        )

        self.system_panel = SystemPanel(self.content_frame)

        self.help_panel = HelpPanel(self.content_frame)

        self.settings_panel = SettingsPanel(
            self.content_frame,
            self.config_path,
            on_settings_changed=self._on_settings_changed
        )

        # Show chat by default
        self._show_panel("chat")

    def _startup_sequence(self):
        """Run startup sequence"""
        self.sidebar.set_status("loading", "Initializing...")

        def startup():
            # Check Ollama
            is_running = self.ollama.is_running()

            # Initialize translation
            if self.translation_enabled:
                def on_trans_progress(msg):
                    self.after(0, lambda: self.sidebar.set_status("loading", msg))

                def on_trans_complete(success):
                    self.after(0, lambda: self.chat_panel.set_translator(
                        self.translator,
                        self.translation_source,
                        self.translation_target,
                        self.auto_translate_input
                    ))

                self.translator.initialize(
                    source_lang=self.translation_source,
                    target_lang=self.translation_target,
                    on_progress=on_trans_progress,
                    on_complete=on_trans_complete,
                )

            # Detect GPU
            gpu_info = self._detect_gpu()

            def update():
                if is_running:
                    self.sidebar.set_status("connected", "Ollama Online")
                    self._refresh_models()
                else:
                    self.sidebar.set_status("disconnected", "Ollama Offline")
                    self._prompt_start_ollama()

                self.sidebar.set_gpu_info(gpu_info)

                # Load last chat or create new
                self._load_last_or_new_chat()
                self._refresh_chat_list()

            self.after(0, update)

        threading.Thread(target=startup, daemon=True).start()

    def _detect_gpu(self) -> str:
        """Detect GPU info"""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return "Not detected"

    def _prompt_start_ollama(self):
        """Prompt to start Ollama"""
        if messagebox.askyesno(
            "Ollama Offline",
            "Ollama is not running.\nStart Ollama server now?"
        ):
            self._start_ollama()

    def _start_ollama(self):
        """Try to start Ollama"""
        self.sidebar.set_status("loading", "Starting Ollama...")

        def start():
            success = self.ollama.start_server()

            def update():
                if success:
                    self.sidebar.set_status("connected", "Ollama Online")
                    self._refresh_models()
                else:
                    self.sidebar.set_status("disconnected", "Start Failed")
                    messagebox.showerror(
                        "Error",
                        "Could not start Ollama.\nRun 'ollama serve' manually."
                    )

            self.after(0, update)

        threading.Thread(target=start, daemon=True).start()

    def _refresh_models(self):
        """Refresh model list"""
        def fetch():
            models = self.ollama.list_models()
            model_names = [m.name for m in models]

            def update():
                if model_names:
                    current = self.current_model if self.current_model in model_names else None
                    self.sidebar.update_models(model_names, current)
                    if not self.current_model:
                        self.current_model = model_names[0]
                else:
                    self.sidebar.update_models([])

            self.after(0, update)

        threading.Thread(target=fetch, daemon=True).start()

    def _on_nav(self, panel_name: str):
        """Handle navigation"""
        if panel_name == "refresh_models":
            self._refresh_models()
        elif panel_name == "new_chat":
            self._create_new_chat()
            self._show_panel("chat")
            self.sidebar._on_nav_click("chat")
        elif panel_name == "search_chats":
            self._refresh_chat_list()
        elif panel_name.startswith("load_chat:"):
            self._load_chat(panel_name.split(":", 1)[1])
        elif panel_name.startswith("delete_chat:"):
            self._delete_chat(panel_name.split(":", 1)[1])
        else:
            self._show_panel(panel_name)

    def _show_panel(self, panel_name: str):
        """Show specified panel"""
        self.chat_panel.grid_remove()
        self.models_panel.grid_remove()
        self.system_panel.grid_remove()
        self.help_panel.grid_remove()
        self.settings_panel.grid_remove()

        panels = {
            "chat": self.chat_panel,
            "models": self.models_panel,
            "system": self.system_panel,
            "help": self.help_panel,
            "settings": self.settings_panel,
        }

        if panel_name in panels:
            panels[panel_name].grid(row=0, column=0, sticky="nsew")

    def _on_model_selected(self, model_name: str):
        """Handle model selection and load its system prompt"""
        if model_name not in ["No models", "Loading..."]:
            self.current_model = model_name
            self._load_model_system_prompt(model_name)

    def _load_model_system_prompt(self, model_name: str):
        """Load system prompt from the model's Modelfile in background"""
        import subprocess as sp

        def fetch():
            prompt = ""
            try:
                result = sp.run(
                    ["ollama", "show", model_name, "--modelfile"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    in_system = False
                    lines = []
                    for line in result.stdout.splitlines():
                        if line.strip().upper().startswith("SYSTEM"):
                            in_system = True
                            # Content after SYSTEM keyword on same line
                            rest = line.strip()[6:].strip().strip('"').strip()
                            if rest:
                                lines.append(rest)
                            continue
                        if in_system:
                            # SYSTEM block ends at next keyword or triple-quote
                            if line.strip().startswith(('FROM ', 'PARAMETER ', 'TEMPLATE ', 'LICENSE ')):
                                break
                            if line.strip() == '"""':
                                if lines:
                                    break
                                continue
                            lines.append(line)
                    prompt = "\n".join(lines).strip()
            except Exception:
                pass

            def apply():
                self.chat_panel.set_system_prompt(prompt)

            self.after(0, apply)

        threading.Thread(target=fetch, daemon=True).start()

    def _on_model_created(self, model_name: str):
        """Handle new model created"""
        self._refresh_models()
        self.current_model = model_name
        self._show_panel("chat")
        self.sidebar._on_nav_click("chat")

    def _on_settings_changed(self, settings: dict):
        """Handle settings change"""
        ollama_config = settings.get("ollama", {})
        self.ollama = OllamaClient(
            host=ollama_config.get("host", "http://localhost:11434"),
            timeout=ollama_config.get("timeout", 120)
        )

        paths_config = settings.get("paths", {})
        models_dir = paths_config.get("models_dir", "~/ai-models")
        self.gguf_manager = GGUFManager([models_dir])

        translation_config = settings.get("translation", {})
        self.translation_enabled = translation_config.get("enabled", True)
        self.translation_source = translation_config.get("source_lang", "es")
        self.translation_target = translation_config.get("target_lang", "en")
        self.auto_translate_input = translation_config.get("auto_translate_input", True)

        self._startup_sequence()

    def _on_chat_stop(self):
        """Handle STOP button - cancel the running generation thread"""
        if self._chat_cancel_event:
            self._chat_cancel_event.set()

    def _on_chat_send(self, message: str):
        """Handle chat message"""
        model = self.sidebar.get_selected_model()

        if not model or model in ["No models", "Loading..."]:
            messagebox.showwarning("Warning", "Select a model first")
            self.chat_panel._toggle_generating(False)
            return

        self.current_model = model

        # Cancel any previous generation
        if self._chat_cancel_event:
            self._chat_cancel_event.set()

        # New cancel event and generation id for this request
        self._chat_cancel_event = threading.Event()
        self._generation_id += 1
        gen_id = self._generation_id
        cancel_event = self._chat_cancel_event

        # Start streaming response
        self.chat_panel.start_assistant_message()

        # Get messages and translate if needed
        messages = self.chat_panel.get_messages()
        if self.auto_translate_input and self.translator.is_ready() and self.chat_panel.translate_toggle_on():
            translated_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    translated_text = self.translator.translate(
                        msg["content"], self.translation_source, self.translation_target
                    )
                    translated_messages.append({"role": "user", "content": translated_text})
                else:
                    translated_messages.append(msg)
            messages = translated_messages

        options = {
            "temperature": 0.7,
            "top_p": 0.9
        }

        def on_token(t):
            # Discard tokens from stale generations
            if gen_id != self._generation_id:
                return
            self.after(0, lambda: self.chat_panel.append_to_assistant(t))

        def on_complete():
            if gen_id != self._generation_id:
                return
            self.after(0, self.chat_panel.finish_assistant_message)

        def on_error(e):
            if gen_id != self._generation_id:
                return
            self.after(0, lambda: self._on_chat_error(e))

        self.ollama.chat_async(
            model=model,
            messages=messages,
            on_token=on_token,
            on_complete=on_complete,
            on_error=on_error,
            options=options,
            cancel_event=cancel_event
        )

    def _load_last_or_new_chat(self):
        """Load the most recent chat or create a new one."""
        chats = self.chat_storage.list_chats()
        if chats:
            chat_data = self.chat_storage.load_chat(chats[0]["id"])
            if chat_data:
                self.active_chat_id = chat_data["id"]
                self.chat_panel.load_chat(chat_data)
                return
        # No chats exist, create new
        self._create_new_chat()

    def _create_new_chat(self):
        """Create a new empty chat session."""
        model = self.sidebar.get_selected_model()
        if model in ["No models", "Loading..."]:
            model = ""
        chat = self.chat_storage.new_chat(model=model)
        self.active_chat_id = chat["id"]
        self.chat_panel.clear_chat()
        self.chat_panel.set_current_chat(chat)
        self._refresh_chat_list()

    def _on_chat_data_updated(self, chat_data):
        """Called by ChatPanel when messages change (auto-save)."""
        if chat_data is None:
            # Chat was cleared — create new
            self._create_new_chat()
            return
        chat_data["model"] = self.current_model or ""
        self.chat_storage.save_chat(chat_data)
        # Debounced refresh — avoids re-rendering the sidebar on every token
        self._schedule_refresh_chat_list()

    def _schedule_refresh_chat_list(self, delay_ms: int = 500):
        """Schedule a chat list refresh with debounce.

        Multiple calls within *delay_ms* are collapsed into one.
        """
        if self._refresh_timer is not None:
            self.after_cancel(self._refresh_timer)
        self._refresh_timer = self.after(delay_ms, self._refresh_chat_list)

    def _refresh_chat_list(self):
        """Refresh the chat list in the sidebar (fast — reads from cache)."""
        self._refresh_timer = None
        query = self.sidebar.get_search_query()
        if query:
            chats = self.chat_storage.search_chats(query)
        else:
            chats = self.chat_storage.list_chats()
        self.sidebar.update_chat_list(chats, self.active_chat_id)

    def _load_chat(self, chat_id: str):
        """Load a specific chat."""
        chat_data = self.chat_storage.load_chat(chat_id)
        if chat_data:
            self.active_chat_id = chat_id
            self.chat_panel.load_chat(chat_data)
            self._refresh_chat_list()
            # Switch to chat panel if not already there
            self._show_panel("chat")
            self.sidebar._on_nav_click("chat")

    def _delete_chat(self, chat_id: str):
        """Delete a chat with confirmation."""
        if not messagebox.askyesno("Delete Chat", "Are you sure you want to delete this chat?"):
            return
        self.chat_storage.delete_chat(chat_id)
        if chat_id == self.active_chat_id:
            self._load_last_or_new_chat()
        self._refresh_chat_list()

    def _on_chat_error(self, error: str):
        """Handle chat error"""
        self.chat_panel.finish_assistant_message()
        messagebox.showerror("Error", f"Chat error: {error}")
