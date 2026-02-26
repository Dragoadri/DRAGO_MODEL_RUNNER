"""Matrix-styled Settings Panel"""
import customtkinter as ctk
from tkinter import filedialog
from typing import Callable, Optional
from pathlib import Path
import json

from .theme import COLORS, DECORATIONS, RADIUS
from .widgets import (
    MatrixFrame, MatrixButton, MatrixEntry, MatrixLabel,
    MatrixComboBox, TerminalHeader, MatrixScrollableFrame
)


class SettingsPanel(ctk.CTkFrame):
    """Matrix-styled settings panel"""

    def __init__(
        self,
        parent,
        config_path: Path,
        on_settings_changed: Optional[Callable[[dict], None]] = None,
        **kwargs
    ):
        kwargs.setdefault("fg_color", COLORS["bg_primary"])
        kwargs.setdefault("corner_radius", 0)

        super().__init__(parent, **kwargs)

        self.config_path = config_path
        self.on_settings_changed = on_settings_changed
        self.settings = self._load_settings()

        self._setup_ui()

    def _load_settings(self) -> dict:
        """Load settings from file"""
        try:
            if self.config_path.exists():
                return json.loads(self.config_path.read_text())
        except Exception:
            pass

        return {
            "ollama": {"host": "http://localhost:11434", "timeout": 120},
            "ui": {"theme": "dark", "font_size": 14},
            "paths": {"models_dir": "~/ai-models"},
            "translation": {
                "enabled": True,
                "source_lang": "es",
                "target_lang": "en",
                "auto_translate_input": True
            }
        }

    def _save_settings(self):
        """Save settings to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(json.dumps(self.settings, indent=2))
            if self.on_settings_changed:
                self.on_settings_changed(self.settings)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def _setup_ui(self):
        """Setup settings UI"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = TerminalHeader(self, "SYSTEM CONFIG", "settings.json")
        header.grid(row=0, column=0, sticky="ew")

        # Scrollable content
        content = MatrixScrollableFrame(self, fg_color=COLORS["bg_primary"], border_width=0)
        content.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        content.grid_columnconfigure(0, weight=1)

        # === OLLAMA SECTION ===
        ollama_section = self._create_section(content, "OLLAMA CONNECTION")
        ollama_section.pack(fill="x", pady=(0, 20))

        ollama_grid = MatrixFrame(ollama_section)
        ollama_grid.pack(fill="x", padx=15, pady=15)
        ollama_grid.grid_columnconfigure(1, weight=1)

        # Host
        MatrixLabel(ollama_grid, text=f"{DECORATIONS['arrow_r']} Host:", size="sm").grid(
            row=0, column=0, padx=15, pady=10, sticky="w"
        )
        self.host_entry = MatrixEntry(ollama_grid, width=350)
        self.host_entry.insert(0, self.settings["ollama"]["host"])
        self.host_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Timeout
        MatrixLabel(ollama_grid, text=f"{DECORATIONS['arrow_r']} Timeout (s):", size="sm").grid(
            row=1, column=0, padx=15, pady=10, sticky="w"
        )
        self.timeout_entry = MatrixEntry(ollama_grid, width=100)
        self.timeout_entry.insert(0, str(self.settings["ollama"]["timeout"]))
        self.timeout_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        # Test connection button
        test_btn = MatrixButton(
            ollama_grid,
            text=f"{DECORATIONS['block_med']} TEST CONNECTION",
            command=self._test_connection
        )
        test_btn.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        self.connection_status = MatrixLabel(
            ollama_grid,
            text="",
            size="sm"
        )
        self.connection_status.grid(row=2, column=0, padx=15, pady=10, sticky="w")

        # === UI SECTION ===
        ui_section = self._create_section(content, "INTERFACE")
        ui_section.pack(fill="x", pady=(0, 20))

        ui_grid = MatrixFrame(ui_section)
        ui_grid.pack(fill="x", padx=15, pady=15)
        ui_grid.grid_columnconfigure(1, weight=1)

        # Theme
        MatrixLabel(ui_grid, text=f"{DECORATIONS['arrow_r']} Theme:", size="sm").grid(
            row=0, column=0, padx=15, pady=10, sticky="w"
        )
        self.theme_combo = MatrixComboBox(
            ui_grid,
            values=["dark", "light", "system"],
            command=self._on_theme_change,
            width=150
        )
        self.theme_combo.set(self.settings["ui"].get("theme", "dark"))
        self.theme_combo.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Font size
        MatrixLabel(ui_grid, text=f"{DECORATIONS['arrow_r']} Font Size:", size="sm").grid(
            row=1, column=0, padx=15, pady=10, sticky="w"
        )
        self.font_combo = MatrixComboBox(
            ui_grid,
            values=["12", "13", "14", "16", "18"],
            width=100
        )
        self.font_combo.set(str(self.settings["ui"].get("font_size", 14)))
        self.font_combo.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        # === PATHS SECTION ===
        paths_section = self._create_section(content, "PATHS")
        paths_section.pack(fill="x", pady=(0, 20))

        paths_grid = MatrixFrame(paths_section)
        paths_grid.pack(fill="x", padx=15, pady=15)
        paths_grid.grid_columnconfigure(1, weight=1)

        # Models directory
        MatrixLabel(paths_grid, text=f"{DECORATIONS['arrow_r']} Models Dir:", size="sm").grid(
            row=0, column=0, padx=15, pady=10, sticky="w"
        )
        self.models_dir_entry = MatrixEntry(paths_grid, width=350)
        self.models_dir_entry.insert(0, self.settings["paths"]["models_dir"])
        self.models_dir_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        MatrixButton(
            paths_grid,
            text="BROWSE",
            width=80,
            command=self._browse_models_dir
        ).grid(row=0, column=2, padx=10, pady=10)

        # === TRANSLATION SECTION ===
        trans_section = self._create_section(content, "TRANSLATION")
        trans_section.pack(fill="x", pady=(0, 20))

        trans_grid = MatrixFrame(trans_section)
        trans_grid.pack(fill="x", padx=15, pady=15)
        trans_grid.grid_columnconfigure(1, weight=1)

        trans_config = self.settings.get("translation", {})

        # Enable translation
        MatrixLabel(trans_grid, text=f"{DECORATIONS['arrow_r']} Enabled:", size="sm").grid(
            row=0, column=0, padx=15, pady=10, sticky="w"
        )
        self.trans_enabled_switch = ctk.CTkSwitch(
            trans_grid,
            text="",
            width=40,
            height=20,
            fg_color=COLORS["bg_tertiary"],
            progress_color=COLORS["matrix_green_dark"],
            button_color=COLORS["matrix_green"],
            button_hover_color=COLORS["matrix_green_bright"],
        )
        if trans_config.get("enabled", True):
            self.trans_enabled_switch.select()
        self.trans_enabled_switch.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Source language (user's language)
        MatrixLabel(trans_grid, text=f"{DECORATIONS['arrow_r']} Your language:", size="sm").grid(
            row=1, column=0, padx=15, pady=10, sticky="w"
        )
        self.source_lang_combo = MatrixComboBox(
            trans_grid,
            values=["es", "fr", "de", "it", "pt", "zh", "ja", "ko", "ru", "ar"],
            width=100
        )
        self.source_lang_combo.set(trans_config.get("source_lang", "es"))
        self.source_lang_combo.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        # Target language (model's language)
        MatrixLabel(trans_grid, text=f"{DECORATIONS['arrow_r']} Model language:", size="sm").grid(
            row=2, column=0, padx=15, pady=10, sticky="w"
        )
        self.target_lang_combo = MatrixComboBox(
            trans_grid,
            values=["en", "es", "fr", "de", "zh", "ja"],
            width=100
        )
        self.target_lang_combo.set(trans_config.get("target_lang", "en"))
        self.target_lang_combo.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        # Auto-translate input
        MatrixLabel(trans_grid, text=f"{DECORATIONS['arrow_r']} Auto-translate input:", size="sm").grid(
            row=3, column=0, padx=15, pady=10, sticky="w"
        )
        self.auto_translate_switch = ctk.CTkSwitch(
            trans_grid,
            text="",
            width=40,
            height=20,
            fg_color=COLORS["bg_tertiary"],
            progress_color=COLORS["matrix_green_dark"],
            button_color=COLORS["matrix_green"],
            button_hover_color=COLORS["matrix_green_bright"],
        )
        if trans_config.get("auto_translate_input", True):
            self.auto_translate_switch.select()
        self.auto_translate_switch.grid(row=3, column=1, padx=10, pady=10, sticky="w")

        # === ABOUT SECTION ===
        about_section = self._create_section(content, "ABOUT")
        about_section.pack(fill="x", pady=(0, 20))

        about_text = f"""
{DECORATIONS['block']} DRAGO MODEL RUNNER v1.0
{DECORATIONS['h_line'] * 35}

Local LLM inference interface powered by Ollama.
Designed for running uncensored models locally.

{DECORATIONS['arrow_r']} GitHub: github.com/drago/model-runner
{DECORATIONS['arrow_r']} License: MIT

{DECORATIONS['h_line'] * 35}
v1.0.0 // Matrix Edition
        """

        about_label = ctk.CTkLabel(
            about_section,
            text=about_text,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=COLORS["text_muted"],
            justify="left",
            anchor="w",
            wraplength=600
        )
        about_label.pack(fill="x", padx=20, pady=15)

        def _update_about_wrap(event=None):
            try:
                about_label.configure(wraplength=max(200, about_section.winfo_width() - 60))
            except Exception:
                pass

        about_section.bind("<Configure>", _update_about_wrap, add="+")

        # === SAVE BUTTON ===
        save_frame = ctk.CTkFrame(content, fg_color="transparent")
        save_frame.pack(fill="x", pady=20)

        self.save_btn = MatrixButton(
            save_frame,
            text=f"{DECORATIONS['check']} SAVE CONFIGURATION",
            height=45,
            primary=True,
            command=self._apply_settings
        )
        self.save_btn.pack(pady=10)

        self.status_label = MatrixLabel(save_frame, text="", size="sm")
        self.status_label.pack()

    def _create_section(self, parent, title: str) -> ctk.CTkFrame:
        """Create a styled section"""
        section = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border_green"],
            border_width=1,
            corner_radius=RADIUS["lg"]
        )

        header = ctk.CTkFrame(section, fg_color=COLORS["bg_tertiary"], corner_radius=0)
        header.pack(fill="x")

        MatrixLabel(
            header,
            text=f" {DECORATIONS['corner_tl']}{DECORATIONS['h_line']*3} {title} {DECORATIONS['h_line']*3}{DECORATIONS['corner_tr']}",
            size="md",
            bright=True
        ).pack(anchor="w", padx=10, pady=8)

        return section

    def _on_theme_change(self, theme: str):
        """Handle theme change"""
        ctk.set_appearance_mode(theme)

    def _browse_models_dir(self):
        """Browse for models directory"""
        directory = filedialog.askdirectory(
            title="Select Models Directory",
            initialdir=str(Path(self.models_dir_entry.get()).expanduser())
        )
        if directory:
            self.models_dir_entry.delete(0, "end")
            self.models_dir_entry.insert(0, directory)

    def _test_connection(self):
        """Test Ollama connection"""
        import threading

        self.connection_status.configure(
            text=f"{DECORATIONS['block_med']} Testing...",
            text_color=COLORS["warning"]
        )

        def test():
            import httpx
            try:
                host = self.host_entry.get()
                with httpx.Client(timeout=5) as client:
                    response = client.get(f"{host}/api/tags")
                    success = response.status_code == 200
            except Exception:
                success = False

            def update():
                if success:
                    self.connection_status.configure(
                        text=f"{DECORATIONS['check']} Connected",
                        text_color=COLORS["success"]
                    )
                else:
                    self.connection_status.configure(
                        text=f"{DECORATIONS['cross']} Failed",
                        text_color=COLORS["error"]
                    )

            self.after(0, update)

        threading.Thread(target=test, daemon=True).start()

    def _apply_settings(self):
        """Apply and save settings"""
        self.settings["ollama"]["host"] = self.host_entry.get()
        self.settings["ollama"]["timeout"] = int(self.timeout_entry.get())
        self.settings["ui"]["theme"] = self.theme_combo.get()
        self.settings["ui"]["font_size"] = int(self.font_combo.get())
        self.settings["paths"]["models_dir"] = self.models_dir_entry.get()

        self.settings.setdefault("translation", {})
        self.settings["translation"]["enabled"] = self.trans_enabled_switch.get() == 1
        self.settings["translation"]["source_lang"] = self.source_lang_combo.get()
        self.settings["translation"]["target_lang"] = self.target_lang_combo.get()
        self.settings["translation"]["auto_translate_input"] = self.auto_translate_switch.get() == 1

        self._save_settings()

        self.status_label.configure(
            text=f"{DECORATIONS['check']} Configuration saved",
            text_color=COLORS["success"]
        )
        self.after(3000, lambda: self.status_label.configure(text=""))

    def get_settings(self) -> dict:
        """Get current settings"""
        return self.settings.copy()
