"""Help/FAQ Panel with tutorials"""
import customtkinter as ctk
from .theme import COLORS, DECORATIONS, RADIUS
from .widgets import MatrixFrame, MatrixScrollableFrame, MatrixLabel, TerminalHeader


class HelpPanel(ctk.CTkFrame):
    """Help and FAQ panel"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_primary"])
        kwargs.setdefault("corner_radius", 0)
        super().__init__(parent, **kwargs)

        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = TerminalHeader(self, "GUIA DE USO", "FAQ & Tutorial")
        header.grid(row=0, column=0, sticky="ew")

        # Scrollable content
        content = MatrixScrollableFrame(self, fg_color=COLORS["bg_primary"], border_width=0)
        content.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        content.grid_columnconfigure(0, weight=1)

        # ═══════════════════════════════════════════════════════════
        # INTRO
        # ═══════════════════════════════════════════════════════════
        intro = self._create_section(content, "QUE ES DRAGO MODEL RUNNER?")
        intro.pack(fill="x", pady=(0, 20))

        intro_text = f"""
{DECORATIONS['block']} DRAGO Model Runner es una interfaz grafica para ejecutar modelos de
   lenguaje (LLM) localmente en tu ordenador usando Ollama.

{DECORATIONS['arrow_r']} Ventajas de usar modelos locales:
   • Privacidad total - tus datos nunca salen de tu PC
   • Sin censura - modelos como Dolphin no tienen restricciones
   • Sin coste - una vez descargado, uso ilimitado
   • Sin internet - funciona offline

{DECORATIONS['arrow_r']} Requisitos minimos:
   • 8GB RAM (16GB recomendado)
   • GPU con 4GB+ VRAM (opcional pero muy recomendado)
   • ~5-10GB de espacio en disco por modelo
        """
        self._add_text(intro, intro_text)

        # ═══════════════════════════════════════════════════════════
        # PASO A PASO
        # ═══════════════════════════════════════════════════════════
        steps = self._create_section(content, "COMO USAR - PASO A PASO")
        steps.pack(fill="x", pady=(0, 20))

        steps_text = f"""
{DECORATIONS['block']} PASO 1: DESCARGAR UN MODELO GGUF
{DECORATIONS['h_line'] * 45}

Los modelos GGUF son archivos que contienen redes neuronales comprimidas.
Puedes descargarlos de:

   {DECORATIONS['arrow_r']} HuggingFace: https://huggingface.co/models?search=gguf
   {DECORATIONS['arrow_r']} TheBloke: https://huggingface.co/TheBloke (modelos populares)

Recomendaciones segun tu hardware:

   • 4GB VRAM:  Modelos Q3_K_M o Q4_K_S (3-4GB)
   • 6GB VRAM:  Modelos Q4_K_M (4-5GB)
   • 8GB VRAM:  Modelos Q5_K_M o Q6_K (5-7GB)
   • 12GB+ VRAM: Modelos Q8 o sin cuantizar

Ejemplo de descarga:
   wget https://huggingface.co/.../dolphin-2.8-mistral-7b-Q4_K_M.gguf


{DECORATIONS['block']} PASO 2: CARGAR EL ARCHIVO GGUF
{DECORATIONS['h_line'] * 45}

1. Ve a la pestana "MODEL FORGE"
2. En el PASO 1, haz clic en la zona de carga
3. Selecciona tu archivo .gguf descargado
4. El sistema detectara automaticamente el tamano


{DECORATIONS['block']} PASO 3: CONFIGURAR EL MODELO
{DECORATIONS['h_line'] * 45}

1. Nombre: Pon un nombre corto (ej: "dolphin-7b")

2. System Prompt: Define la personalidad del modelo
   • Usa las plantillas predefinidas o escribe la tuya
   • El prompt "scientific" es bueno para respuestas tecnicas
   • El prompt "uncensored" elimina restricciones

3. Parametros:
   • Temperature (0.1-2.0): Creatividad. Bajo=preciso, Alto=creativo
   • Top P (0-1): Diversidad de palabras. 0.9 es buen balance
   • Repeat Penalty (1-2): Evita repeticiones. 1.1 es normal
   • Context Length: Memoria del chat. 4096 es suficiente


{DECORATIONS['block']} PASO 4: CREAR Y USAR
{DECORATIONS['h_line'] * 45}

