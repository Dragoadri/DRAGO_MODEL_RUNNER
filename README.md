```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     ██████╗ ██████╗  █████╗  ██████╗  ██████╗                                ║
║     ██╔══██╗██╔══██╗██╔══██╗██╔════╝ ██╔═══██╗                               ║
║     ██║  ██║██████╔╝███████║██║  ███╗██║   ██║                               ║
║     ██║  ██║██╔══██╗██╔══██║██║   ██║██║   ██║                               ║
║     ██████╔╝██║  ██║██║  ██║╚██████╔╝╚██████╔╝                               ║
║     ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝                                ║
║                                                                              ║
║     M O D E L   R U N N E R  //  M A T R I X   E D I T I O N                 ║
║                                                                              ║
║     [ LOCAL LLM INFERENCE INTERFACE ]                                        ║
║     [ NO CLOUD • NO CENSORSHIP • NO LIMITS ]                                 ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

> *"I know kung fu." — Neo*
>
> *"Show me." — Morpheus*

---

## ▸ WHAT IS THIS

DRAGO Model Runner is a **cyberpunk-themed desktop application** for running Large Language Models locally on your machine. No API keys. No cloud. No filters. Just you and your GPU.

Built on top of [Ollama](https://ollama.ai), wrapped in a **Matrix-inspired terminal UI** with glowing green text, rain animations, and the aesthetic of a 90s hacker's dream.

```
    ┌─────────────────────────────────────────────────┐
    │  ╔══════════════════════╗  ┌──────────────────┐ │
    │  ║  ██████╗ ██████╗     ║  │ NEURAL INTERFACE │ │
    │  ║  ██╔══██╗██╔══██╗    ║  ├──────────────────┤ │
    │  ║  ██║  ██║██████╔╝    ║  │ ▌ USER           │ │
    │  ║  ██║  ██║██╔══██╗    ║  │   How do I...    │ │
    │  ║  ██████╔╝██║  ██║    ║  │                  │ │
    │  ║  ╚═════╝ ╚═╝  ╚═╝    ║  │ █ DRAGO          │ │
    │  ║    DRAGO RUNNER      ║  │   Here's how:    │ │
    │  ╚══════════════════════╝  │   ```python      │ │
    │                            │   def solve()... │ │
    │  ● Ollama Online           │                  │ │
    │  → GPU: RTX 5060           │                  │ │
    │                            ├──────────────────┤ │
    │  [⌨ CHAT] [⚙ FORGE]       │ ▸ INPUT:         │ │
    │  [☰ SYS ] [? HELP ]       │ [_______________]│ │
    │  [⌘ CFG ]                  │        [→ SEND]  │ │
    │                            │        [ CLEAR]  │ │
    │  ─────────────────         └──────────────────┘ │
    │  █ MODEL                                        │
    │  [deepseek-r1:7b ▾]                             │
    │                                                 │
    │  ▸ NEW CHAT                                     │
    │  ┌─────────────────┐                            │
    │  │ Chat about code │                            │
    │  │ 2025-03-01  4m  │                            │
    │  └─────────────────┘                            │
    └─────────────────────────────────────────────────┘
```

---

## ▸ FEATURES

