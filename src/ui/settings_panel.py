"""Matrix-styled Settings Panel"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Callable, Optional
from pathlib import Path
import json
import re

from ..utils.logger import get_logger
log = get_logger("settings_panel")

from .theme import COLORS, DECORATIONS, RADIUS
from .widgets import (
    MatrixFrame, MatrixButton, MatrixEntry, MatrixLabel,
    MatrixComboBox, TerminalHeader, MatrixScrollableFrame
)

DEFAULT_SETTINGS = {
    "ollama": {"host": "http://localhost:11434", "timeout": 120, "auto_start": False},
    "ui": {"theme": "dark", "font_size": 14},
    "paths": {"models_dir": "~/ai-models"},
    "chat": {"max_context_messages": 40},
    "translation": {
        "enabled": True,
        "source_lang": "es",
        "target_lang": "en",
        "auto_translate_input": True
    }
}


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
        """Load settings from file, merging with defaults"""
        defaults = json.loads(json.dumps(DEFAULT_SETTINGS))
        try:
            if self.config_path.exists():
                saved = json.loads(self.config_path.read_text())
                # Deep merge saved over defaults
                for section, values in saved.items():
                    if section in defaults and isinstance(values, dict):
                        defaults[section].update(values)
                    else:
                        defaults[section] = values
        except Exception:
            pass
        return defaults

    def _save_settings(self):
        """Save settings to file atomically."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.config_path.with_suffix(".json.tmp")
            tmp_path.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
            tmp_path.replace(self.config_path)  # atomic on POSIX
            if self.on_settings_changed:
                self.on_settings_changed(self.settings)
        except OSError as e:
            log.error("Error saving settings: %s", e)
            try:
                self.config_path.with_suffix(".json.tmp").unlink(missing_ok=True)
            except OSError:
                pass

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
        self.host_entry.bind("<KeyRelease>", self._validate_host_live)

        self.host_validation = ctk.CTkLabel(
            ollama_grid,
            text="",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"],
        )
        self.host_validation.grid(row=1, column=1, padx=10, pady=(0, 5), sticky="w")

        # Timeout
        MatrixLabel(ollama_grid, text=f"{DECORATIONS['arrow_r']} Timeout (s):", size="sm").grid(
            row=2, column=0, padx=15, pady=10, sticky="w"
        )
        self.timeout_entry = MatrixEntry(ollama_grid, width=100)
        self.timeout_entry.insert(0, str(self.settings["ollama"]["timeout"]))
        self.timeout_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        # Auto-start Ollama
        MatrixLabel(ollama_grid, text=f"{DECORATIONS['arrow_r']} Auto-start:", size="sm").grid(
            row=3, column=0, padx=15, pady=10, sticky="w"
        )
        auto_start_frame = ctk.CTkFrame(ollama_grid, fg_color="transparent")
        auto_start_frame.grid(row=3, column=1, padx=10, pady=10, sticky="w")

        self.auto_start_switch = ctk.CTkSwitch(
            auto_start_frame,
            text="",
            width=40,
            height=20,
            fg_color=COLORS["bg_tertiary"],
            progress_color=COLORS["matrix_green_dark"],
            button_color=COLORS["matrix_green"],
            button_hover_color=COLORS["matrix_green_bright"],
        )
        if self.settings["ollama"].get("auto_start", False):
            self.auto_start_switch.select()
        self.auto_start_switch.pack(side="left")

        ctk.CTkLabel(
            auto_start_frame,
            text="  Iniciar Ollama automaticamente al abrir la app",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"],
        ).pack(side="left")

        # Test connection button
        test_btn = MatrixButton(
            ollama_grid,
            text=f"{DECORATIONS['block_med']} TEST CONNECTION",
            command=self._test_connection
        )
        test_btn.grid(row=4, column=1, padx=10, pady=10, sticky="w")

        self.connection_status = MatrixLabel(
            ollama_grid,
            text="",
            size="sm"
        )
        self.connection_status.grid(row=4, column=0, padx=15, pady=10, sticky="w")

        # === CHAT SECTION ===
        chat_section = self._create_section(content, "CHAT")
        chat_section.pack(fill="x", pady=(0, 20))

        chat_grid = MatrixFrame(chat_section)
        chat_grid.pack(fill="x", padx=15, pady=15)
        chat_grid.grid_columnconfigure(1, weight=1)

        # Max context messages
        MatrixLabel(chat_grid, text=f"{DECORATIONS['arrow_r']} Max context messages:", size="sm").grid(
            row=0, column=0, padx=15, pady=10, sticky="w"
        )
        self.ctx_msgs_combo = MatrixComboBox(
            chat_grid,
            values=["10", "20", "40", "60", "80", "100"],
            width=100
        )
        self.ctx_msgs_combo.set(str(self.settings.get("chat", {}).get("max_context_messages", 40)))
        self.ctx_msgs_combo.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(
            chat_grid,
            text="Mensajes enviados al modelo (ventana deslizante). Mas = mas contexto, mas lento.",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"],
        ).grid(row=1, column=1, padx=10, pady=(0, 8), sticky="w")

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
{DECORATIONS['block']} DRAGO MODEL RUNNER v1.0.0
{DECORATIONS['h_line'] * 35}

