"""Matrix-styled Main Application Window"""
import customtkinter as ctk
from tkinter import messagebox
from typing import Optional
from pathlib import Path
import threading
import random

from .theme import COLORS, DECORATIONS, ASCII_LOGO
from .widgets import (
    MatrixFrame, MatrixButton, MatrixLabel, MatrixComboBox,
    StatusIndicator, GlowingTitle
)
from .chat_panel import ChatPanel
from .model_manager import ModelManagerPanel
from .settings_panel import SettingsPanel
from ..core import OllamaClient, GGUFManager


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
        self.grid_rowconfigure(5, weight=1)

        # Logo area with Matrix effect
        logo_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        logo_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # ASCII Logo
        logo_text = """
╔══════════════════════╗
║  ██████╗ ██████╗     ║
║  ██╔══██╗██╔══██╗    ║
║  ██║  ██║██████╔╝    ║
║  ██║  ██║██╔══██╗    ║
║  ██████╔╝██║  ██║    ║
║  ╚═════╝ ╚═╝  ╚═╝    ║
║    DRAGO RUNNER      ║
╚══════════════════════╝"""

        logo_label = ctk.CTkLabel(
            logo_frame,
            text=logo_text,
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=COLORS["matrix_green"],
            justify="center"
        )
        logo_label.pack(pady=15)

        # Separator
        sep = ctk.CTkFrame(self, fg_color=COLORS["border_green"], height=1)
        sep.grid(row=1, column=0, sticky="ew", padx=10)

        # Model selector
        model_frame = ctk.CTkFrame(self, fg_color="transparent")
        model_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=15)

        MatrixLabel(
            model_frame,
            text=f"{DECORATIONS['block']} ACTIVE MODEL",
            size="sm",
            bright=True
        ).pack(anchor="w", pady=(0, 8))

        self.model_combo = MatrixComboBox(
            model_frame,
            values=["Loading..."],
            width=200
        )
        self.model_combo.pack(fill="x")

        refresh_btn = MatrixButton(
            model_frame,
            text=f"{DECORATIONS['block_med']} Refresh",
            height=28,
            command=lambda: self.on_nav("refresh_models")
        )
        refresh_btn.pack(fill="x", pady=(8, 0))

        # Status indicator
        status_frame = MatrixFrame(self)
        status_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        status_header = ctk.CTkLabel(
            status_frame,
            text=f" {DECORATIONS['h_line']*3} STATUS {DECORATIONS['h_line']*3}",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"]
        )
        status_header.pack(anchor="w", padx=10, pady=(8, 5))

        self.status_indicator = StatusIndicator(status_frame)
        self.status_indicator.pack(anchor="w", padx=15, pady=(0, 10))

        # GPU info
        self.gpu_label = ctk.CTkLabel(
            status_frame,
            text=f"  {DECORATIONS['arrow_r']} GPU: Detecting...",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"]
        )
        self.gpu_label.pack(anchor="w", padx=10, pady=(0, 10))

        # Separator
        sep2 = ctk.CTkFrame(self, fg_color=COLORS["border_green"], height=1)
        sep2.grid(row=4, column=0, sticky="ew", padx=10, pady=5)

        # Navigation buttons
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.grid(row=5, column=0, sticky="nsew", padx=10, pady=10)

        self.nav_buttons = {}

        nav_items = [
            ("chat", f"{DECORATIONS['prompt']} NEURAL CHAT", True),
            ("models", f"{DECORATIONS['block']} MODEL FORGE", False),
            ("settings", f"{DECORATIONS['arrow_r']} CONFIG", False),
        ]

        for name, text, is_active in nav_items:
            btn = MatrixButton(
                nav_frame,
                text=text,
                height=40,
                primary=is_active,
                command=lambda n=name: self._on_nav_click(n)
            )
            btn.pack(fill="x", pady=4)
            self.nav_buttons[name] = btn

        # Version info at bottom
        version_frame = ctk.CTkFrame(self, fg_color="transparent")
        version_frame.grid(row=6, column=0, sticky="sew", padx=10, pady=10)

        ctk.CTkLabel(
            version_frame,
            text=f"{DECORATIONS['h_line']*8}\nv1.0.0 // Matrix Edition\n{DECORATIONS['h_line']*8}",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=COLORS["text_muted"],
            justify="center"
        ).pack()

    def _on_nav_click(self, panel_name: str):
        """Handle navigation click"""
        self.current_panel = panel_name

        # Update button styles
        for name, btn in self.nav_buttons.items():
            if name == panel_name:
                btn.configure(
                    fg_color=COLORS["matrix_green_dark"],
                    border_color=COLORS["matrix_green"],
                    text_color=COLORS["bg_dark"]
                )
            else:
                btn.configure(
                    fg_color=COLORS["bg_tertiary"],
                    border_color=COLORS["matrix_green_dim"],
                    text_color=COLORS["matrix_green"]
                )

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


class MainWindow(ctk.CTk):
    """Matrix-styled main application window"""

    def __init__(self, config_path: Path):
        super().__init__()

        self.config_path = config_path
        self.current_model: Optional[str] = None

        # Initialize core
        self._init_core()

        # Window setup
        self.title("DRAGO Model Runner // Matrix Edition")
        self.geometry("1600x1000")
        self.minsize(1200, 800)
        self.configure(fg_color=COLORS["bg_dark"])

        # Scale up UI elements
        ctk.set_widget_scaling(1.2)
        ctk.set_window_scaling(1.2)

        # Setup UI
        self._setup_ui()

        # Initial checks
        self.after(100, self._startup_sequence)

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

        # Create panels
        self.chat_panel = ChatPanel(
            self.content_frame,
            on_send=self._on_chat_send
        )

        self.models_panel = ModelManagerPanel(
            self.content_frame,
            self.ollama,
            self.gguf_manager,
            on_model_created=self._on_model_created
        )

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
        else:
            self._show_panel(panel_name)

    def _show_panel(self, panel_name: str):
        """Show specified panel"""
        self.chat_panel.grid_remove()
        self.models_panel.grid_remove()
        self.settings_panel.grid_remove()

        panels = {
            "chat": self.chat_panel,
            "models": self.models_panel,
            "settings": self.settings_panel,
        }

        if panel_name in panels:
            panels[panel_name].grid(row=0, column=0, sticky="nsew")

    def _on_model_selected(self, model_name: str):
        """Handle model selection"""
        if model_name not in ["No models", "Loading..."]:
            self.current_model = model_name

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

        self._startup_sequence()

    def _on_chat_send(self, message: str):
        """Handle chat message"""
        model = self.sidebar.get_selected_model()

        if not model or model in ["No models", "Loading..."]:
            messagebox.showwarning("Warning", "Select a model first")
            self.chat_panel._toggle_generating(False)
            return

        self.current_model = model

        # Start streaming response
        self.chat_panel.start_assistant_message()

        messages = self.chat_panel.get_messages()

        options = {
            "temperature": 0.7,
            "top_p": 0.9
        }

        self.ollama.chat_async(
            model=model,
            messages=messages,
            on_token=lambda t: self.after(0, lambda: self.chat_panel.append_to_assistant(t)),
            on_complete=lambda: self.after(0, self.chat_panel.finish_assistant_message),
            on_error=lambda e: self.after(0, lambda: self._on_chat_error(e)),
            options=options
        )

    def _on_chat_error(self, error: str):
        """Handle chat error"""
        self.chat_panel.finish_assistant_message()
        messagebox.showerror("Error", f"Chat error: {error}")