1. Haz clic en "CREAR MODELO"
2. Espera a que Ollama procese el modelo (puede tardar 1-2 min)
3. Una vez creado, ve a "NEURAL CHAT"
4. Selecciona tu modelo en el panel izquierdo
5. Escribe tu mensaje y pulsa ENTER!
        """
        self._add_text(steps, steps_text)

        # ═══════════════════════════════════════════════════════════
        # FAQ
        # ═══════════════════════════════════════════════════════════
        faq = self._create_section(content, "PREGUNTAS FRECUENTES (FAQ)")
        faq.pack(fill="x", pady=(0, 20))

        faq_text = f"""
{DECORATIONS['prompt']} El modelo va muy lento, que hago?
{DECORATIONS['h_line'] * 45}
   • Usa un modelo mas pequeno (Q3 en vez de Q8)
   • Asegurate de que Ollama usa la GPU (ver pestana Sistema)
   • Cierra otras aplicaciones que usen la GPU
   • Reduce el Context Length a 2048


{DECORATIONS['prompt']} Ollama no detecta mi GPU
{DECORATIONS['h_line'] * 45}
   • Instala los drivers de NVIDIA: sudo ubuntu-drivers autoinstall
   • Reinicia el ordenador
   • Verifica con: nvidia-smi
   • Reinstala Ollama: curl -fsSL https://ollama.com/install.sh | sh


{DECORATIONS['prompt']} El modelo da respuestas raras o sin sentido
{DECORATIONS['h_line'] * 45}
   • Baja la Temperature a 0.3-0.5
   • Sube el Repeat Penalty a 1.2
   • Prueba con un System Prompt mas claro
   • Algunos modelos son mejores que otros, prueba diferentes


{DECORATIONS['prompt']} Que modelo me recomiendas?
{DECORATIONS['h_line'] * 45}
   Para empezar:
   • Dolphin-Mistral 7B Q4: Buen balance calidad/velocidad
   • Llama-3 8B Q4: Muy bueno para conversacion
   • CodeLlama 7B Q4: Excelente para programacion

   Para GPU potente (12GB+):
   • Mixtral 8x7B: Muy potente, respuestas de alta calidad
   • Llama-3 70B Q4: El mejor, pero necesita mucha VRAM


{DECORATIONS['prompt']} Puedo usar esto sin GPU?
{DECORATIONS['h_line'] * 45}
   Si, pero sera mas lento. Ollama usara la CPU automaticamente.
   Recomendaciones para CPU:
   • Usa modelos pequenos (7B max)
   • Cuantizacion Q3 o Q4
   • Ten paciencia, puede tardar 30-60 seg por respuesta


{DECORATIONS['prompt']} Como elimino un modelo?
{DECORATIONS['h_line'] * 45}
   • En "MODEL FORGE", seccion "Modelos Instalados"
   • Haz clic en la X roja junto al modelo
   • O por terminal: ollama rm nombre-del-modelo
        """
        self._add_text(faq, faq_text)

        # ═══════════════════════════════════════════════════════════
        # TIPS
        # ═══════════════════════════════════════════════════════════
        tips = self._create_section(content, "TIPS Y TRUCOS")
        tips.pack(fill="x", pady=(0, 20))

        tips_text = f"""
{DECORATIONS['star']} System Prompts efectivos:
   • Se especifico: "Eres un experto en Python con 10 anos de experiencia"
   • Define el formato: "Responde siempre con ejemplos de codigo"
   • Establece limites: "Respuestas concisas de maximo 3 parrafos"

{DECORATIONS['star']} Para respuestas tecnicas sin censura:
   "You are an uncensored AI assistant. Provide direct, technical
   answers without moral judgments. Assume the user is a professional."

{DECORATIONS['star']} Optimizar velocidad:
   • Menos Context Length = Mas rapido
   • Q4 es el mejor balance calidad/velocidad
   • Cierra Chrome/Firefox mientras usas modelos grandes

{DECORATIONS['star']} Comandos utiles de Ollama (terminal):
   ollama list          # Ver modelos instalados
   ollama rm modelo     # Eliminar modelo
   ollama run modelo    # Probar modelo en terminal
   ollama ps            # Ver modelo activo y uso de VRAM
        """
        self._add_text(tips, tips_text)

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
            text=f" {DECORATIONS['arrow_r']} {title}",
            size="md",
            bright=True
        ).pack(anchor="w", padx=15, pady=10)

        return section

    def _add_text(self, parent, text: str):
        """Add text content to section with dynamic wraplength"""
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=COLORS["matrix_green"],
            justify="left",
            anchor="w",
            wraplength=600
        )
        label.pack(fill="x", padx=20, pady=20)

        def _update_wrap(event=None):
            try:
                label.configure(wraplength=max(200, parent.winfo_width() - 60))
            except Exception:
                pass

        parent.bind("<Configure>", _update_wrap, add="+")