Local LLM inference interface powered by Ollama.
Designed for running uncensored models locally.

{DECORATIONS['arrow_r']} Backend: Ollama (local inference)
{DECORATIONS['arrow_r']} Frontend: CustomTkinter (Python)
{DECORATIONS['arrow_r']} Translation: Argos Translate (offline)
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

        # === ACTION BUTTONS ===
        actions_frame = ctk.CTkFrame(content, fg_color="transparent")
        actions_frame.pack(fill="x", pady=20)

        # Save button
        self.save_btn = MatrixButton(
            actions_frame,
            text=f"{DECORATIONS['check']} SAVE CONFIGURATION",
            height=45,
            primary=True,
            command=self._apply_settings
        )
        self.save_btn.pack(pady=(0, 10))

        self.status_label = MatrixLabel(actions_frame, text="", size="sm")
        self.status_label.pack(pady=(0, 10))

        # Secondary action buttons row
        btn_row = ctk.CTkFrame(actions_frame, fg_color="transparent")
        btn_row.pack()

        MatrixButton(
            btn_row,
            text=f"{DECORATIONS['arrow_r']} RESET TO DEFAULTS",
            height=32,
            command=self._reset_to_defaults
        ).pack(side="left", padx=5)

        MatrixButton(
            btn_row,
            text=f"{DECORATIONS['arrow_r']} EXPORT",
            height=32,
            command=self._export_settings
        ).pack(side="left", padx=5)

        MatrixButton(
            btn_row,
            text=f"{DECORATIONS['arrow_r']} IMPORT",
            height=32,
            command=self._import_settings
        ).pack(side="left", padx=5)

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

    def _validate_host_live(self, event=None):
        """Validate Ollama host URL inline"""
        host = self.host_entry.get().strip()
        if not host:
            self.host_validation.configure(
                text=f"{DECORATIONS['cross']} URL requerida",
                text_color=COLORS["error"]
            )
            return

        # Check URL format
        url_pattern = re.compile(
            r'^https?://'
            r'[a-zA-Z0-9._-]+'
            r'(:\d{1,5})?'
            r'/?$'
        )
        if not url_pattern.match(host):
            self.host_validation.configure(
                text=f"{DECORATIONS['cross']} Formato invalido. Ej: http://localhost:11434",
                text_color=COLORS["error"]
            )
            return

        # Check port range if present
        port_match = re.search(r':(\d+)', host.split('//')[1] if '//' in host else host)
        if port_match:
            port = int(port_match.group(1))
            if port < 1 or port > 65535:
                self.host_validation.configure(
                    text=f"{DECORATIONS['cross']} Puerto invalido (1-65535)",
                    text_color=COLORS["error"]
                )
                return

        self.host_validation.configure(
            text=f"{DECORATIONS['check']} URL valida",
            text_color=COLORS["success"]
        )

    def _on_theme_change(self, theme: str):
        """Handle theme change -- apply live preview"""
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
            try:
                import httpx
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
        # Validate numeric fields before saving
        try:
            timeout_val = int(self.timeout_entry.get())
        except ValueError:
            messagebox.showerror("Invalid value", "Timeout must be a valid integer.")
            return

        try:
            font_size_val = int(self.font_combo.get())
        except ValueError:
            messagebox.showerror("Invalid value", "Font size must be a valid integer.")
            return

        try:
            ctx_msgs_val = int(self.ctx_msgs_combo.get())
        except ValueError:
            ctx_msgs_val = 40

        # Validate host URL
        host = self.host_entry.get().strip()
        if not host or not re.match(r'^https?://.+', host):
            messagebox.showerror("Invalid value", "Ollama host must be a valid URL (http://...)")
            return

        self.settings["ollama"]["host"] = host
        self.settings["ollama"]["timeout"] = timeout_val
        self.settings["ollama"]["auto_start"] = self.auto_start_switch.get() == 1
        self.settings["ui"]["theme"] = self.theme_combo.get()
        self.settings["ui"]["font_size"] = font_size_val
        self.settings["paths"]["models_dir"] = self.models_dir_entry.get()

        self.settings.setdefault("chat", {})
        self.settings["chat"]["max_context_messages"] = ctx_msgs_val

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

    def _reset_to_defaults(self):
        """Reset all settings to defaults"""
        if not messagebox.askyesno(
            "Reset Settings",
            "Restaurar todos los ajustes a los valores por defecto?\n\n"
            "Esto no se puede deshacer."
        ):
            return

        self.settings = json.loads(json.dumps(DEFAULT_SETTINGS))

        # Update UI fields
        self.host_entry.delete(0, "end")
        self.host_entry.insert(0, self.settings["ollama"]["host"])
        self.timeout_entry.delete(0, "end")
        self.timeout_entry.insert(0, str(self.settings["ollama"]["timeout"]))
        self.auto_start_switch.deselect()
        self.theme_combo.set(self.settings["ui"]["theme"])
        self.font_combo.set(str(self.settings["ui"]["font_size"]))
        self.models_dir_entry.delete(0, "end")
        self.models_dir_entry.insert(0, self.settings["paths"]["models_dir"])
        self.ctx_msgs_combo.set(str(self.settings["chat"]["max_context_messages"]))
        self.trans_enabled_switch.select()
        self.source_lang_combo.set(self.settings["translation"]["source_lang"])
        self.target_lang_combo.set(self.settings["translation"]["target_lang"])
        self.auto_translate_switch.select()
        self.host_validation.configure(text="")
        self.connection_status.configure(text="")

        self._save_settings()

        self.status_label.configure(
            text=f"{DECORATIONS['check']} Reset to defaults",
            text_color=COLORS["success"]
        )
        self.after(3000, lambda: self.status_label.configure(text=""))

    def _export_settings(self):
        """Export settings to a JSON file"""
        path = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="drago_settings.json",
        )
        if not path:
            return

        try:
            Path(path).write_text(json.dumps(self.settings, indent=2))
            self.status_label.configure(
                text=f"{DECORATIONS['check']} Exported to {Path(path).name}",
                text_color=COLORS["success"]
            )
            self.after(3000, lambda: self.status_label.configure(text=""))
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")

    def _import_settings(self):
        """Import settings from a JSON file"""
        path = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            imported = json.loads(Path(path).read_text())
            if not isinstance(imported, dict):
                messagebox.showerror("Import Error", "Invalid settings file format.")
                return

            if not messagebox.askyesno(
                "Import Settings",
                f"Importar ajustes desde {Path(path).name}?\n\n"
                "Los ajustes actuales seran reemplazados."
            ):
                return

            self.settings = imported

            # Refresh UI from imported settings
            self.host_entry.delete(0, "end")
            self.host_entry.insert(0, self.settings.get("ollama", {}).get("host", "http://localhost:11434"))
            self.timeout_entry.delete(0, "end")
            self.timeout_entry.insert(0, str(self.settings.get("ollama", {}).get("timeout", 120)))
            if self.settings.get("ollama", {}).get("auto_start", False):
                self.auto_start_switch.select()
            else:
                self.auto_start_switch.deselect()
            self.theme_combo.set(self.settings.get("ui", {}).get("theme", "dark"))
            self.font_combo.set(str(self.settings.get("ui", {}).get("font_size", 14)))
            self.models_dir_entry.delete(0, "end")
            self.models_dir_entry.insert(0, self.settings.get("paths", {}).get("models_dir", "~/ai-models"))
            self.ctx_msgs_combo.set(str(self.settings.get("chat", {}).get("max_context_messages", 40)))

            trans = self.settings.get("translation", {})
            if trans.get("enabled", True):
                self.trans_enabled_switch.select()
            else:
                self.trans_enabled_switch.deselect()
            self.source_lang_combo.set(trans.get("source_lang", "es"))
            self.target_lang_combo.set(trans.get("target_lang", "en"))
            if trans.get("auto_translate_input", True):
                self.auto_translate_switch.select()
            else:
                self.auto_translate_switch.deselect()

            self._save_settings()

            self.status_label.configure(
                text=f"{DECORATIONS['check']} Imported from {Path(path).name}",
                text_color=COLORS["success"]
            )
            self.after(3000, lambda: self.status_label.configure(text=""))

        except json.JSONDecodeError:
            messagebox.showerror("Import Error", "File is not valid JSON.")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import: {e}")

    def get_settings(self) -> dict:
        """Get current settings"""
        return self.settings.copy()
