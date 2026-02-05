"""System Specifications Panel"""
import customtkinter as ctk
import subprocess
import threading
import os
import platform
from pathlib import Path
from typing import Dict, Optional

from .theme import COLORS, DECORATIONS
from .widgets import (
    MatrixFrame, MatrixScrollableFrame, MatrixLabel,
    TerminalHeader, MatrixProgressBar
)


class SystemInfo:
    """Gather system information"""

    @staticmethod
    def get_cpu_info() -> Dict:
        """Get CPU information"""
        info = {
            "name": "Unknown",
            "cores": os.cpu_count() or 0,
            "threads": os.cpu_count() or 0,
        }

        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        info["name"] = line.split(":")[1].strip()
                        break
        except Exception:
            info["name"] = platform.processor() or "Unknown CPU"

        return info

    @staticmethod
    def get_memory_info() -> Dict:
        """Get RAM information"""
        info = {"total_gb": 0, "available_gb": 0, "used_percent": 0}

        try:
            with open("/proc/meminfo", "r") as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        meminfo[parts[0].rstrip(":")] = int(parts[1])

                total_kb = meminfo.get("MemTotal", 0)
                available_kb = meminfo.get("MemAvailable", 0)

                info["total_gb"] = total_kb / (1024 * 1024)
                info["available_gb"] = available_kb / (1024 * 1024)
                info["used_percent"] = ((total_kb - available_kb) / total_kb * 100) if total_kb > 0 else 0
        except Exception:
            pass

        return info

    @staticmethod
    def get_gpu_info() -> Dict:
        """Get GPU information via nvidia-smi"""
        info = {
            "available": False,
            "name": "No GPU detected",
            "vram_total_gb": 0,
            "vram_used_gb": 0,
            "vram_free_gb": 0,
            "temperature": 0,
            "utilization": 0,
            "driver_version": "",
            "cuda_version": ""
        }

        try:
            # Get GPU name and memory
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,driver_version",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                if len(parts) >= 7:
                    info["available"] = True
                    info["name"] = parts[0].strip()
                    info["vram_total_gb"] = float(parts[1].strip()) / 1024
                    info["vram_used_gb"] = float(parts[2].strip()) / 1024
                    info["vram_free_gb"] = float(parts[3].strip()) / 1024
                    info["temperature"] = int(parts[4].strip())
                    info["utilization"] = int(parts[5].strip().replace("%", ""))
                    info["driver_version"] = parts[6].strip()

            # Get CUDA version
            result2 = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result2.returncode == 0:
                # Try to get CUDA version from nvidia-smi output
                result3 = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
                if "CUDA Version:" in result3.stdout:
                    for line in result3.stdout.split("\n"):
                        if "CUDA Version:" in line:
                            cuda_part = line.split("CUDA Version:")[1].split()[0]
                            info["cuda_version"] = cuda_part.strip()
                            break

        except Exception:
            pass

        return info

    @staticmethod
    def get_disk_info() -> Dict:
        """Get disk information for ai-models directory"""
        info = {"total_gb": 0, "free_gb": 0, "used_percent": 0}

        try:
            models_path = Path.home() / "ai-models"
            if not models_path.exists():
                models_path = Path.home()

            stat = os.statvfs(str(models_path))
            info["total_gb"] = (stat.f_blocks * stat.f_frsize) / (1024**3)
            info["free_gb"] = (stat.f_bavail * stat.f_frsize) / (1024**3)
            info["used_percent"] = ((info["total_gb"] - info["free_gb"]) / info["total_gb"] * 100) if info["total_gb"] > 0 else 0
        except Exception:
            pass

        return info

    @staticmethod
    def get_ollama_info() -> Dict:
        """Get Ollama status"""
        info = {
            "installed": False,
            "version": "",
            "running": False,
            "models_count": 0
        }

        try:
            # Check version
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                info["installed"] = True
                info["version"] = result.stdout.strip().split()[-1] if result.stdout else ""

            # Check if running
            result2 = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                text=True,
                timeout=5
            )
            info["running"] = result2.returncode == 0

            # Count models
            result3 = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result3.returncode == 0:
                lines = result3.stdout.strip().split("\n")
                info["models_count"] = max(0, len(lines) - 1)  # Exclude header

        except Exception:
            pass

        return info


