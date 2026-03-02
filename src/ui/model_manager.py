"""Matrix-styled Model Management Panel with Drag & Drop"""
import customtkinter as ctk
import re
from tkinter import filedialog, messagebox
from typing import Callable, Optional
from pathlib import Path
import threading
import os

from ..utils.logger import get_logger
log = get_logger("model_manager")


def _validate_model_name(name: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_:.\-]*$', name)) and len(name) <= 100

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
from ..core.model_config import SYSTEM_PROMPTS, PARAMETER_PRESETS
from ..core.gguf_manager import detect_split_gguf
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

        # Warning label (for split files etc.)
        self.warning_label = ctk.CTkLabel(
            content,
            text="",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["warning"],
            wraplength=350
        )
        self.warning_label.pack(pady=(5, 0))

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
        try:
            size_gb = Path(file_path).stat().st_size / (1024**3)
        except (OSError, FileNotFoundError) as exc:
            log.error("Cannot read file %s: %s", file_path, exc)
            messagebox.showerror("Error", f"Cannot read file: {exc}")
            return

        # Check for split GGUF
        split_info = detect_split_gguf(file_path)
        warning_text = ""
        if split_info:
            if not split_info["all_complete"]:
                missing = split_info["missing_parts"]
                warning_text = (
                    f"ARCHIVO DIVIDIDO: parte {split_info['part']} de {split_info['total']}. "
                    f"Faltan partes: {', '.join(str(p) for p in missing)}. "
                    f"Todas las partes deben estar en la misma carpeta."
                )
                self.warning_label.configure(
                    text=warning_text,
                    text_color=COLORS["error"]
                )
            else:
                warning_text = (
                    f"Archivo dividido: parte {split_info['part']} de {split_info['total']}. "
                    f"Todas las partes encontradas."
                )
                self.warning_label.configure(
                    text=warning_text,
                    text_color=COLORS["success"]
                )
        else:
            self.warning_label.configure(text="")

        # Extract quantization info
        quant = ""
        m = re.search(r'[_-](Q\d+[_-]?K?[_-]?[A-Z]?)', filename, re.IGNORECASE)
        if m:
            quant = m.group(1).upper().replace('-', '_')

        info_parts = [filename, f"[{size_gb:.2f} GB]"]
        if quant:
            info_parts.append(f"Quant: {quant}")

        self.icon_label.configure(text=DECORATIONS["check"], text_color=COLORS["success"])
        self.main_label.configure(text="ARCHIVO CARGADO")
        self.sub_label.configure(text="clic para cambiar")
        self.file_label.configure(text="\n".join(info_parts))

        if split_info and not split_info["all_complete"]:
            self.configure(border_color=COLORS["warning"])
        else:
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
        self.warning_label.configure(text="")
        self.configure(border_color=COLORS["matrix_green_dim"])
        if hasattr(self, 'perf_label'):
            self.perf_label.destroy()