```
╔═══════════════════════════════════════════════════════════╗
║  FEATURE MATRIX                                           ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  [■] Streaming chat          Real-time token-by-token     ║
║  [■] Rich markdown           Code blocks, headers, lists  ║
║  [■] Model Forge             Build models from GGUF       ║
║  [■] GPU monitoring          NVIDIA + AMD live stats      ║
║  [■] Chat persistence        Auto-save, search, export    ║
║  [■] Offline translation     ES ↔ EN via Argos Translate  ║
║  [■] System prompts          Scientific, Code, Creative   ║
║  [■] Parameter presets       Balanced, Precise, Creative  ║
║  [■] HiDPI support           Auto-scales for 4K displays  ║
║  [■] Keyboard shortcuts      Ctrl+N, Ctrl+1-5, Esc       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

### Neural Interface (Chat)

- **Streaming responses** — tokens appear in real-time as the model thinks
- **Rich markdown rendering** — code blocks with copy buttons, headers, bold, lists
- **Sliding context window** — keeps the last 40 messages for optimal context
- **One-click copy** — copy any message or code block to clipboard
- **Inline translation** — translate assistant responses ES↔EN offline
- **Chat export** — save conversations as Markdown files

### Model Forge

Create custom Ollama models from GGUF files in 4 steps:

```
  STEP 1          STEP 2          STEP 3          STEP 4
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ SELECT   │──▸│ SYSTEM   │──▸│ TUNE     │──▸│ CREATE   │
│ GGUF     │   │ PROMPT   │   │ PARAMS   │   │ MODEL    │
│          │   │          │   │          │   │          │
│ drag+drop│   │ presets: │   │ temp     │   │ progress │
│ or browse│   │ science  │   │ top_p    │   │ bar      │
│          │   │ code     │   │ top_k    │   │ live log │
│ auto-    │   │ creative │   │ ctx_len  │   │          │
│ detect   │   │ general  │   │ gpu_alloc│   │ done!    │
│ splits   │   │ uncensor │   │          │   │          │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
```

- Automatic split-GGUF detection (`model-00001-of-00003.gguf`)
- Quantization level display (Q3_K, Q4_K_M, Q5_K, Q8, FP16...)
- 5 system prompt presets + custom editor
- Parameter presets: Balanced, Creative, Precise, Code

### System Monitor

Real-time hardware diagnostics with 30-second auto-refresh:

```
┌─ CPU ────────────────────────────────────┐
│  AMD Ryzen 9 7950X • 16C/32T             │
├─ MEMORY ─────────────────────────────────┤
│  RAM: 32.0 GB total • 18.2 GB available  │
│  Swap: 8.0 GB total • 8.0 GB free        │
├─ GPU ────────────────────────────────────┤
│  NVIDIA RTX 5060 • 16 GB VRAM            │
│  Driver: 570.86 • CUDA 12.8              │
│  Temp: 42°C • Utilization: 3%            │
├─ DISK ───────────────────────────────────┤
│  /: 500 GB total • 234 GB free (47%)     │
├─ OLLAMA ─────────────────────────────────┤
│  Status: ● Running                       │
│  Models: deepseek-r1:7b, llama3:8b       │
└──────────────────────────────────────────┘
```

---

## ▸ INSTALLATION

### Prerequisites

```
  ┌───────────────────────────────────────────────┐
  │  REQUIRED                                     │
  │  ─────────                                    │
  │  • Python 3.10+         (with tkinter)        │
  │  • Ollama 0.3+          (ollama.ai)           │
  │                                               │
  │  RECOMMENDED                                  │
  │  ───────────                                  │
  │  • 16 GB RAM            (8 GB minimum)        │
  │  • NVIDIA/AMD GPU       (4+ GB VRAM)          │
  │  • Linux / macOS        (primary targets)     │
  └───────────────────────────────────────────────┘
```

### Quick Start

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Clone & install
git clone https://github.com/your-user/DRAGO_MODEL_RUNNER.git
cd DRAGO_MODEL_RUNNER
bash install.sh

# 3. Launch
./run.sh
```

### Manual Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Dependencies

```
customtkinter >= 5.2.0     # Modern Tk GUI framework
Pillow >= 10.0.0           # Image processing
ollama >= 0.3.0            # Ollama Python client
httpx >= 0.25.0            # HTTP client
pydantic >= 2.0.0          # Data validation
python-dotenv >= 1.0.0     # Environment config
pyperclip >= 1.8.0         # Clipboard support
argostranslate >= 1.9.0    # Offline translation engine
```

---

## ▸ USAGE

### Chatting

1. Select a model from the sidebar dropdown
2. Type in the input box
3. Press **Enter** to send (Shift+Enter for newline)
4. Watch the streaming response in real-time
5. Press **Escape** to stop generation

### Creating Models from GGUF