def estimate_model_performance(model_size_gb: float, gpu_info: Dict, ram_info: Dict) -> Dict:
    """Estimate how well a model will run"""
    result = {
        "can_run": False,
        "recommended": False,
        "speed_rating": "Unknown",
        "will_use_gpu": False,
        "warnings": [],
        "tips": []
    }

    vram_free = gpu_info.get("vram_free_gb", 0)
    vram_total = gpu_info.get("vram_total_gb", 0)
    ram_available = ram_info.get("available_gb", 0)
    has_gpu = gpu_info.get("available", False)

    # Check if can run at all
    total_memory = vram_free + ram_available
    if total_memory < model_size_gb * 1.1:  # Need 10% overhead
        result["can_run"] = False
        result["speed_rating"] = "NO PUEDE EJECUTAR"
        result["warnings"].append(f"Memoria insuficiente. Necesitas {model_size_gb:.1f}GB, tienes {total_memory:.1f}GB disponibles")
        return result

    result["can_run"] = True

    # Check GPU fit
    if has_gpu and vram_free >= model_size_gb * 1.05:
        result["will_use_gpu"] = True
        result["recommended"] = True

        if vram_free >= model_size_gb * 1.5:
            result["speed_rating"] = "EXCELENTE"
            result["tips"].append("El modelo cabe completamente en GPU - maxima velocidad!")
        elif vram_free >= model_size_gb * 1.2:
            result["speed_rating"] = "MUY BUENO"
            result["tips"].append("Buen margen de VRAM disponible")
        else:
            result["speed_rating"] = "BUENO"
            result["tips"].append("Ajustado pero funcionara bien en GPU")

    elif has_gpu and vram_free >= model_size_gb * 0.5:
        result["will_use_gpu"] = True
        result["speed_rating"] = "ACEPTABLE"
        result["warnings"].append("Parte del modelo usara RAM (mas lento)")
        result["tips"].append("Considera un modelo mas pequeno para mejor rendimiento")

    elif ram_available >= model_size_gb * 1.2:
        result["will_use_gpu"] = False
        result["speed_rating"] = "LENTO"
        result["warnings"].append("Ejecutara en CPU - respuestas lentas (30-60 seg)")
        result["tips"].append("Instala drivers NVIDIA para usar GPU")

    else:
        result["speed_rating"] = "MUY LENTO"
        result["warnings"].append("Memoria muy justa - puede ir muy lento o fallar")
        result["tips"].append("Usa un modelo mas pequeno (Q3_K_S)")

    return result


class SpecCard(ctk.CTkFrame):
    """Card showing a system specification"""

    def __init__(self, parent, title: str, icon: str, **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border_green"],
            border_width=1,
            corner_radius=6,
            **kwargs
        )

        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_tertiary"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            header,
            text=f" {icon} {title}",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLORS["matrix_green_bright"]
        ).pack(anchor="w", padx=15, pady=10)

        # Content area
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="ew", padx=15, pady=15)
        self.content.grid_columnconfigure(1, weight=1)

    def add_row(self, label: str, value: str, row: int, highlight: bool = False):
        """Add a data row"""
        color = COLORS["matrix_green_bright"] if highlight else COLORS["matrix_green"]

        ctk.CTkLabel(
            self.content,
            text=label,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=COLORS["text_muted"]
        ).grid(row=row, column=0, sticky="w", pady=3)

        ctk.CTkLabel(
            self.content,
            text=value,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=color
        ).grid(row=row, column=1, sticky="e", pady=3)

    def add_progress(self, label: str, value: float, row: int):
        """Add a progress bar row"""
        ctk.CTkLabel(
            self.content,
            text=label,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=COLORS["text_muted"]
        ).grid(row=row, column=0, sticky="w", pady=3)

        bar = MatrixProgressBar(self.content, width=150, height=12)
        bar.set(value / 100)
        bar.grid(row=row, column=1, sticky="e", pady=3)


