"""Matrix-styled Model Management Panel with Drag & Drop"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Callable, Optional
from pathlib import Path
import threading
import os

# Optional drag and drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    DND_FILES = None

from .theme import COLORS, DECORATIONS, RADIUS
from .widgets import (
    MatrixFrame, MatrixButton, MatrixEntry, MatrixTextbox,
    MatrixLabel, MatrixComboBox, MatrixSlider, MatrixProgressBar,
    TerminalHeader, MatrixScrollableFrame
)
from ..core import GGUFManager, ModelConfig, ModelParameters, OllamaClient
from ..core.model_config import SYSTEM_PROMPTS
from .system_panel import SystemInfo, estimate_model_performance


class DropZone(ctk.CTkFrame):
    """Drag and drop zone for GGUF files"""

    def __init__(self, parent, on_file_dropped: Callable[[str], None], **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["matrix_green_dim"],
            border_width=2,
            corner_radius=8,
            **kwargs
        )

        self.on_file_dropped = on_file_dropped
        self.selected_file: Optional[str] = None

        self._setup_ui()
        self._setup_dnd()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Content frame
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.place(relx=0.5, rely=0.5, anchor="center")

        # Icon
        self.icon_label = ctk.CTkLabel(
            content,
            text="[ GGUF ]",
            font=ctk.CTkFont(family="Consolas", size=28, weight="bold"),
            text_color=COLORS["matrix_green_dim"]
        )
        self.icon_label.pack(pady=(0, 10))

        # Main text
        self.main_label = ctk.CTkLabel(
            content,
            text="ARRASTRA UN ARCHIVO GGUF AQUI",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLORS["matrix_green"]
        )
        self.main_label.pack()

        # Sub text
        self.sub_label = ctk.CTkLabel(
            content,
            text="o haz clic para explorar",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=COLORS["text_muted"]
        )
        self.sub_label.pack(pady=(5, 0))

        # File info (hidden initially)
        self.file_label = ctk.CTkLabel(
            content,
            text="",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=COLORS["matrix_green_bright"],
            wraplength=350
        )
        self.file_label.pack(pady=(10, 0))

        # Bind click recursively to all children
        self._bind_click_recursive(self)

    def _bind_click_recursive(self, widget):
        """Bind click to widget and all children recursively"""
        widget.bind("<Button-1>", self._on_click, add="+")
        for child in widget.winfo_children():
            self._bind_click_recursive(child)

    def _setup_dnd(self):
        """Setup drag and drop - fallback if tkinterdnd2 not available"""
        if not DND_AVAILABLE or DND_FILES is None:
            # Update text to indicate DnD is not available
            self.after(100, lambda: self.sub_label.configure(
                text="haz clic aqui para explorar archivos"
            ))
            return

        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._on_drop)
            self.dnd_bind('<<DragEnter>>', self._on_drag_enter)
            self.dnd_bind('<<DragLeave>>', self._on_drag_leave)
        except Exception:
            self.after(100, lambda: self.sub_label.configure(
                text="haz clic aqui para explorar archivos"
            ))

    def _get_initial_dir(self) -> str:
        """Get the best initial directory for the file browser"""
        candidates = [
            Path.home() / "ai-models",
            Path.home() / "Descargas",
            Path.home() / "Downloads",
            Path.home() / "Escritorio",
            Path.home() / "Desktop",
            Path.home(),
        ]
        for path in candidates:
            if path.exists() and path.is_dir():
                return str(path)
        return str(Path.home())

    def _on_click(self, event=None):
        """Handle click to browse"""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo GGUF",
            filetypes=[
                ("GGUF files", "*.gguf"),
                ("Binary files", "*.bin"),
                ("All files", "*.*")
            ],
            initialdir=self._get_initial_dir()
        )
        if file_path:
            self._set_file(file_path)

    def _on_drop(self, event):
        """Handle file drop"""
        # Handle multiple file path formats from different DnD sources
        data = event.data.strip()
        # Remove curly braces (Tk wraps paths with spaces)
        if data.startswith('{') and data.endswith('}'):
            file_path = data[1:-1]
        else:
            # Could be multiple files separated by space, take first
            file_path = data.split()[0] if data else ""

        # Remove file:// URI prefix if present
        if file_path.startswith("file://"):
            file_path = file_path[7:]

        # URL-decode (e.g. %20 -> space)
        try:
            from urllib.parse import unquote
            file_path = unquote(file_path)
        except ImportError:
            pass

        if file_path and file_path.lower().endswith(('.gguf', '.bin')):
            self._set_file(file_path)
        elif file_path:
            messagebox.showwarning("Formato invalido", "Solo se aceptan archivos .gguf o .bin")

    def _on_drag_enter(self, event):
        self.configure(border_color=COLORS["matrix_green_bright"])

    def _on_drag_leave(self, event):
        self.configure(border_color=COLORS["matrix_green_dim"])

    def _set_file(self, file_path: str):
        """Set selected file"""
        self.selected_file = file_path
        filename = Path(file_path).name
        size_gb = Path(file_path).stat().st_size / (1024**3)

        self.icon_label.configure(text=DECORATIONS["check"], text_color=COLORS["success"])
        self.main_label.configure(text="ARCHIVO CARGADO")
        self.sub_label.configure(text="clic para cambiar")
        self.file_label.configure(text=f"{filename}\n[{size_gb:.2f} GB]")
        self.configure(border_color=COLORS["success"])

        # Estimate performance
        self._show_performance_estimate(size_gb)

        if self.on_file_dropped:
            self.on_file_dropped(file_path)

    def _show_performance_estimate(self, size_gb: float):
        """Show performance estimate for the model"""
        import threading

        def analyze():
            gpu_info = SystemInfo.get_gpu_info()
            mem_info = SystemInfo.get_memory_info()
            estimate = estimate_model_performance(size_gb, gpu_info, mem_info)

            def update():
                # Create or update performance label
                if hasattr(self, 'perf_label'):
                    self.perf_label.destroy()

                rating = estimate["speed_rating"]
                colors = {
                    "EXCELENTE": COLORS["success"],
                    "MUY BUENO": COLORS["success"],
                    "BUENO": COLORS["matrix_green"],
                    "ACEPTABLE": COLORS["warning"],
                    "LENTO": COLORS["accent_orange"],
                    "MUY LENTO": COLORS["error"],
                    "NO PUEDE EJECUTAR": COLORS["error"],
                }

                color = colors.get(rating, COLORS["text_muted"])

                perf_text = f"\n{DECORATIONS['arrow_r']} Rendimiento: {rating}"
                if estimate["will_use_gpu"]:
                    perf_text += f" (GPU)"
                else:
                    perf_text += f" (CPU)"

                if estimate["warnings"]:
                    perf_text += f"\n{DECORATIONS['circle']} {estimate['warnings'][0][:50]}"

                self.perf_label = ctk.CTkLabel(
                    self.winfo_children()[0],  # content frame
                    text=perf_text,
                    font=ctk.CTkFont(family="Consolas", size=11),
                    text_color=color,
                    wraplength=350
                )
                self.perf_label.pack(pady=(5, 0))

            self.after(0, update)

        threading.Thread(target=analyze, daemon=True).start()

    def reset(self):
        """Reset to initial state"""
        self.selected_file = None
        self.icon_label.configure(text="[ GGUF ]", text_color=COLORS["matrix_green_dim"])
        self.main_label.configure(text="ARRASTRA UN ARCHIVO GGUF AQUI")
        self.sub_label.configure(text="o haz clic para explorar")
        self.file_label.configure(text="")
        self.configure(border_color=COLORS["matrix_green_dim"])
        if hasattr(self, 'perf_label'):
            self.perf_label.destroy()


class ModelCard(ctk.CTkFrame):
    """Matrix-styled model info card"""

    def __init__(self, parent, model_name: str, model_size: str, on_delete: Callable, **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border_green"],
            border_width=1,
            corner_radius=4,
            **kwargs
        )

        self.model_name = model_name
        self.grid_columnconfigure(1, weight=1)

        icon_label = ctk.CTkLabel(
            self,
            text=DECORATIONS["block"],
            font=ctk.CTkFont(family="Consolas", size=20),
            text_color=COLORS["matrix_green"],
            width=40
        )
        icon_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

        name_label = ctk.CTkLabel(
            self,
            text=model_name,
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLORS["matrix_green_bright"],
            anchor="w",
            wraplength=400
        )
        name_label.grid(row=0, column=1, sticky="ew", padx=5, pady=(10, 0))

        size_label = ctk.CTkLabel(
            self,
            text=f"Size: {model_size}",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        size_label.grid(row=1, column=1, sticky="w", padx=5, pady=(0, 10))

        del_btn = ctk.CTkButton(
            self,
            text=DECORATIONS["cross"],
            font=ctk.CTkFont(family="Consolas", size=14),
            width=35,
            height=35,
            fg_color="#220000",
            hover_color="#440000",
            border_color=COLORS["error"],
            border_width=1,
            text_color=COLORS["error"],
            command=lambda: on_delete(model_name)
        )
        del_btn.grid(row=0, column=2, rowspan=2, padx=10, pady=10)


class ModelManagerPanel(ctk.CTkFrame):
    """Matrix-styled model management panel"""

    def __init__(
        self,
        parent,
        ollama_client: OllamaClient,
        gguf_manager: GGUFManager,
        on_model_created: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        kwargs.setdefault("fg_color", COLORS["bg_primary"])
        kwargs.setdefault("corner_radius", 0)

        super().__init__(parent, **kwargs)

        self.ollama = ollama_client
        self.gguf_manager = gguf_manager
        self.on_model_created = on_model_created
        self.selected_gguf_path: Optional[str] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup model manager UI"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = TerminalHeader(self, "MODEL FORGE", "crear y gestionar modelos")
        header.grid(row=0, column=0, sticky="ew")

        # Main scrollable content
        self.content = MatrixScrollableFrame(self, fg_color=COLORS["bg_primary"], border_width=0)
        self.content.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.content.grid_columnconfigure(0, weight=1)

        # ═══════════════════════════════════════════════════════════
        # STEP 1: CARGAR ARCHIVO GGUF
        # ═══════════════════════════════════════════════════════════
        step1 = self._create_section(
            self.content, "PASO 1: CARGAR ARCHIVO GGUF",
            description="Selecciona o arrastra un archivo .gguf desde tu disco. "
                        "Estos archivos contienen modelos de IA cuantizados listos para usar.",
            step_num=1
        )
        step1.pack(fill="x", pady=(0, 20))

        # Drop zone
        self.drop_zone = DropZone(step1, on_file_dropped=self._on_file_selected, height=150)
        self.drop_zone.pack(fill="x", padx=15, pady=15)

        # ═══════════════════════════════════════════════════════════
        # STEP 2: CONFIGURAR MODELO (MODELFILE)
        # ═══════════════════════════════════════════════════════════
        step2 = self._create_section(
            self.content, "PASO 2: CONFIGURAR MODELO (Modelfile)",
            description="Dale un nombre y configura el system prompt. "
                        "El nombre se usa para identificar tu modelo en Ollama.",
            step_num=2
        )
        step2.pack(fill="x", pady=(0, 20))

        config_frame = ctk.CTkFrame(step2, fg_color="transparent")
        config_frame.pack(fill="x", padx=15, pady=10)
        config_frame.grid_columnconfigure(1, weight=1)

        # Model Name
        MatrixLabel(config_frame, text="Nombre del modelo:", size="sm").grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        self.name_entry = MatrixEntry(config_frame, placeholder_text="mi-modelo-custom", width=300)
        self.name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # System Prompt Template
        MatrixLabel(config_frame, text="Plantilla de prompt:", size="sm").grid(
            row=1, column=0, padx=10, pady=10, sticky="w"
        )

        template_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        template_frame.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        self.prompt_preset = MatrixComboBox(
            template_frame,
            values=["-- Seleccionar --"] + list(SYSTEM_PROMPTS.keys()) + ["Personalizado"],
            command=self._on_preset_selected,
            width=200
        )
        self.prompt_preset.pack(side="left")

        # System Prompt Text
        MatrixLabel(config_frame, text="System Prompt:", size="sm").grid(
            row=2, column=0, padx=10, pady=(10, 5), sticky="nw"
        )

        prompt_container = ctk.CTkFrame(config_frame, fg_color="transparent")
        prompt_container.grid(row=2, column=1, padx=10, pady=(10, 5), sticky="ew")

        self.system_prompt = MatrixTextbox(prompt_container, height=120)
        self.system_prompt.pack(fill="x")

        hint_label = ctk.CTkLabel(
            prompt_container,
            text="Escribe las instrucciones de comportamiento para tu modelo",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"],
            wraplength=500
        )
        hint_label.pack(anchor="w", pady=(5, 0))

        # ═══════════════════════════════════════════════════════════
        # STEP 3: PARAMETROS DE INFERENCIA
        # ═══════════════════════════════════════════════════════════
        step3 = self._create_section(
            self.content, "PASO 3: PARAMETROS DE INFERENCIA",
            description="Ajusta los parametros de generacion. "
                        "Los valores por defecto funcionan bien para la mayoria de casos.",
            step_num=3
        )
        step3.pack(fill="x", pady=(0, 20))

        params_frame = ctk.CTkFrame(step3, fg_color="transparent")
        params_frame.pack(fill="x", padx=15, pady=10)
        params_frame.grid_columnconfigure((1, 3), weight=1)

        # Temperature
        MatrixLabel(params_frame, text="Temperature:", size="sm").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.temp_slider = MatrixSlider(params_frame, from_=0, to=2, number_of_steps=40)
        self.temp_slider.set(0.7)
        self.temp_slider.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        self.temp_label = MatrixLabel(params_frame, text="0.70", size="sm")
        self.temp_label.grid(row=0, column=2, padx=10, pady=8)
        self.temp_slider.configure(command=lambda v: self.temp_label.configure(text=f"{v:.2f}"))
        ctk.CTkLabel(params_frame, text="Bajo = preciso, Alto = creativo",
                     font=ctk.CTkFont(family="Consolas", size=10), text_color=COLORS["text_muted"]
                     ).grid(row=0, column=3, padx=10, pady=8, sticky="w")

        # Top P
        MatrixLabel(params_frame, text="Top P:", size="sm").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.top_p_slider = MatrixSlider(params_frame, from_=0, to=1, number_of_steps=20)
        self.top_p_slider.set(0.9)
        self.top_p_slider.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
        self.top_p_label = MatrixLabel(params_frame, text="0.90", size="sm")
        self.top_p_label.grid(row=1, column=2, padx=10, pady=8)
        self.top_p_slider.configure(command=lambda v: self.top_p_label.configure(text=f"{v:.2f}"))
        ctk.CTkLabel(params_frame, text="Diversidad de tokens. 0.9 = buen balance",
                     font=ctk.CTkFont(family="Consolas", size=10), text_color=COLORS["text_muted"]
                     ).grid(row=1, column=3, padx=10, pady=8, sticky="w")

        # Repeat Penalty
        MatrixLabel(params_frame, text="Repeat Penalty:", size="sm").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.repeat_slider = MatrixSlider(params_frame, from_=1, to=2, number_of_steps=20)
        self.repeat_slider.set(1.1)
        self.repeat_slider.grid(row=2, column=1, padx=10, pady=8, sticky="ew")
        self.repeat_label = MatrixLabel(params_frame, text="1.10", size="sm")
        self.repeat_label.grid(row=2, column=2, padx=10, pady=8)
        self.repeat_slider.configure(command=lambda v: self.repeat_label.configure(text=f"{v:.2f}"))
        ctk.CTkLabel(params_frame, text="Penaliza repeticiones. 1.1 = normal",
                     font=ctk.CTkFont(family="Consolas", size=10), text_color=COLORS["text_muted"]
                     ).grid(row=2, column=3, padx=10, pady=8, sticky="w")

        # Context Length
        MatrixLabel(params_frame, text="Context Length:", size="sm").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.ctx_combo = MatrixComboBox(
            params_frame,
            values=["2048", "4096", "8192", "16384", "32768"],
            width=120
        )
        self.ctx_combo.set("4096")
        self.ctx_combo.grid(row=3, column=1, padx=10, pady=8, sticky="w")
        ctk.CTkLabel(params_frame, text="Mas contexto = mas memoria. 4096 suficiente",
                     font=ctk.CTkFont(family="Consolas", size=10), text_color=COLORS["text_muted"]
                     ).grid(row=3, column=3, padx=10, pady=8, sticky="w")

        # ═══════════════════════════════════════════════════════════
        # STEP 4: CREAR MODELO
        # ═══════════════════════════════════════════════════════════
        step4 = self._create_section(
            self.content, "PASO 4: CREAR MODELO EN OLLAMA",
            description="Revisa la configuracion y crea tu modelo. "
                        "El proceso puede tardar unos segundos dependiendo del archivo.",
            step_num=4
        )
        step4.pack(fill="x", pady=(0, 20))

        create_frame = ctk.CTkFrame(step4, fg_color="transparent")
        create_frame.pack(fill="x", padx=15, pady=15)

        # Preview button
        preview_btn = ctk.CTkButton(
            create_frame,
            text="VER MODELFILE",
            font=ctk.CTkFont(family="Consolas", size=12),
            width=150,
            height=35,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["matrix_green_dim"],
            border_width=1,
            text_color=COLORS["matrix_green"],
            command=self._preview_modelfile
        )
        preview_btn.pack(side="left", padx=(0, 10))

        # Create button (disabled until a GGUF file is loaded)
        self.create_btn = ctk.CTkButton(
            create_frame,
            text=f"{DECORATIONS['block']} CREAR MODELO",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            width=200,
            height=45,
            fg_color=COLORS["matrix_green_dark"],
            hover_color=COLORS["matrix_green_dim"],
            border_color=COLORS["matrix_green"],
            border_width=1,
            text_color=COLORS["bg_dark"],
            command=self._create_model,
            state="disabled"
        )
        self.create_btn.pack(side="left", padx=10)

        # Reset button
        reset_btn = ctk.CTkButton(
            create_frame,
            text="RESET",
            font=ctk.CTkFont(family="Consolas", size=12),
            width=80,
            height=35,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["text_muted"],
            border_width=1,
            text_color=COLORS["text_muted"],
            command=self._reset_form
        )
        reset_btn.pack(side="left", padx=10)

        # Progress
        self.progress_frame = ctk.CTkFrame(step4, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.status_label = MatrixLabel(self.progress_frame, text="", size="sm")
        self.status_label.pack(anchor="w")

        self.progress = MatrixProgressBar(self.progress_frame)
        self.progress.set(0)

        # ═══════════════════════════════════════════════════════════
        # MODELOS INSTALADOS
        # ═══════════════════════════════════════════════════════════
        models_section = self._create_section(self.content, "MODELOS INSTALADOS EN OLLAMA")
        models_section.pack(fill="x", pady=(0, 20))

        self.models_list_frame = ctk.CTkFrame(models_section, fg_color="transparent")
        self.models_list_frame.pack(fill="x", padx=15, pady=10)

        refresh_btn = ctk.CTkButton(
            models_section,
            text=f"{DECORATIONS['block_med']} ACTUALIZAR LISTA",
            font=ctk.CTkFont(family="Consolas", size=12),
            width=180,
            height=35,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["matrix_green_dim"],
            border_width=1,
            text_color=COLORS["matrix_green"],
            command=self._refresh_models_list
        )
        refresh_btn.pack(pady=(0, 15))

        # Initial load
        self.after(500, self._refresh_models_list)

    def _create_section(
        self, parent, title: str,
        description: str = "", step_num: int = 0
    ) -> ctk.CTkFrame:
        """Create a styled section with optional description and step indicator"""
        section = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border_green"],
            border_width=1,
            corner_radius=RADIUS["lg"]
        )

        header = ctk.CTkFrame(section, fg_color=COLORS["bg_tertiary"], corner_radius=0)
        header.pack(fill="x")
        header.grid_columnconfigure(1, weight=1)

        # Step indicator (circle that becomes checkmark when completed)
        if step_num > 0:
            indicator = ctk.CTkLabel(
                header,
                text="\u25cb",  # empty circle
                font=ctk.CTkFont(family="Consolas", size=16),
                text_color=COLORS["text_muted"],
                width=30
            )
            indicator.grid(row=0, column=0, padx=(10, 0), pady=10)
            # Store reference for later update
            attr_name = f"_step{step_num}_indicator"
            setattr(self, attr_name, indicator)

        title_col = 1 if step_num > 0 else 0
        title_colspan = 1

        MatrixLabel(
            header,
            text=f" {DECORATIONS['arrow_r']} {title}",
            size="md",
            bright=True
        ).grid(row=0, column=title_col, sticky="w", padx=15 if step_num == 0 else 5, pady=10)

        # Description text below header
        if description:
            desc_label = ctk.CTkLabel(
                section,
                text=f"  {description}",
                font=ctk.CTkFont(family="Consolas", size=11),
                text_color=COLORS["text_muted"],
                anchor="w",
                wraplength=700
            )
            desc_label.pack(fill="x", padx=15, pady=(5, 0))

        return section

    def _mark_step_completed(self, step_num: int):
        """Mark a step indicator as completed (green checkmark)"""
        attr_name = f"_step{step_num}_indicator"
        indicator = getattr(self, attr_name, None)
        if indicator:
            indicator.configure(
                text=DECORATIONS["check"],
                text_color=COLORS["success"]
            )

    def _reset_step_indicator(self, step_num: int):
        """Reset a step indicator to empty circle"""
        attr_name = f"_step{step_num}_indicator"
        indicator = getattr(self, attr_name, None)
        if indicator:
            indicator.configure(
                text="\u25cb",
                text_color=COLORS["text_muted"]
            )

    @staticmethod
    def _sanitize_model_name(file_path: str) -> str:
        """Generate a valid Ollama model name from a GGUF filename.
        Ollama names: lowercase alphanumeric, hyphens allowed, no dots/underscores/uppercase.
        """
        import re
        stem = Path(file_path).stem.lower()

        # Remove quantization suffixes (q3_k_m, q4_k_s, etc.) and part numbers
        stem = re.sub(r'[-_]q\d+[-_]?k?[-_]?[a-z]?$', '', stem, flags=re.IGNORECASE)
        stem = re.sub(r'[-_]?\d{5}-of-\d{5}$', '', stem)

        # Replace non-alphanumeric chars with hyphens
        stem = re.sub(r'[^a-z0-9]', '-', stem)
        # Collapse multiple hyphens
        stem = re.sub(r'-{2,}', '-', stem)
        # Strip leading/trailing hyphens
        stem = stem.strip('-')

        # Truncate and ensure not empty
        stem = stem[:30].rstrip('-')
        return stem or "my-model"

    def _on_file_selected(self, file_path: str):
        """Handle file selection"""
        self.selected_gguf_path = file_path

        # Mark step 1 as completed and enable create button
        self._mark_step_completed(1)
        self.create_btn.configure(state="normal")

        # Always update name when a file is loaded
        suggested = self._sanitize_model_name(file_path)
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, suggested)

        # Auto-detect best system prompt based on model name
        filename_lower = Path(file_path).stem.lower()
        uncensored_keywords = ["dolphin", "uncensored", "abliterated", "nous-hermes"]
        code_keywords = ["code", "codellama", "starcoder", "deepseek-coder", "codegemma"]

        preset = None
        if any(kw in filename_lower for kw in uncensored_keywords):
            preset = "uncensored"
        elif any(kw in filename_lower for kw in code_keywords):
            preset = "coding"

        if preset and not self.system_prompt.get("1.0", "end-1c").strip():
            self.prompt_preset.set(preset)
            self.system_prompt.delete("1.0", "end")
            self.system_prompt.insert("1.0", SYSTEM_PROMPTS[preset])

    def _on_preset_selected(self, preset: str):
        """Handle preset selection"""
        if preset in SYSTEM_PROMPTS:
            self.system_prompt.delete("1.0", "end")
            self.system_prompt.insert("1.0", SYSTEM_PROMPTS[preset])

    def _preview_modelfile(self):
        """Show Modelfile preview"""
        if not self.selected_gguf_path:
            messagebox.showwarning("Aviso", "Primero selecciona un archivo GGUF")
            return

        params = ModelParameters(
            temperature=self.temp_slider.get(),
            top_p=self.top_p_slider.get(),
            repeat_penalty=self.repeat_slider.get(),
            num_ctx=int(self.ctx_combo.get())
        )

        config = ModelConfig(
            name=self.name_entry.get() or "mi-modelo",
            gguf_path=self.selected_gguf_path,
            system_prompt=self.system_prompt.get("1.0", "end-1c").strip(),
            parameters=params
        )

        modelfile_content = config.generate_modelfile()

        # Show in popup
        popup = ctk.CTkToplevel(self)
        popup.title("Modelfile Preview")
        popup.geometry("700x500")
        popup.minsize(400, 300)
        popup.configure(fg_color=COLORS["bg_primary"])

        MatrixLabel(popup, text="CONTENIDO DEL MODELFILE:", size="md", bright=True).pack(
            anchor="w", padx=20, pady=(20, 10)
        )

        text = MatrixTextbox(popup, height=350)
        text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        text.insert("1.0", modelfile_content)
        text.configure(state="disabled")

        close_btn = ctk.CTkButton(
            popup,
            text="CERRAR",
            command=popup.destroy
        )
        close_btn.pack(pady=(0, 20))

    def _create_model(self):
        """Create the model"""
        if not self.selected_gguf_path:
            messagebox.showerror("Error", "Selecciona un archivo GGUF primero (Paso 1)")
            return

        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Ingresa un nombre para el modelo (Paso 2)")
            return

        # Sanitize name for Ollama compatibility
        import re
        name = re.sub(r'[^a-z0-9-]', '-', name.lower())
        name = re.sub(r'-{2,}', '-', name).strip('-')
        if not name:
            messagebox.showerror("Error", "Nombre de modelo invalido")
            return
        # Update the entry to show the sanitized name
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, name)

        params = ModelParameters(
            temperature=self.temp_slider.get(),
            top_p=self.top_p_slider.get(),
            repeat_penalty=self.repeat_slider.get(),
            num_ctx=int(self.ctx_combo.get())
        )

        config = ModelConfig(
            name=name,
            gguf_path=self.selected_gguf_path,
            system_prompt=self.system_prompt.get("1.0", "end-1c").strip(),
            parameters=params
        )

        # Save Modelfile
        modelfile_path = Path(self.selected_gguf_path).parent / f"Modelfile_{name}"
        config.save_modelfile(modelfile_path)

        # Mark steps 2 and 3 as completed (config + params accepted)
        self._mark_step_completed(2)
        self._mark_step_completed(3)

        # Start creation
        self.create_btn.configure(state="disabled")
        self.progress.pack(fill="x", pady=(5, 0))
        self.progress.set(0)
        self.status_label.configure(text=f"{DECORATIONS['block_med']} Creando modelo...")

        def do_create():
            progress_val = [0]

            def on_progress(status: str):
                progress_val[0] = min(progress_val[0] + 0.05, 0.95)
                self.after(0, lambda: self.status_label.configure(
                    text=f"{DECORATIONS['block_med']} {status}"
                ))
                self.after(0, lambda: self.progress.set(progress_val[0]))

            success = self.ollama.create_model(name, modelfile_path, on_progress)

            def on_complete():
                self.progress.pack_forget()
                self.create_btn.configure(state="normal")

                if success:
                    self._mark_step_completed(4)
                    self.status_label.configure(
                        text=f"{DECORATIONS['check']} Modelo '{name}' creado!",
                        text_color=COLORS["success"]
                    )
                    self._refresh_models_list()
                    if self.on_model_created:
                        self.on_model_created(name)
                else:
                    self.status_label.configure(
                        text=f"{DECORATIONS['cross']} Error al crear modelo",
                        text_color=COLORS["error"]
                    )

            self.after(0, on_complete)

        threading.Thread(target=do_create, daemon=True).start()

    def _reset_form(self):
        """Reset the form"""
        self.drop_zone.reset()
        self.selected_gguf_path = None
        self.name_entry.delete(0, "end")
        self.system_prompt.delete("1.0", "end")
        self.prompt_preset.set("-- Seleccionar --")
        self.temp_slider.set(0.7)
        self.top_p_slider.set(0.9)
        self.repeat_slider.set(1.1)
        self.ctx_combo.set("4096")
        self.status_label.configure(text="")
        # Reset step indicators and disable create button
        for i in range(1, 5):
            self._reset_step_indicator(i)
        self.create_btn.configure(state="disabled")

    def _refresh_models_list(self):
        """Refresh installed models list"""
        for widget in self.models_list_frame.winfo_children():
            widget.destroy()

        def fetch():
            models = self.ollama.list_models()

            def update():
                if not models:
                    MatrixLabel(
                        self.models_list_frame,
                        text=f"{DECORATIONS['circle']} No hay modelos instalados",
                        size="sm",
                        text_color=COLORS["text_muted"]
                    ).pack(anchor="w", pady=10)
                else:
                    for model in models:
                        card = ModelCard(
                            self.models_list_frame,
                            model.name,
                            model.size_human,
                            self._delete_model
                        )
                        card.pack(fill="x", pady=5)

            self.after(0, update)

        threading.Thread(target=fetch, daemon=True).start()

    def _delete_model(self, name: str):
        """Delete a model"""
        if messagebox.askyesno("Confirmar", f"Eliminar modelo '{name}'?"):
            def do_delete():
                self.ollama.delete_model(name)
                self.after(0, self._refresh_models_list)

            threading.Thread(target=do_delete, daemon=True).start()