class ModelCard(ctk.CTkFrame):
    """Matrix-styled model info card with details"""

    def __init__(self, parent, model_name: str, model_size: str, on_delete: Callable,
                 quantization: str = "", family: str = "", params: str = "", **kwargs):
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

        # Detail line: size + quantization + family + params
        detail_parts = [f"Size: {model_size}"]
        if quantization:
            detail_parts.append(f"Quant: {quantization}")
        if family:
            detail_parts.append(f"Family: {family}")
        if params:
            detail_parts.append(f"Params: {params}")

        detail_text = " | ".join(detail_parts)

        size_label = ctk.CTkLabel(
            self,
            text=detail_text,
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
        self.grid_rowconfigure(2, weight=1)

        # Header
        header = TerminalHeader(self, "MODEL FORGE", "crear y gestionar modelos")
        header.grid(row=0, column=0, sticky="ew")

        # Step navigation bar
        self._step_widgets = {}
        nav_bar = ctk.CTkFrame(self, fg_color=COLORS["bg_tertiary"], height=36)
        nav_bar.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        nav_bar.grid_propagate(False)
        nav_inner = ctk.CTkFrame(nav_bar, fg_color="transparent")
        nav_inner.pack(side="left", padx=10, pady=4)

        ctk.CTkLabel(
            nav_inner, text=f"{DECORATIONS['arrow_r']} IR A:",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"]
        ).pack(side="left", padx=(0, 8))

        for step_n, step_label in [(1, "ARCHIVO"), (2, "CONFIG"), (3, "PARAMS"), (4, "CREAR")]:
            btn = ctk.CTkButton(
                nav_inner,
                text=f"{step_n}. {step_label}",
                font=ctk.CTkFont(family="Consolas", size=10),
                width=80, height=24,
                fg_color=COLORS["bg_secondary"],
                hover_color=COLORS["bg_hover"],
                border_color=COLORS["border_dim"],
                border_width=1,
                text_color=COLORS["matrix_green_dim"],
                command=lambda n=step_n: self._scroll_to_step(n)
            )
            btn.pack(side="left", padx=2)

        # Main scrollable content
        self.content = MatrixScrollableFrame(self, fg_color=COLORS["bg_primary"], border_width=0)
        self.content.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.content.grid_columnconfigure(0, weight=1)

        # ===============================================================
        # STEP 1: CARGAR ARCHIVO GGUF
        # ===============================================================
        step1 = self._create_section(
            self.content, "PASO 1: CARGAR ARCHIVO GGUF",
            description="Selecciona o arrastra un archivo .gguf desde tu disco (o USB). "
                        "Los archivos GGUF son modelos de IA comprimidos (cuantizados) que "
                        "puedes descargar de HuggingFace. Cuanto menor sea la cuantizacion "
                        "(Q3, Q4...) mas ligero pero menos preciso. Q4_K_M es el mejor "
                        "balance para la mayoria de GPUs.",
            step_num=1
        )
        step1.pack(fill="x", pady=(0, 20))
        self._step_widgets[1] = step1

        # Drop zone
        self.drop_zone = DropZone(step1, on_file_dropped=self._on_file_selected, height=150)
        self.drop_zone.pack(fill="x", padx=15, pady=15)

        # ===============================================================
        # STEP 2: CONFIGURAR MODELO (MODELFILE)
        # ===============================================================
        step2 = self._create_section(
            self.content, "PASO 2: CONFIGURAR MODELO (Modelfile)",
            description="Dale un nombre corto a tu modelo (ej: 'dolphin-7b') y configura "
                        "su personalidad con el System Prompt. El Modelfile es la receta que "
                        "Ollama usa para saber como ejecutar tu modelo.",
            step_num=2
        )
        step2.pack(fill="x", pady=(0, 20))
        self._step_widgets[2] = step2

        config_frame = ctk.CTkFrame(step2, fg_color="transparent")
        config_frame.pack(fill="x", padx=15, pady=10)
        config_frame.grid_columnconfigure(1, weight=1)

        # Model Name
        MatrixLabel(config_frame, text="Nombre del modelo:", size="sm").grid(
            row=0, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        self.name_entry = MatrixEntry(config_frame, placeholder_text="mi-modelo-custom", width=300)
        self.name_entry.grid(row=0, column=1, padx=10, pady=(10, 0), sticky="w")
        self.name_entry.bind("<KeyRelease>", self._validate_name_live)

        # Inline validation label
        self.name_validation_label = ctk.CTkLabel(
            config_frame,
            text="Solo letras minusculas, numeros y guiones. Ej: dolphin-7b, llama3-code",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"],
        )
        self.name_validation_label.grid(row=1, column=1, padx=10, pady=(2, 8), sticky="w")

        # System Prompt Template
        MatrixLabel(config_frame, text="Plantilla de prompt:", size="sm").grid(
            row=2, column=0, padx=10, pady=10, sticky="w"
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

        # ===============================================================
        # STEP 3: PARAMETROS DE INFERENCIA
        # ===============================================================
        step3 = self._create_section(
            self.content, "PASO 3: PARAMETROS DE INFERENCIA",
            description="Ajusta los parametros de generacion. "
                        "Los valores por defecto funcionan bien para la mayoria de casos.",
            step_num=3
        )
        step3.pack(fill="x", pady=(0, 20))
        self._step_widgets[3] = step3

        params_frame = ctk.CTkFrame(step3, fg_color="transparent")
        params_frame.pack(fill="x", padx=15, pady=10)
        params_frame.grid_columnconfigure((1, 3), weight=1)

        # Parameter presets row
        MatrixLabel(params_frame, text="Preset:", size="sm").grid(
            row=0, column=0, padx=10, pady=8, sticky="w"
        )
        preset_row = ctk.CTkFrame(params_frame, fg_color="transparent")
        preset_row.grid(row=0, column=1, columnspan=3, padx=10, pady=8, sticky="w")

        for preset_name in PARAMETER_PRESETS:
            btn = MatrixButton(
                preset_row,
                text=preset_name.upper(),
                height=28,
                width=90,
                command=lambda n=preset_name: self._apply_param_preset(n)
            )
            btn.pack(side="left", padx=(0, 6))

        # Temperature
        MatrixLabel(params_frame, text="Temperature:", size="sm").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.temp_slider = MatrixSlider(params_frame, from_=0, to=2, number_of_steps=40)
        self.temp_slider.set(0.7)
        self.temp_slider.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
        self.temp_label = MatrixLabel(params_frame, text="0.70", size="sm")
        self.temp_label.grid(row=1, column=2, padx=10, pady=8)
        self.temp_slider.configure(command=lambda v: self.temp_label.configure(text=f"{v:.2f}"))
        ctk.CTkLabel(params_frame, text="Bajo = preciso, Alto = creativo",
                     font=ctk.CTkFont(family="Consolas", size=10), text_color=COLORS["text_muted"]
                     ).grid(row=1, column=3, padx=10, pady=8, sticky="w")

        # Top P
        MatrixLabel(params_frame, text="Top P:", size="sm").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.top_p_slider = MatrixSlider(params_frame, from_=0, to=1, number_of_steps=20)
        self.top_p_slider.set(0.9)
        self.top_p_slider.grid(row=2, column=1, padx=10, pady=8, sticky="ew")
        self.top_p_label = MatrixLabel(params_frame, text="0.90", size="sm")
        self.top_p_label.grid(row=2, column=2, padx=10, pady=8)
        self.top_p_slider.configure(command=lambda v: self.top_p_label.configure(text=f"{v:.2f}"))
        ctk.CTkLabel(params_frame, text="Diversidad de tokens. 0.9 = buen balance",
                     font=ctk.CTkFont(family="Consolas", size=10), text_color=COLORS["text_muted"]
                     ).grid(row=2, column=3, padx=10, pady=8, sticky="w")

        # Repeat Penalty
        MatrixLabel(params_frame, text="Repeat Penalty:", size="sm").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.repeat_slider = MatrixSlider(params_frame, from_=1, to=2, number_of_steps=20)
        self.repeat_slider.set(1.1)
        self.repeat_slider.grid(row=3, column=1, padx=10, pady=8, sticky="ew")
        self.repeat_label = MatrixLabel(params_frame, text="1.10", size="sm")
        self.repeat_label.grid(row=3, column=2, padx=10, pady=8)
        self.repeat_slider.configure(command=lambda v: self.repeat_label.configure(text=f"{v:.2f}"))
        ctk.CTkLabel(params_frame, text="Penaliza repeticiones. 1.1 = normal",
                     font=ctk.CTkFont(family="Consolas", size=10), text_color=COLORS["text_muted"]
                     ).grid(row=3, column=3, padx=10, pady=8, sticky="w")

        # Context Length
        MatrixLabel(params_frame, text="Context Length:", size="sm").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        self.ctx_combo = MatrixComboBox(
            params_frame,
            values=["2048", "4096", "8192", "16384", "32768"],
            width=120
        )
        self.ctx_combo.set("4096")
        self.ctx_combo.grid(row=4, column=1, padx=10, pady=8, sticky="w")
        ctk.CTkLabel(params_frame, text="Mas contexto = mas memoria. 4096 suficiente",
                     font=ctk.CTkFont(family="Consolas", size=10), text_color=COLORS["text_muted"]
                     ).grid(row=4, column=3, padx=10, pady=8, sticky="w")

        # ===============================================================
        # STEP 4: CREAR MODELO
        # ===============================================================
        step4 = self._create_section(
            self.content, "PASO 4: CREAR MODELO EN OLLAMA",
            description="Revisa la configuracion y crea tu modelo. "
                        "El proceso puede tardar unos segundos dependiendo del archivo.",
            step_num=4
        )
        step4.pack(fill="x", pady=(0, 20))
        self._step_widgets[4] = step4

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

        # ===============================================================
        # IMPORT MODEL FROM REGISTRY
        # ===============================================================
        import_section = self._create_section(
            self.content, "IMPORTAR MODELO DE OLLAMA REGISTRY",
            description="Descarga un modelo directamente del registro de Ollama "
                        "por nombre (ej: llama3.2, mistral, qwen2.5). "
                        "Requiere conexion a internet."
        )
        import_section.pack(fill="x", pady=(0, 20))

        import_frame = ctk.CTkFrame(import_section, fg_color="transparent")
        import_frame.pack(fill="x", padx=15, pady=15)
        import_frame.grid_columnconfigure(1, weight=1)

        MatrixLabel(import_frame, text="Nombre del modelo:", size="sm").grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        self.pull_name_entry = MatrixEntry(
            import_frame,
            placeholder_text="llama3.2, mistral, qwen2.5...",
            width=300
        )
        self.pull_name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        self.pull_btn = MatrixButton(
            import_frame,
            text=f"{DECORATIONS['arrow_r']} DESCARGAR",
            height=35,
            width=140,
            primary=True,
            command=self._pull_model
        )
        self.pull_btn.grid(row=0, column=2, padx=10, pady=10)

        self.pull_status_label = MatrixLabel(import_frame, text="", size="sm")
        self.pull_status_label.grid(row=1, column=0, columnspan=3, padx=10, sticky="w")

        self.pull_progress = MatrixProgressBar(import_frame)
        self.pull_progress.set(0)

        # ===============================================================
        # MODELOS INSTALADOS
        # ===============================================================
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

    def _scroll_to_step(self, step_num: int):
        """Scroll the content area to bring the given step into view."""
        widget = self._step_widgets.get(step_num)
        if not widget:
            return

        def do_scroll():
            try:
                canvas = self.content._parent_canvas
                canvas.update_idletasks()
                # Get the widget's y position relative to the canvas content
                widget_y = widget.winfo_y()
                bbox = canvas.bbox("all")
                if not bbox:
                    return
                total_h = bbox[3]
                if total_h <= 0:
                    return
                # Scroll so the step is near the top with a small offset
                frac = max(0.0, (widget_y - 10) / total_h)
                canvas.yview_moveto(min(1.0, frac))
            except Exception:
                pass
        self.after(50, do_scroll)

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

    def _validate_name_live(self, event=None):
        """Validate model name as user types and show inline feedback"""
        name = self.name_entry.get().strip()
        if not name:
            self.name_validation_label.configure(
                text="Solo letras minusculas, numeros y guiones. Ej: dolphin-7b, llama3-code",
                text_color=COLORS["text_muted"]
            )
            return

        # Check for uppercase
        if name != name.lower():
            self.name_validation_label.configure(
                text=f"{DECORATIONS['cross']} Solo minusculas. Se convertira a: {name.lower()}",
                text_color=COLORS["warning"]
            )
            return

        # Check for invalid characters
        sanitized = re.sub(r'[^a-z0-9-]', '-', name.lower())
        sanitized = re.sub(r'-{2,}', '-', sanitized).strip('-')
        if sanitized != name:
            self.name_validation_label.configure(
                text=f"{DECORATIONS['cross']} Caracteres invalidos. Se usara: {sanitized}",
                text_color=COLORS["warning"]
            )
            return

        if len(name) > 100:
            self.name_validation_label.configure(
                text=f"{DECORATIONS['cross']} Nombre demasiado largo (max 100 caracteres)",
                text_color=COLORS["error"]
            )
            return

        # Valid
        self.name_validation_label.configure(
            text=f"{DECORATIONS['check']} Nombre valido",
            text_color=COLORS["success"]
        )

    def _on_file_selected(self, file_path: str):
        """Handle file selection"""
        self.selected_gguf_path = file_path

        # Check for split GGUF and warn
        split_info = detect_split_gguf(file_path)
        if split_info and not split_info["all_complete"]:
            missing = split_info["missing_parts"]
            messagebox.showwarning(
                "Archivo GGUF dividido",
                f"Este archivo es la parte {split_info['part']} de {split_info['total']}.\n\n"
                f"Faltan las partes: {', '.join(str(p) for p in missing)}.\n\n"
                f"Descarga todas las partes y colocadas en la misma carpeta "
                f"para que el modelo funcione correctamente."
            )

        # Mark step 1 as completed and enable create button
        self._mark_step_completed(1)
        self.create_btn.configure(state="normal")

        # Always update name when a file is loaded
        suggested = self._sanitize_model_name(file_path)
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, suggested)
        self._validate_name_live()

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

    def _apply_param_preset(self, preset_name: str):
        """Apply a parameter preset to all sliders"""
        preset = PARAMETER_PRESETS.get(preset_name)
        if not preset:
            return

        self.temp_slider.set(preset.temperature)
        self.temp_label.configure(text=f"{preset.temperature:.2f}")
        self.top_p_slider.set(preset.top_p)
        self.top_p_label.configure(text=f"{preset.top_p:.2f}")
        self.repeat_slider.set(preset.repeat_penalty)
        self.repeat_label.configure(text=f"{preset.repeat_penalty:.2f}")
        self.ctx_combo.set(str(preset.num_ctx))

        self.status_label.configure(
            text=f"{DECORATIONS['check']} Preset '{preset_name}' aplicado",
            text_color=COLORS["matrix_green"]
        )
        self.after(2000, lambda: self.status_label.configure(text=""))

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
        name = re.sub(r'[^a-z0-9-]', '-', name.lower())
        name = re.sub(r'-{2,}', '-', name).strip('-')
        if not name or not _validate_model_name(name):
            messagebox.showerror("Error", "Nombre de modelo invalido. Solo letras, numeros, guiones, puntos, dos puntos y guion bajo.")
            return
        # Update the entry to show the sanitized name
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, name)

        # Warn about split files
        split_info = detect_split_gguf(self.selected_gguf_path)
        if split_info and not split_info["all_complete"]:
            if not messagebox.askyesno(
                "Archivo incompleto",
                f"Faltan partes del archivo GGUF ({len(split_info['missing_parts'])} de {split_info['total']}).\n\n"
                "El modelo probablemente no funcionara. Continuar de todos modos?"
            ):
                return

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
        self.status_label.configure(
            text=f"{DECORATIONS['block_med']} Creando modelo...",
            text_color=COLORS["matrix_green"]
        )

        def do_create():
            progress_val = [0]
            step_count = [0]

            def on_progress(status: str):
                step_count[0] += 1
                # Parse percentage from status if available
                pct_match = re.search(r'(\d+)%', status)
                if pct_match:
                    progress_val[0] = int(pct_match.group(1)) / 100.0
                else:
                    progress_val[0] = min(progress_val[0] + 0.05, 0.95)

                display = f"{DECORATIONS['block_med']} {status}"
                if progress_val[0] > 0:
                    display += f"  [{progress_val[0]*100:.0f}%]"

                self.after(0, lambda: self.status_label.configure(text=display))
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
                        text=f"{DECORATIONS['cross']} Error al crear modelo. Revisa que Ollama este corriendo.",
                        text_color=COLORS["error"]
                    )

            self.after(0, on_complete)

        threading.Thread(target=do_create, daemon=True).start()

    def _pull_model(self):
        """Pull a model from Ollama registry"""
        name = self.pull_name_entry.get().strip()
        if not name:
            messagebox.showwarning("Aviso", "Ingresa el nombre del modelo a descargar")
            return

        self.pull_btn.configure(state="disabled")
        self.pull_progress.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="ew")
        self.pull_progress.set(0)
        self.pull_status_label.configure(
            text=f"{DECORATIONS['block_med']} Descargando {name}...",
            text_color=COLORS["warning"]
        )

        def do_pull():
            def on_progress(status: str, pct: float):
                display = f"{DECORATIONS['block_med']} {status}"
                if pct > 0:
                    display += f"  [{pct:.0f}%]"
                self.after(0, lambda: self.pull_status_label.configure(text=display))
                self.after(0, lambda: self.pull_progress.set(pct / 100.0))

            success = self.ollama.pull_model(name, on_progress)

            def on_complete():
                self.pull_btn.configure(state="normal")
                try:
                    self.pull_progress.grid_forget()
                except Exception:
                    pass

                if success:
                    self.pull_status_label.configure(
                        text=f"{DECORATIONS['check']} Modelo '{name}' descargado!",
                        text_color=COLORS["success"]
                    )
                    self._refresh_models_list()
                    if self.on_model_created:
                        self.on_model_created(name)
                else:
                    self.pull_status_label.configure(
                        text=f"{DECORATIONS['cross']} Error al descargar '{name}'. Verifica el nombre y tu conexion.",
                        text_color=COLORS["error"]
                    )

            self.after(0, on_complete)

        threading.Thread(target=do_pull, daemon=True).start()

    def _reset_form(self):
        """Reset the form"""
        self.drop_zone.reset()
        self.selected_gguf_path = None
        self.name_entry.delete(0, "end")
        self.name_validation_label.configure(
            text="Solo letras minusculas, numeros y guiones. Ej: dolphin-7b, llama3-code",
            text_color=COLORS["text_muted"]
        )
        self.system_prompt.delete("1.0", "end")
        self.prompt_preset.set("-- Seleccionar --")
        self.temp_slider.set(0.7)
        self.temp_label.configure(text="0.70")
        self.top_p_slider.set(0.9)
        self.top_p_label.configure(text="0.90")
        self.repeat_slider.set(1.1)
        self.repeat_label.configure(text="1.10")
        self.ctx_combo.set("4096")
        self.status_label.configure(text="")
        # Reset step indicators and disable create button
        for i in range(1, 5):
            self._reset_step_indicator(i)
        self.create_btn.configure(state="disabled")

    def _refresh_models_list(self):
        """Refresh installed models list with detailed info"""
        for widget in self.models_list_frame.winfo_children():
            widget.destroy()

        def fetch():
            models = self.ollama.list_models()

            # Try to get detailed info for each model via `ollama show`
            model_details = {}
            for model in models:
                detail = self._get_model_details(model.name)
                if detail:
                    model_details[model.name] = detail

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
                        details = model_details.get(model.name, {})
                        card = ModelCard(
                            self.models_list_frame,
                            model.name,
                            model.size_human,
                            self._delete_model,
                            quantization=details.get("quantization", ""),
                            family=details.get("family", ""),
                            params=details.get("parameters", ""),
                        )
                        card.pack(fill="x", pady=5)

            self.after(0, update)

        threading.Thread(target=fetch, daemon=True).start()

    @staticmethod
    def _get_model_details(model_name: str) -> dict:
        """Get detailed model info via ollama show (runs in background thread)"""
        import subprocess
        details = {}
        try:
            result = subprocess.run(
                ["ollama", "show", model_name],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("family"):
                        parts = line.split(None, 1)
                        if len(parts) > 1:
                            details["family"] = parts[1].strip()
                    elif line.startswith("parameters"):
                        parts = line.split(None, 1)
                        if len(parts) > 1:
                            details["parameters"] = parts[1].strip()
                    elif line.startswith("quantization"):
                        parts = line.split(None, 1)
                        if len(parts) > 1:
                            details["quantization"] = parts[1].strip()
        except Exception:
            pass
        return details

    def _delete_model(self, name: str):
        """Delete a model"""
        if not _validate_model_name(name):
            messagebox.showerror("Error", "Nombre de modelo invalido.")
            return
        if messagebox.askyesno("Confirmar", f"Eliminar modelo '{name}'?"):
            def do_delete():
                self.ollama.delete_model(name)
                self.after(0, self._refresh_models_list)

            threading.Thread(target=do_delete, daemon=True).start()