class SystemPanel(ctk.CTkFrame):
    """System specifications panel"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_primary"])
        kwargs.setdefault("corner_radius", 0)
        super().__init__(parent, **kwargs)

        self.system_info = {}
        self._setup_ui()
        self.after(100, self._load_info)

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = TerminalHeader(self, "ESPECIFICACIONES", "system.info")
        header.grid(row=0, column=0, sticky="ew")

        # Scrollable content
        self.content = MatrixScrollableFrame(self, fg_color=COLORS["bg_primary"], border_width=0)
        self.content.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.content.grid_columnconfigure(0, weight=1)

        # Loading indicator
        self.loading_label = MatrixLabel(
            self.content,
            text=f"{DECORATIONS['block_med']} Analizando sistema...",
            size="lg"
        )
        self.loading_label.pack(pady=50)

    def _load_info(self):
        """Load system info in background"""
        def load():
            self.system_info = {
                "cpu": SystemInfo.get_cpu_info(),
                "memory": SystemInfo.get_memory_info(),
                "gpu": SystemInfo.get_gpu_info(),
                "disk": SystemInfo.get_disk_info(),
                "ollama": SystemInfo.get_ollama_info()
            }
            self.after(0, self._display_info)

        threading.Thread(target=load, daemon=True).start()

    def _display_info(self):
        """Display gathered info"""
        self.loading_label.destroy()

        cpu = self.system_info["cpu"]
        mem = self.system_info["memory"]
        gpu = self.system_info["gpu"]
        disk = self.system_info["disk"]
        ollama = self.system_info["ollama"]

        # ═══════════════════════════════════════════════════════════
        # RESUMEN DE CAPACIDAD
        # ═══════════════════════════════════════════════════════════
        summary = self._create_summary_card()
        summary.pack(fill="x", pady=(0, 15))

        # ═══════════════════════════════════════════════════════════
        # GPU
        # ═══════════════════════════════════════════════════════════
        gpu_card = SpecCard(self.content, "GPU (NVIDIA)", DECORATIONS["block"])
        gpu_card.pack(fill="x", pady=(0, 10))

        if gpu["available"]:
            gpu_card.add_row("Modelo:", gpu["name"], 0, highlight=True)
            gpu_card.add_row("VRAM Total:", f"{gpu['vram_total_gb']:.1f} GB", 1)
            gpu_card.add_row("VRAM Libre:", f"{gpu['vram_free_gb']:.1f} GB", 2, highlight=True)
            gpu_card.add_row("VRAM Usado:", f"{gpu['vram_used_gb']:.1f} GB", 3)
            gpu_card.add_row("Temperatura:", f"{gpu['temperature']}°C", 4)
            gpu_card.add_row("Uso GPU:", f"{gpu['utilization']}%", 5)
            gpu_card.add_row("Driver:", gpu["driver_version"], 6)
            if gpu["cuda_version"]:
                gpu_card.add_row("CUDA:", gpu["cuda_version"], 7)
        else:
            gpu_card.add_row("Estado:", "No detectada", 0)
            gpu_card.add_row("Nota:", "Instala drivers NVIDIA", 1)

        # ═══════════════════════════════════════════════════════════
        # RAM
        # ═══════════════════════════════════════════════════════════
        ram_card = SpecCard(self.content, "MEMORIA RAM", DECORATIONS["block"])
        ram_card.pack(fill="x", pady=(0, 10))

        ram_card.add_row("Total:", f"{mem['total_gb']:.1f} GB", 0)
        ram_card.add_row("Disponible:", f"{mem['available_gb']:.1f} GB", 1, highlight=True)
        ram_card.add_progress("Uso:", mem['used_percent'], 2)

        # ═══════════════════════════════════════════════════════════
        # CPU
        # ═══════════════════════════════════════════════════════════
        cpu_card = SpecCard(self.content, "PROCESADOR (CPU)", DECORATIONS["block"])
        cpu_card.pack(fill="x", pady=(0, 10))

        cpu_card.add_row("Modelo:", cpu["name"][:50], 0)
        cpu_card.add_row("Nucleos:", str(cpu["cores"]), 1)

        # ═══════════════════════════════════════════════════════════
        # DISCO
        # ═══════════════════════════════════════════════════════════
        disk_card = SpecCard(self.content, "ALMACENAMIENTO", DECORATIONS["block"])
        disk_card.pack(fill="x", pady=(0, 10))

        disk_card.add_row("Espacio Total:", f"{disk['total_gb']:.0f} GB", 0)
        disk_card.add_row("Espacio Libre:", f"{disk['free_gb']:.0f} GB", 1, highlight=True)
        disk_card.add_progress("Uso:", disk['used_percent'], 2)

        # ═══════════════════════════════════════════════════════════
        # OLLAMA
        # ═══════════════════════════════════════════════════════════
        ollama_card = SpecCard(self.content, "OLLAMA", DECORATIONS["block"])
        ollama_card.pack(fill="x", pady=(0, 10))

        ollama_card.add_row("Instalado:", "Si" if ollama["installed"] else "No", 0)
        if ollama["installed"]:
            ollama_card.add_row("Version:", ollama["version"], 1)
            ollama_card.add_row("Servidor:", "Activo" if ollama["running"] else "Inactivo", 2,
                               highlight=ollama["running"])
            ollama_card.add_row("Modelos:", str(ollama["models_count"]), 3)

        # Refresh button
        refresh_btn = ctk.CTkButton(
            self.content,
            text=f"{DECORATIONS['block_med']} ACTUALIZAR INFO",
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["matrix_green_dim"],
            border_width=1,
            text_color=COLORS["matrix_green"],
            command=self._refresh
        )
        refresh_btn.pack(pady=15)

    def _create_summary_card(self) -> ctk.CTkFrame:
        """Create summary card with recommendations"""
        gpu = self.system_info["gpu"]
        mem = self.system_info["memory"]

        card = ctk.CTkFrame(
            self.content,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["matrix_green"],
            border_width=2,
            corner_radius=6
        )

        header = ctk.CTkFrame(card, fg_color=COLORS["bg_tertiary"], corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text=f" {DECORATIONS['star']} RESUMEN - QUE MODELOS PUEDO USAR?",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLORS["matrix_green_bright"]
        ).pack(anchor="w", padx=15, pady=10)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=15)

        vram = gpu.get("vram_free_gb", 0)
        ram = mem.get("available_gb", 0)
        has_gpu = gpu.get("available", False)

        if has_gpu:
            summary_text = f"""
{DECORATIONS['check']} GPU Detectada: {gpu['name']}
{DECORATIONS['check']} VRAM Disponible: {vram:.1f} GB
{DECORATIONS['check']} RAM Disponible: {ram:.1f} GB

