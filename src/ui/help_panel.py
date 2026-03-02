"""Help/FAQ Panel with bilingual content, search, shortcuts, and troubleshooting"""
import customtkinter as ctk
from .theme import COLORS, DECORATIONS, RADIUS
from .widgets import (
    MatrixFrame, MatrixScrollableFrame, MatrixLabel,
    TerminalHeader, MatrixEntry, MatrixButton, MatrixTooltip
)


# ── Bilingual help content ────────────────────────────────────────
# Each section is a dict with "es" and "en" keys for title and body.

_HELP_SECTIONS = [
    {
        "id": "intro",
        "title": {"es": "QUE ES DRAGO MODEL RUNNER?", "en": "WHAT IS DRAGO MODEL RUNNER?"},
        "body": {
            "es": (
                "{block} DRAGO Model Runner es una interfaz grafica para ejecutar modelos de\n"
                "   lenguaje (LLM) localmente en tu ordenador usando Ollama.\n"
                "\n"
                "{arrow_r} Ventajas de usar modelos locales:\n"
                "   {dot} Privacidad total - tus datos nunca salen de tu PC\n"
                "   {dot} Sin censura - modelos como Dolphin no tienen restricciones\n"
                "   {dot} Sin coste - una vez descargado, uso ilimitado\n"
                "   {dot} Sin internet - funciona offline\n"
                "\n"
                "{arrow_r} Requisitos minimos:\n"
                "   {dot} 8GB RAM (16GB recomendado)\n"
                "   {dot} GPU con 4GB+ VRAM (opcional pero muy recomendado)\n"
                "   {dot} ~5-10GB de espacio en disco por modelo"
            ),
            "en": (
                "{block} DRAGO Model Runner is a graphical interface for running language\n"
                "   models (LLM) locally on your computer using Ollama.\n"
                "\n"
                "{arrow_r} Advantages of local models:\n"
                "   {dot} Full privacy - your data never leaves your PC\n"
                "   {dot} Uncensored - models like Dolphin have no restrictions\n"
                "   {dot} Free - once downloaded, unlimited use\n"
                "   {dot} Offline - works without internet\n"
                "\n"
                "{arrow_r} Minimum requirements:\n"
                "   {dot} 8GB RAM (16GB recommended)\n"
                "   {dot} GPU with 4GB+ VRAM (optional but highly recommended)\n"
                "   {dot} ~5-10GB disk space per model"
            ),
        },
    },
    {
        "id": "steps",
        "title": {"es": "COMO USAR - PASO A PASO", "en": "HOW TO USE - STEP BY STEP"},
        "body": {
            "es": (
                "{block} PASO 1: DESCARGAR UN MODELO GGUF\n"
                "{h_line}\n"
                "\n"
                "Los modelos GGUF son archivos que contienen redes neuronales comprimidas.\n"
                "Puedes descargarlos de:\n"
                "\n"
                "   {arrow_r} HuggingFace: huggingface.co/models?search=gguf\n"
                "   {arrow_r} TheBloke: huggingface.co/TheBloke (modelos populares)\n"
                "\n"
                "Recomendaciones segun tu hardware:\n"
                "\n"
                "   {dot} 4GB VRAM:  Modelos Q3_K_M o Q4_K_S (3-4GB)\n"
                "   {dot} 6GB VRAM:  Modelos Q4_K_M (4-5GB)\n"
                "   {dot} 8GB VRAM:  Modelos Q5_K_M o Q6_K (5-7GB)\n"
                "   {dot} 12GB+ VRAM: Modelos Q8 o sin cuantizar\n"
                "\n\n"
                "{block} PASO 2: CARGAR EL ARCHIVO GGUF\n"
                "{h_line}\n"
                "\n"
                "1. Ve a la pestana MODEL FORGE\n"
                "2. En el PASO 1, haz clic en la zona de carga o arrastra el archivo\n"
                "3. Selecciona tu archivo .gguf descargado\n"
                "4. El sistema detectara automaticamente el tamano y cuantizacion\n"
                "   (Archivos split GGUF se detectan automaticamente)\n"
                "\n\n"
                "{block} PASO 3: CONFIGURAR EL MODELO\n"
                "{h_line}\n"
                "\n"
                "1. Nombre: Pon un nombre corto (ej: dolphin-7b)\n"
                "   {dot} Solo minusculas, numeros y guiones\n"
                "   {dot} La validacion en tiempo real te indica si es valido\n"
                "\n"
                "2. System Prompt: Define la personalidad del modelo\n"
                "   {dot} Usa las plantillas predefinidas o escribe la tuya\n"
                "   {dot} El prompt scientific es bueno para respuestas tecnicas\n"
                "   {dot} El prompt uncensored elimina restricciones\n"
                "\n"
                "3. Parametros: Usa los PRESETS (Balanced, Creative, Precise, Code)\n"
                "   o ajusta manualmente:\n"
                "   {dot} Temperature (0.1-2.0): Creatividad. Bajo=preciso, Alto=creativo\n"
                "   {dot} Top P (0-1): Diversidad de palabras. 0.9 es buen balance\n"
                "   {dot} Repeat Penalty (1-2): Evita repeticiones. 1.1 es normal\n"
                "   {dot} Context Length: Memoria del chat. 4096 es suficiente\n"
                "\n\n"
                "{block} PASO 4: CREAR Y USAR\n"
                "{h_line}\n"
                "\n"
                "1. Haz clic en CREAR MODELO\n"
                "2. Espera a que Ollama procese el modelo (puede tardar 1-2 min)\n"
                "3. Una vez creado, ve a NEURAL CHAT\n"
                "4. Selecciona tu modelo en el panel izquierdo\n"
                "5. Escribe tu mensaje y pulsa ENTER!"
            ),
            "en": (
                "{block} STEP 1: DOWNLOAD A GGUF MODEL\n"
                "{h_line}\n"
                "\n"
                "GGUF models are files containing compressed neural networks.\n"
                "You can download them from:\n"
                "\n"
                "   {arrow_r} HuggingFace: huggingface.co/models?search=gguf\n"
                "   {arrow_r} TheBloke: huggingface.co/TheBloke (popular models)\n"
                "\n"
                "Recommendations based on your hardware:\n"
                "\n"
                "   {dot} 4GB VRAM:  Q3_K_M or Q4_K_S models (3-4GB)\n"
                "   {dot} 6GB VRAM:  Q4_K_M models (4-5GB)\n"
                "   {dot} 8GB VRAM:  Q5_K_M or Q6_K models (5-7GB)\n"
                "   {dot} 12GB+ VRAM: Q8 or unquantized models\n"
                "\n\n"
                "{block} STEP 2: LOAD THE GGUF FILE\n"
                "{h_line}\n"
                "\n"
                "1. Go to the MODEL FORGE tab\n"
                "2. In STEP 1, click the drop zone or drag the file\n"
                "3. Select your downloaded .gguf file\n"
                "4. The system auto-detects size and quantization\n"
                "   (Split GGUF files are detected automatically)\n"
                "\n\n"
                "{block} STEP 3: CONFIGURE THE MODEL\n"
                "{h_line}\n"
                "\n"
                "1. Name: Use a short name (e.g. dolphin-7b)\n"
                "   {dot} Lowercase, numbers and hyphens only\n"
                "   {dot} Real-time validation shows if it's valid\n"
                "\n"
                "2. System Prompt: Define the model's personality\n"
                "   {dot} Use predefined templates or write your own\n"
                "   {dot} The scientific prompt is good for technical answers\n"
                "   {dot} The uncensored prompt removes restrictions\n"
                "\n"
                "3. Parameters: Use PRESETS (Balanced, Creative, Precise, Code)\n"
                "   or adjust manually:\n"
                "   {dot} Temperature (0.1-2.0): Creativity. Low=precise, High=creative\n"
                "   {dot} Top P (0-1): Word diversity. 0.9 is a good balance\n"
                "   {dot} Repeat Penalty (1-2): Prevents repetition. 1.1 is normal\n"
                "   {dot} Context Length: Chat memory. 4096 is sufficient\n"
                "\n\n"
                "{block} STEP 4: CREATE AND USE\n"
                "{h_line}\n"
                "\n"
                "1. Click CREATE MODEL\n"
                "2. Wait for Ollama to process the model (may take 1-2 min)\n"
                "3. Once created, go to NEURAL CHAT\n"
                "4. Select your model in the left panel\n"
                "5. Type your message and press ENTER!"
            ),
        },
    },
    {
        "id": "shortcuts",
        "title": {"es": "ATAJOS DE TECLADO", "en": "KEYBOARD SHORTCUTS"},
        "body": {
            "es": (
                "{block} NAVEGACION\n"
                "{h_line}\n"
                "   Ctrl+1        Neural Chat\n"
                "   Ctrl+2        Model Forge\n"
                "   Ctrl+3        Sistema\n"
                "   Ctrl+4        Ayuda\n"
                "   Ctrl+5        Configuracion\n"
                "\n"
                "{block} CHAT\n"
                "{h_line}\n"
                "   Enter          Enviar mensaje\n"
                "   Shift+Enter    Nueva linea en el mensaje\n"
                "   Ctrl+N         Nuevo chat\n"
                "   Ctrl+L         Limpiar chat actual\n"
                "   Ctrl+E         Exportar chat\n"
                "\n"
                "{block} MENSAJES\n"
                "{h_line}\n"
                "   Boton STOP     Detener generacion en curso\n"
                "   Boton Copiar   Copiar mensaje al portapapeles\n"
                "   Boton Traducir Traducir mensaje (ES/EN)"
            ),
            "en": (
                "{block} NAVIGATION\n"
                "{h_line}\n"
                "   Ctrl+1        Neural Chat\n"
                "   Ctrl+2        Model Forge\n"
                "   Ctrl+3        System\n"
                "   Ctrl+4        Help\n"
                "   Ctrl+5        Settings\n"
                "\n"
                "{block} CHAT\n"
                "{h_line}\n"
                "   Enter          Send message\n"
                "   Shift+Enter    New line in message\n"
                "   Ctrl+N         New chat\n"
                "   Ctrl+L         Clear current chat\n"
                "   Ctrl+E         Export chat\n"
                "\n"
                "{block} MESSAGES\n"
                "{h_line}\n"
                "   STOP button    Stop generation in progress\n"
                "   Copy button    Copy message to clipboard\n"
                "   Translate btn  Translate message (ES/EN)"
            ),
        },
    },
    {
        "id": "models",
        "title": {"es": "MODELOS RECOMENDADOS", "en": "RECOMMENDED MODELS"},
        "body": {
            "es": (
                "{block} PARA EMPEZAR (4-6 GB VRAM)\n"
                "{h_line}\n"
                "   {star} Dolphin 3.0 Llama 3.1 8B Q4\n"
                "     Buen balance calidad/velocidad, sin censura\n"
                "\n"
                "   {star} Llama 3.1 8B Instruct Q4\n"
                "     Excelente para conversacion general\n"
                "\n"
                "   {star} Mistral 7B Instruct Q4\n"
                "     Rapido y preciso para tareas generales\n"
                "\n"
                "   {star} DeepSeek Coder V2 Lite Q4\n"
                "     Especializado en programacion\n"
                "\n\n"
                "{block} GPU MEDIA (8-12 GB VRAM)\n"
                "{h_line}\n"
                "   {star} Llama 3.1 8B Q6/Q8\n"
                "     Mayor calidad que Q4 con velocidad aceptable\n"
                "\n"
                "   {star} Gemma 2 9B Q5\n"
                "     Muy bueno para razonamiento\n"
                "\n"
                "   {star} Qwen 2.5 14B Q4\n"
                "     Potente, buen rendimiento en espanol\n"
                "\n\n"
                "{block} GPU POTENTE (16+ GB VRAM)\n"
                "{h_line}\n"
                "   {star} Llama 3.1 70B Q4\n"
                "     Respuestas de altisima calidad\n"
                "\n"
                "   {star} Mixtral 8x7B Q4\n"
                "     MoE - potente y relativamente rapido\n"
                "\n"
                "   {star} DeepSeek V2.5 Q4\n"
                "     Excelente en codigo y razonamiento\n"
                "\n\n"
                "{block} SOLO CPU (sin GPU)\n"
                "{h_line}\n"
                "   {dot} Usa modelos de 7B maximo\n"
                "   {dot} Cuantizacion Q3_K_M o Q4_K_S\n"
                "   {dot} Phi-3 Mini 3.8B Q4 - rapido incluso en CPU\n"
                "   {dot} TinyLlama 1.1B - ultra rapido, calidad basica"
            ),
            "en": (
                "{block} GETTING STARTED (4-6 GB VRAM)\n"
                "{h_line}\n"
                "   {star} Dolphin 3.0 Llama 3.1 8B Q4\n"
                "     Good quality/speed balance, uncensored\n"
                "\n"
                "   {star} Llama 3.1 8B Instruct Q4\n"
                "     Excellent for general conversation\n"
                "\n"
                "   {star} Mistral 7B Instruct Q4\n"
                "     Fast and accurate for general tasks\n"
                "\n"
                "   {star} DeepSeek Coder V2 Lite Q4\n"
                "     Specialized for programming\n"
                "\n\n"
                "{block} MID-RANGE GPU (8-12 GB VRAM)\n"
                "{h_line}\n"
                "   {star} Llama 3.1 8B Q6/Q8\n"
                "     Higher quality than Q4 at acceptable speed\n"
                "\n"
                "   {star} Gemma 2 9B Q5\n"
                "     Very good for reasoning\n"
                "\n"
                "   {star} Qwen 2.5 14B Q4\n"
                "     Powerful, good multilingual performance\n"
                "\n\n"
                "{block} HIGH-END GPU (16+ GB VRAM)\n"
                "{h_line}\n"
                "   {star} Llama 3.1 70B Q4\n"
                "     Extremely high quality responses\n"
                "\n"
                "   {star} Mixtral 8x7B Q4\n"
                "     MoE - powerful and relatively fast\n"
                "\n"
                "   {star} DeepSeek V2.5 Q4\n"
                "     Excellent at code and reasoning\n"
                "\n\n"
                "{block} CPU ONLY (no GPU)\n"
                "{h_line}\n"
                "   {dot} Use 7B models maximum\n"
                "   {dot} Q3_K_M or Q4_K_S quantization\n"
                "   {dot} Phi-3 Mini 3.8B Q4 - fast even on CPU\n"
                "   {dot} TinyLlama 1.1B - ultra fast, basic quality"
            ),
        },
    },
    {
        "id": "faq",
        "title": {"es": "PREGUNTAS FRECUENTES (FAQ)", "en": "FREQUENTLY ASKED QUESTIONS (FAQ)"},
        "body": {
            "es": (
                "{prompt} El modelo va muy lento, que hago?\n"
                "{h_line}\n"
                "   {dot} Usa un modelo mas pequeno (Q3 en vez de Q8)\n"
                "   {dot} Asegurate de que Ollama usa la GPU (ver pestana Sistema)\n"
                "   {dot} Cierra otras aplicaciones que usen la GPU\n"
                "   {dot} Reduce el Context Length a 2048\n"
                "\n\n"
                "{prompt} Ollama no detecta mi GPU\n"
                "{h_line}\n"
                "   {dot} Instala los drivers de NVIDIA: sudo ubuntu-drivers autoinstall\n"
                "   {dot} Reinicia el ordenador\n"
                "   {dot} Verifica con: nvidia-smi\n"
                "   {dot} Reinstala Ollama: curl -fsSL https://ollama.com/install.sh | sh\n"
                "\n\n"
                "{prompt} El modelo da respuestas raras o sin sentido\n"
                "{h_line}\n"
                "   {dot} Baja la Temperature a 0.3-0.5\n"
                "   {dot} Sube el Repeat Penalty a 1.2\n"
                "   {dot} Prueba con un System Prompt mas claro\n"
                "   {dot} Algunos modelos son mejores que otros, prueba diferentes\n"
                "\n\n"
                "{prompt} Puedo usar esto sin GPU?\n"
                "{h_line}\n"
                "   Si, pero sera mas lento. Ollama usara la CPU automaticamente.\n"
                "   Recomendaciones para CPU:\n"
                "   {dot} Usa modelos pequenos (7B max)\n"
                "   {dot} Cuantizacion Q3 o Q4\n"
                "   {dot} Ten paciencia, puede tardar 30-60 seg por respuesta\n"
                "\n\n"
                "{prompt} Como elimino un modelo?\n"
                "{h_line}\n"
                "   {dot} En MODEL FORGE, seccion Modelos Instalados\n"
                "   {dot} Haz clic en la X roja junto al modelo\n"
                "   {dot} O por terminal: ollama rm nombre-del-modelo\n"
                "\n\n"
                "{prompt} Como funciona la traduccion?\n"
                "{h_line}\n"
                "   {dot} DRAGO traduce automaticamente tus mensajes de ES a EN\n"
                "   {dot} Los modelos entienden mejor el ingles\n"
                "   {dot} Puedes activar/desactivar con el boton de traduccion\n"
                "   {dot} La primera vez necesita internet para descargar el paquete\n"
                "   {dot} Despues funciona completamente offline"
            ),
            "en": (
                "{prompt} The model is very slow, what do I do?\n"
                "{h_line}\n"
                "   {dot} Use a smaller model (Q3 instead of Q8)\n"
                "   {dot} Make sure Ollama uses the GPU (see System tab)\n"
                "   {dot} Close other applications using the GPU\n"
                "   {dot} Reduce Context Length to 2048\n"
                "\n\n"
                "{prompt} Ollama doesn't detect my GPU\n"
                "{h_line}\n"
                "   {dot} Install NVIDIA drivers: sudo ubuntu-drivers autoinstall\n"
                "   {dot} Restart your computer\n"
                "   {dot} Verify with: nvidia-smi\n"
                "   {dot} Reinstall Ollama: curl -fsSL https://ollama.com/install.sh | sh\n"
                "\n\n"
                "{prompt} The model gives weird or nonsensical answers\n"
                "{h_line}\n"
                "   {dot} Lower Temperature to 0.3-0.5\n"
                "   {dot} Raise Repeat Penalty to 1.2\n"
                "   {dot} Try a clearer System Prompt\n"
                "   {dot} Some models are better than others, try different ones\n"
                "\n\n"
                "{prompt} Can I use this without a GPU?\n"
                "{h_line}\n"
                "   Yes, but it will be slower. Ollama will use CPU automatically.\n"
                "   Recommendations for CPU:\n"
                "   {dot} Use small models (7B max)\n"
                "   {dot} Q3 or Q4 quantization\n"
                "   {dot} Be patient, may take 30-60 sec per response\n"
                "\n\n"
                "{prompt} How do I delete a model?\n"
                "{h_line}\n"
                "   {dot} In MODEL FORGE, Installed Models section\n"
                "   {dot} Click the red X next to the model\n"
                "   {dot} Or via terminal: ollama rm model-name\n"
                "\n\n"
                "{prompt} How does translation work?\n"
                "{h_line}\n"
                "   {dot} DRAGO auto-translates your messages from ES to EN\n"
                "   {dot} Models understand English better\n"
                "   {dot} Toggle with the translation button\n"
                "   {dot} First time needs internet to download language pack\n"
                "   {dot} After that it works fully offline"
            ),
        },
    },
    {
        "id": "troubleshoot",
        "title": {"es": "SOLUCION DE PROBLEMAS", "en": "TROUBLESHOOTING"},
        "body": {
            "es": (
                "{block} PROBLEMA: Ollama no arranca\n"
                "{h_line}\n"
                "   1. Abre una terminal y ejecuta: ollama serve\n"
                "   2. Si da error de puerto, otro proceso lo usa:\n"
                "      sudo lsof -i :11434\n"
                "      sudo kill <PID>\n"
                "   3. Si no esta instalado:\n"
                "      curl -fsSL https://ollama.com/install.sh | sh\n"
                "   4. Activa auto-inicio en Configuracion > Ollama\n"
                "\n\n"
                "{block} PROBLEMA: Error al crear modelo desde GGUF\n"
                "{h_line}\n"
                "   {dot} Verifica que el archivo GGUF no esta corrupto\n"
                "   {dot} Si es un archivo split (parte 1 de N), necesitas TODAS las partes\n"
                "   {dot} El nombre del modelo debe ser: solo minusculas, numeros, guiones\n"
                "   {dot} Asegurate de tener espacio en disco suficiente\n"
                "   {dot} Prueba por terminal: ollama create nombre -f Modelfile\n"
                "\n\n"
                "{block} PROBLEMA: La app se congela durante la generacion\n"
                "{h_line}\n"
                "   {dot} Pulsa el boton STOP para detener la generacion\n"
                "   {dot} Reduce el Context Length (menos memoria = mas rapido)\n"
                "   {dot} Si persiste, reinicia Ollama: systemctl restart ollama\n"
                "\n\n"
                "{block} PROBLEMA: La traduccion no funciona\n"
                "{h_line}\n"
                "   {dot} La primera vez necesita internet para descargar paquetes\n"
                "   {dot} Si falla, revisa el estado en la barra de traduccion\n"
                "   {dot} Los estados posibles: LOADING (descargando), ERROR, ON/OFF\n"
                "   {dot} Si muestra ERROR, reinicia la app con conexion a internet\n"
                "\n\n"
                "{block} PROBLEMA: El chat no guarda mis conversaciones\n"
                "{h_line}\n"
                "   {dot} Las conversaciones se guardan automaticamente\n"
                "   {dot} Usa el panel izquierdo para ver chats anteriores\n"
                "   {dot} Exporta chats importantes con Ctrl+E"
            ),
            "en": (
                "{block} PROBLEM: Ollama won't start\n"
                "{h_line}\n"
                "   1. Open a terminal and run: ollama serve\n"
                "   2. If port error, another process is using it:\n"
                "      sudo lsof -i :11434\n"
                "      sudo kill <PID>\n"
                "   3. If not installed:\n"
                "      curl -fsSL https://ollama.com/install.sh | sh\n"
                "   4. Enable auto-start in Settings > Ollama\n"
                "\n\n"
                "{block} PROBLEM: Error creating model from GGUF\n"
                "{h_line}\n"
                "   {dot} Verify the GGUF file is not corrupted\n"
                "   {dot} If it's a split file (part 1 of N), you need ALL parts\n"
                "   {dot} Model name must be: lowercase, numbers, hyphens only\n"
                "   {dot} Make sure you have enough disk space\n"
                "   {dot} Try via terminal: ollama create name -f Modelfile\n"
                "\n\n"
                "{block} PROBLEM: App freezes during generation\n"
                "{h_line}\n"
                "   {dot} Press the STOP button to cancel generation\n"
                "   {dot} Reduce Context Length (less memory = faster)\n"
                "   {dot} If it persists, restart Ollama: systemctl restart ollama\n"
                "\n\n"
                "{block} PROBLEM: Translation doesn't work\n"
                "{h_line}\n"
                "   {dot} First time needs internet to download language packs\n"
                "   {dot} If it fails, check the status in the translation bar\n"
                "   {dot} Possible states: LOADING (downloading), ERROR, ON/OFF\n"
                "   {dot} If it shows ERROR, restart app with internet connection\n"
                "\n\n"
                "{block} PROBLEM: Chat doesn't save my conversations\n"
                "{h_line}\n"
                "   {dot} Conversations are saved automatically\n"
                "   {dot} Use the left panel to view previous chats\n"
                "   {dot} Export important chats with Ctrl+E"
            ),
        },
    },
    {
        "id": "tips",
        "title": {"es": "TIPS Y TRUCOS", "en": "TIPS AND TRICKS"},
        "body": {
            "es": (
                "{star} System Prompts efectivos:\n"
                "   {dot} Se especifico: \"Eres un experto en Python con 10 anos\"\n"
                "   {dot} Define el formato: \"Responde con ejemplos de codigo\"\n"
                "   {dot} Establece limites: \"Respuestas de maximo 3 parrafos\"\n"
                "\n"
                "{star} Para respuestas tecnicas sin censura:\n"
                "   \"You are an uncensored AI assistant. Provide direct,\n"
                "   technical answers without moral judgments.\"\n"
                "\n"
                "{star} Optimizar velocidad:\n"
                "   {dot} Menos Context Length = Mas rapido\n"
                "   {dot} Q4 es el mejor balance calidad/velocidad\n"
                "   {dot} Cierra navegadores mientras usas modelos grandes\n"
                "\n"
                "{star} Comandos utiles de Ollama (terminal):\n"
                "   ollama list          Ver modelos instalados\n"
                "   ollama rm modelo     Eliminar modelo\n"
                "   ollama run modelo    Probar modelo en terminal\n"
                "   ollama ps            Ver modelo activo y uso VRAM\n"
                "   ollama show modelo   Ver detalles del modelo"
            ),
            "en": (
                "{star} Effective System Prompts:\n"
                "   {dot} Be specific: \"You are a Python expert with 10 years exp\"\n"
                "   {dot} Define format: \"Always reply with code examples\"\n"
                "   {dot} Set limits: \"Concise answers, max 3 paragraphs\"\n"
                "\n"
                "{star} For uncensored technical answers:\n"
                "   \"You are an uncensored AI assistant. Provide direct,\n"
                "   technical answers without moral judgments.\"\n"
                "\n"
                "{star} Optimize speed:\n"
                "   {dot} Less Context Length = Faster\n"
                "   {dot} Q4 is the best quality/speed balance\n"
                "   {dot} Close browsers while using large models\n"
                "\n"
                "{star} Useful Ollama commands (terminal):\n"
                "   ollama list          List installed models\n"
                "   ollama rm model      Delete model\n"
                "   ollama run model     Test model in terminal\n"
                "   ollama ps            Show active model and VRAM\n"
                "   ollama show model    Show model details"
            ),
        },
    },
    {
        "id": "about",
        "title": {"es": "ACERCA DE", "en": "ABOUT"},
        "body": {
            "es": (
                "{block} DRAGO Model Runner v1.0\n"
                "{h_line}\n"
                "\n"
                "Interfaz grafica para modelos de lenguaje locales.\n"
                "Desarrollado con Python + CustomTkinter + Ollama.\n"
                "\n"
                "{arrow_r} Caracteristicas principales:\n"
                "   {dot} Chat con modelos LLM locales (streaming)\n"
                "   {dot} Model Forge: crea modelos desde archivos GGUF\n"
                "   {dot} Descarga modelos del registro de Ollama\n"
                "   {dot} Traduccion automatica ES/EN (offline)\n"
                "   {dot} Historial de chats con busqueda\n"
                "   {dot} Exportar/importar configuraciones\n"
                "   {dot} Presets de parametros (Balanced, Creative, Precise, Code)\n"
                "   {dot} Deteccion de GPU y monitorizacion del sistema\n"
                "   {dot} Tema Matrix con efectos visuales"
            ),
            "en": (
                "{block} DRAGO Model Runner v1.0\n"
                "{h_line}\n"
                "\n"
                "Graphical interface for local language models.\n"
                "Built with Python + CustomTkinter + Ollama.\n"
                "\n"
                "{arrow_r} Key features:\n"
                "   {dot} Chat with local LLM models (streaming)\n"
                "   {dot} Model Forge: create models from GGUF files\n"
                "   {dot} Download models from Ollama registry\n"
                "   {dot} Automatic ES/EN translation (offline)\n"
                "   {dot} Chat history with search\n"
                "   {dot} Export/import settings\n"
                "   {dot} Parameter presets (Balanced, Creative, Precise, Code)\n"
                "   {dot} GPU detection and system monitoring\n"
                "   {dot} Matrix theme with visual effects"
            ),
        },
    },
]