1. Download a GGUF from [HuggingFace](https://huggingface.co)
2. Open **Model Forge** tab
3. Drag the `.gguf` file or browse to select
4. Choose a system prompt preset and tune parameters
5. Click **Create** — model is ready to chat

### GGUF Size Guide

```
  YOUR VRAM     QUANTIZATION      TYPICAL SIZE
  ─────────     ────────────      ────────────
   4 GB         Q3_K_M             3 – 4 GB
   6 GB         Q4_K_M             4 – 5 GB
   8 GB         Q5_K_M / Q6_K      5 – 7 GB
  12 GB         Q8_0               7 – 9 GB
  16 GB+        FP16              12 – 15 GB
```

### Keyboard Shortcuts

```
  ┌────────────────┬────────────────────────────┐
  │  Ctrl + N      │  New chat                  │
  │  Ctrl + L      │  Clear current chat        │
  │  Ctrl + E      │  Export chat as Markdown    │
  │  Ctrl + 1-5    │  Switch panels             │
  │  Enter         │  Send message              │
  │  Shift + Enter │  New line in input         │
  │  Escape        │  Stop generation           │
  └────────────────┴────────────────────────────┘
```

---

## ▸ CONFIGURATION

Edit `config/default_settings.json`:

```json
{
  "ollama": {
    "host": "http://localhost:11434",
    "timeout": 120,
    "auto_start": false
  },
  "chat": {
    "max_context_messages": 40
  },
  "translation": {
    "enabled": true,
    "source_lang": "es",
    "target_lang": "en"
  },
  "paths": {
    "models_dir": "~/ai-models"
  }
}
```

---

## ▸ ARCHITECTURE

```
  DRAGO_MODEL_RUNNER/
  │
  ├── main.py                          # Entry point
  ├── config/
  │   └── default_settings.json        # App configuration
  │
  ├── src/
  │   ├── core/                        # ── BACKEND ──────────────
  │   │   ├── ollama_client.py         #    Ollama API + streaming
  │   │   ├── gguf_manager.py          #    GGUF discovery + splits
  │   │   ├── chat_storage.py          #    Chat persistence (JSON)
  │   │   ├── model_config.py          #    Parameters + presets
  │   │   └── translation_service.py   #    Offline ES↔EN
  │   │
  │   ├── ui/                          # ── FRONTEND ─────────────
  │   │   ├── main_window.py           #    Window + sidebar + nav
  │   │   ├── chat_panel.py            #    Chat + rich markdown
  │   │   ├── model_manager.py         #    Model Forge wizard
  │   │   ├── system_panel.py          #    Hardware monitoring
  │   │   ├── settings_panel.py        #    Config editor
  │   │   ├── help_panel.py            #    Docs + FAQ
  │   │   ├── theme.py                 #    Matrix color palette
  │   │   └── widgets.py               #    Custom CTk components
  │   │
  │   └── utils/
  │       ├── helpers.py               #    Utility functions
  │       └── logger.py                #    Logging setup
  │
  ├── requirements.txt
  ├── install.sh                       # Guided installer
  └── run.sh                           # Launch script
```

### Data Flow

```
  USER INPUT
      │
      ▼
  ┌─────────┐     ┌──────────────┐     ┌─────────┐
  │  Chat   │────▸│ OllamaClient │────▸│ Ollama  │
  │  Panel  │◂────│  (streaming) │◂────│ Server  │
  └─────────┘     └──────────────┘     └─────────┘
      │                                     │
      ▼                                     ▼
  ┌─────────┐                         ┌─────────┐
  │  Chat   │                         │  Local  │
  │ Storage │                         │  Model  │
  │ (JSON)  │                         │ (GGUF)  │
  └─────────┘                         └─────────┘
```

---

## ▸ FILE LOCATIONS

```
  ~/.drago-model-runner/chats/            Chat history (JSON)
  ~/.local/share/drago-model-runner/      Window state
  ~/.ollama/models/                       Ollama model store
  ~/ai-models/                            GGUF downloads (configurable)
```

---

## ▸ TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| Ollama not found | `curl -fsSL https://ollama.com/install.sh \| sh` |
| GPU not detected | Check `nvidia-smi` or `rocm-smi` |
| Translation slow first run | Argos downloads language packs once, then works offline |
| UI looks small/large | App auto-detects DPI; adjust system display scaling |
| Chat not loading | Check `~/.drago-model-runner/chats/` permissions |

---

## ▸ TECH STACK

```
  ┌─────────────────────────────────────────────────┐
  │                                                 │
  │   FRONTEND         customtkinter + Pillow       │
  │   ─────────        Matrix theme, rich widgets   │
  │                                                 │
  │   BACKEND          Python 3.10+ + httpx         │
  │   ───────          Async streaming, threading   │
  │                                                 │
  │   LLM ENGINE       Ollama                       │
  │   ──────────       Local inference, GGUF, GPU   │
  │                                                 │
  │   TRANSLATION      Argos Translate              │
  │   ───────────      Offline, no API keys         │
  │                                                 │
  │   STORAGE          JSON files                   │
  │   ───────          No database required          │
  │                                                 │
  └─────────────────────────────────────────────────┘
```

---

## ▸ LICENSE

This project is provided as-is for local LLM experimentation.
Do whatever you want with it.

---

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   "Unfortunately, no one can be told what the Matrix is.                     ║
║    You have to see it for yourself."                                         ║
║                                                                              ║
║                                              — Morpheus                      ║
║                                                                              ║
║  ██████████████████████████████████████████████████████████████████████████  ║
║  █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    █  ║
║  █░░▀█▀░█░█░█▀▀░░░█▀▄░█▀▄░█▀█░█▀▀░█▀█░░░█░█▀▀░░░█▀█░█░░░▀█▀░█░█░█▀▀░      █  ║
║  █░░░█░░█▀█░█▀▀░░░█░█░█▀▄░█▀█░█░█░█░█░░░█░▀▀█░░░█▀█░█░░░░█░░█ █░█▀▀░      █  ║
║  █░░░▀░░▀░▀░▀▀▀░░░▀▀░░▀░▀░▀░▀░▀▀▀░▀▀▀░░░▀░▀▀▀░░░▀░▀░▀▀▀░▀▀▀░░▀░░▀▀▀░      █  ║
║  ██████████████████████████████████████████████████████████████████████████  ║
║                                                                              ║
║                          DRAGO MODEL RUNNER v1.0                             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```