{DECORATIONS['arrow_r']} MODELOS RECOMENDADOS PARA TU SISTEMA:
"""
            if vram >= 10:
                summary_text += f"""
   {DECORATIONS['star']} Modelos 13B Q5/Q6 - EXCELENTE rendimiento
   {DECORATIONS['star']} Modelos 7B Q8 - PERFECTO
   {DECORATIONS['star']} Modelos 7B Q4/Q5 - MUY RAPIDO
"""
            elif vram >= 6:
                summary_text += f"""
   {DECORATIONS['star']} Modelos 7B Q4_K_M - RECOMENDADO (4-5GB)
   {DECORATIONS['star']} Modelos 7B Q5_K_S - Bueno si cabe
   {DECORATIONS['circle']} Modelos 13B Q3 - Funcionara pero ajustado
"""
            elif vram >= 4:
                summary_text += f"""
   {DECORATIONS['star']} Modelos 7B Q3_K_M - RECOMENDADO (3-4GB)
   {DECORATIONS['star']} Modelos 7B Q4_K_S - Deberia funcionar
   {DECORATIONS['cross']} Modelos 13B+ - Demasiado grandes
"""
            else:
                summary_text += f"""
   {DECORATIONS['star']} Modelos 7B Q2_K o Q3_K_S - Lo mas ligero
   {DECORATIONS['circle']} Puede necesitar usar RAM tambien
"""
        else:
            summary_text = f"""
{DECORATIONS['cross']} GPU: No detectada
{DECORATIONS['check']} RAM Disponible: {ram:.1f} GB

{DECORATIONS['arrow_r']} SIN GPU - Ejecutara en CPU (mas lento)

   {DECORATIONS['star']} Modelos 7B Q3_K_S - Mejor opcion sin GPU
   {DECORATIONS['circle']} Espera 30-60 segundos por respuesta
   {DECORATIONS['prompt']} TIP: Instala drivers NVIDIA para acelerar
"""

        summary_label = ctk.CTkLabel(
            content,
            text=summary_text,
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=COLORS["matrix_green"],
            justify="left",
            anchor="w",
            wraplength=600
        )
        summary_label.pack(fill="x")

        def _update_summary_wrap(event=None):
            try:
                summary_label.configure(wraplength=max(200, content.winfo_width() - 60))
            except Exception:
                pass

        content.bind("<Configure>", _update_summary_wrap, add="+")

        return card

    def _refresh(self):
        """Refresh system info"""
        # Clear content
        for widget in self.content.winfo_children():
            widget.destroy()

        self.loading_label = MatrixLabel(
            self.content,
            text=f"{DECORATIONS['block_med']} Actualizando...",
            size="lg"
        )
        self.loading_label.pack(pady=50)

        self.after(100, self._load_info)

    def get_performance_estimate(self, model_size_gb: float) -> Dict:
        """Get performance estimate for a model"""
        if not self.system_info:
            return {"can_run": False, "speed_rating": "Unknown", "warnings": ["Info no cargada"]}

        return estimate_model_performance(
            model_size_gb,
            self.system_info.get("gpu", {}),
            self.system_info.get("memory", {})
        )