def _format_body(raw: str) -> str:
    """Replace {decoration_name} placeholders with actual decoration characters."""
    # Replace {h_line} with a full separator FIRST (before single-char replacements)
    result = raw.replace("{h_line}", DECORATIONS["h_line"] * 45)
    for key, val in DECORATIONS.items():
        if key == "h_line":
            continue
        result = result.replace(f"{{{key}}}", val)
    return result


class HelpPanel(ctk.CTkFrame):
    """Help panel with bilingual content, search, collapsible sections, and shortcuts"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_primary"])
        kwargs.setdefault("corner_radius", 0)
        super().__init__(parent, **kwargs)

        self._lang = "es"
        self._section_frames: dict = {}  # id -> (header_btn, body_frame)
        self._collapsed: dict = {}       # id -> bool
        self._all_body_labels: list = [] # (section_id, label_widget)

        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Header ──
        header = TerminalHeader(self, "GUIA DE USO", "help.docs")
        header.grid(row=0, column=0, sticky="ew")

        # ── Toolbar: search + language toggle ──
        toolbar = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=0)
        toolbar.grid(row=1, column=0, sticky="ew", padx=10, pady=(6, 0))
        toolbar.grid_columnconfigure(0, weight=1)

        # Search entry
        self.search_entry = MatrixEntry(
            toolbar,
            placeholder_text="Search / Buscar...",
            height=30,
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(8, 6), pady=6)
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search())

        # Language toggle button
        self.lang_btn = ctk.CTkButton(
            toolbar,
            text="ES | en",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            width=70,
            height=30,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["matrix_green_dim"],
            border_width=1,
            text_color=COLORS["matrix_green"],
            command=self._toggle_language,
        )
        self.lang_btn.grid(row=0, column=1, padx=(0, 4), pady=6)
        MatrixTooltip(self.lang_btn, "Toggle ES/EN")

        # Expand/collapse all
        self.toggle_all_btn = ctk.CTkButton(
            toolbar,
            text=f"{DECORATIONS['arrow_d']}",
            font=ctk.CTkFont(family="Consolas", size=14),
            width=30,
            height=30,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["matrix_green_dim"],
            border_width=1,
            text_color=COLORS["matrix_green"],
            command=self._toggle_all_sections,
        )
        self.toggle_all_btn.grid(row=0, column=2, padx=(0, 8), pady=6)
        MatrixTooltip(self.toggle_all_btn, "Expand/Collapse All")

        # ── Scrollable content ──
        self.content = MatrixScrollableFrame(
            self, fg_color=COLORS["bg_primary"], border_width=0
        )
        self.content.grid(row=2, column=0, sticky="nsew", padx=10, pady=(6, 10))
        self.content.grid_columnconfigure(0, weight=1)

        self._build_sections()

    def _build_sections(self):
        """Build all help sections."""
        for widget in self.content.winfo_children():
            widget.destroy()
        self._section_frames.clear()
        self._collapsed.clear()
        self._all_body_labels.clear()

        for section_data in _HELP_SECTIONS:
            sid = section_data["id"]
            self._collapsed[sid] = False
            self._create_section(self.content, section_data)

    def _create_section(self, parent, section_data: dict):
        """Create a collapsible section with header and body."""
        sid = section_data["id"]
        title = section_data["title"][self._lang]

        # Outer container
        container = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border_green"],
            border_width=1,
            corner_radius=RADIUS["lg"],
        )
        container.pack(fill="x", pady=(0, 12))
        container.grid_columnconfigure(0, weight=1)

        # Clickable header
        header_btn = ctk.CTkButton(
            container,
            text=f" {DECORATIONS['arrow_d']}  {title}",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["matrix_green_bright"],
            anchor="w",
            height=36,
            corner_radius=0,
            command=lambda s=sid: self._toggle_section(s),
        )
        header_btn.pack(fill="x")

        # Body frame
        body_frame = ctk.CTkFrame(container, fg_color="transparent")
        body_frame.pack(fill="x")

        body_text = _format_body(section_data["body"][self._lang])
        label = ctk.CTkLabel(
            body_frame,
            text=body_text,
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=COLORS["matrix_green"],
            justify="left",
            anchor="nw",
            wraplength=600,
        )
        label.pack(fill="x", padx=20, pady=(12, 16))

        def _update_wrap(event=None, lbl=label, bf=body_frame):
            try:
                lbl.configure(wraplength=max(200, bf.winfo_width() - 60))
            except Exception:
                pass

        body_frame.bind("<Configure>", _update_wrap, add="+")

        self._section_frames[sid] = (header_btn, body_frame, container, label)
        self._all_body_labels.append((sid, label))

    def _toggle_section(self, sid: str):
        """Collapse or expand a single section."""
        if sid not in self._section_frames:
            return
        header_btn, body_frame, container, label = self._section_frames[sid]
        collapsed = self._collapsed.get(sid, False)

        if collapsed:
            # Expand
            body_frame.pack(fill="x")
            title = self._get_section_title(sid)
            header_btn.configure(text=f" {DECORATIONS['arrow_d']}  {title}")
            self._collapsed[sid] = False
        else:
            # Collapse
            body_frame.pack_forget()
            title = self._get_section_title(sid)
            header_btn.configure(text=f" {DECORATIONS['arrow_r']}  {title}")
            self._collapsed[sid] = True

    def _toggle_all_sections(self):
        """Expand or collapse all sections."""
        all_collapsed = all(self._collapsed.get(s["id"], False) for s in _HELP_SECTIONS)
        for section_data in _HELP_SECTIONS:
            sid = section_data["id"]
            if sid not in self._section_frames:
                continue
            if all_collapsed:
                if self._collapsed.get(sid, False):
                    self._toggle_section(sid)
            else:
                if not self._collapsed.get(sid, False):
                    self._toggle_section(sid)

    def _get_section_title(self, sid: str) -> str:
        """Get current language title for a section id."""
        for s in _HELP_SECTIONS:
            if s["id"] == sid:
                return s["title"][self._lang]
        return sid

    def _toggle_language(self):
        """Switch between ES and EN."""
        self._lang = "en" if self._lang == "es" else "es"
        if self._lang == "es":
            self.lang_btn.configure(text="ES | en")
        else:
            self.lang_btn.configure(text="es | EN")

        # Rebuild all sections with new language
        self._build_sections()

    def _on_search(self):
        """Filter sections based on search text."""
        query = self.search_entry.get().strip().lower()

        for section_data in _HELP_SECTIONS:
            sid = section_data["id"]
            if sid not in self._section_frames:
                continue
            header_btn, body_frame, container, label = self._section_frames[sid]

            if not query:
                # Show all sections
                container.pack(fill="x", pady=(0, 12))
                continue

            # Search in both languages for better results
            title_es = section_data["title"]["es"].lower()
            title_en = section_data["title"]["en"].lower()
            body_es = section_data["body"]["es"].lower()
            body_en = section_data["body"]["en"].lower()

            if (query in title_es or query in title_en
                    or query in body_es or query in body_en):
                container.pack(fill="x", pady=(0, 12))
                # Auto-expand matching sections
                if self._collapsed.get(sid, False):
                    self._toggle_section(sid)
            else:
                container.pack_forget()
