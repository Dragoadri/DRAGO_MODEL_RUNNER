# Translation Layer + Icon Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add auto-translation (ES<->EN via Argos Translate) to the chat flow and fix the dock icon on Ubuntu.

**Architecture:** A `TranslationService` singleton wraps Argos Translate, initialized at app startup. The chat panel gets a toggle switch for auto-translating input, and each assistant message gets a "TRADUCIR" button. The icon fix sets WM_CLASS to match the .desktop file.

**Tech Stack:** Python 3, CustomTkinter, Argos Translate (argostranslate), Pillow (already present)

---

### Task 1: Add argostranslate dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add the dependency**

In `requirements.txt`, add after the Utilities section:

```
# Translation (local, offline)
argostranslate>=1.9.0
```

**Step 2: Install it**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && source .venv/bin/activate && pip install argostranslate>=1.9.0`

Expected: Successfully installed argostranslate and its dependencies.

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add argostranslate dependency for local translation"
```

---

### Task 2: Create TranslationService

**Files:**
- Create: `src/core/translation_service.py`
- Modify: `src/core/__init__.py`

**Step 1: Create the translation service module**

Create `src/core/translation_service.py` with this content:

```python
"""Local translation service using Argos Translate"""
import threading
from typing import Optional, Callable


class TranslationService:
    """Wraps Argos Translate for offline ES<->EN translation.

    Language packs are downloaded on first use (~100MB per pair).
    All public methods are thread-safe.
    """

    _instance: Optional["TranslationService"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._ready = False
        self._initializing = False
        self._installed_pairs: set[tuple[str, str]] = set()

    @classmethod
    def get_instance(cls) -> "TranslationService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(
        self,
        source_lang: str = "es",
        target_lang: str = "en",
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[bool], None]] = None,
    ):
        """Initialize in background thread: download language packs if needed.

        Args:
            source_lang: User's language code (e.g. "es")
            target_lang: Model's language code (e.g. "en")
            on_progress: Called with status messages during setup
            on_complete: Called with True on success, False on failure
        """
        if self._initializing:
            return

        self._initializing = True

        def _setup():
            try:
                if on_progress:
                    on_progress("Loading translation engine...")

                import argostranslate.package
                import argostranslate.translate

                # Update package index
                if on_progress:
                    on_progress("Checking language packs...")
                argostranslate.package.update_package_index()

                # Install both directions: source->target and target->source
                for from_code, to_code in [(source_lang, target_lang), (target_lang, source_lang)]:
                    if (from_code, to_code) in self._installed_pairs:
                        continue

                    installed = argostranslate.translate.get_installed_languages()
                    installed_codes = [lang.code for lang in installed]

                    if from_code in installed_codes and to_code in installed_codes:
                        # Check if the specific translation is available
                        from_lang = next(l for l in installed if l.code == from_code)
                        translation = from_lang.get_translation(
                            next(l for l in installed if l.code == to_code)
                        )
                        if translation:
                            self._installed_pairs.add((from_code, to_code))
                            continue

                    # Need to download
                    if on_progress:
                        on_progress(f"Downloading {from_code}->{to_code} pack...")

                    available = argostranslate.package.get_available_packages()
                    pkg = next(
                        (p for p in available if p.from_code == from_code and p.to_code == to_code),
                        None,
                    )
                    if pkg:
                        pkg.install()
                        self._installed_pairs.add((from_code, to_code))
                    else:
                        if on_progress:
                            on_progress(f"Warning: no pack for {from_code}->{to_code}")

                self._ready = True
                self._initializing = False
                if on_progress:
                    on_progress("Translation ready")
                if on_complete:
                    on_complete(True)

            except Exception as e:
                self._ready = False
                self._initializing = False
                if on_progress:
                    on_progress(f"Translation error: {e}")
                if on_complete:
                    on_complete(False)

        threading.Thread(target=_setup, daemon=True).start()

    def translate(self, text: str, from_lang: str, to_lang: str) -> str:
        """Translate text. Returns original text if translation fails or not ready."""
        if not self._ready or not text.strip():
            return text

        try:
            import argostranslate.translate
            return argostranslate.translate.translate(text, from_lang, to_lang)
        except Exception:
            return text

    def is_ready(self) -> bool:
        return self._ready
```

**Step 2: Export from core __init__**

In `src/core/__init__.py`, add the import. The file should become:

```python
"""Core business logic for DRAGO Model Runner"""
from .ollama_client import OllamaClient
from .model_config import ModelConfig, ModelParameters
from .gguf_manager import GGUFManager
from .translation_service import TranslationService

__all__ = ["OllamaClient", "ModelConfig", "ModelParameters", "GGUFManager", "TranslationService"]
```

**Step 3: Verify import works**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && source .venv/bin/activate && python -c "from src.core import TranslationService; print('OK:', TranslationService)"`

Expected: `OK: <class 'src.core.translation_service.TranslationService'>`

**Step 4: Commit**

```bash
git add src/core/translation_service.py src/core/__init__.py
git commit -m "feat: add TranslationService with Argos Translate backend"
```

---

### Task 3: Add translation config to default_settings.json

**Files:**
- Modify: `config/default_settings.json`

**Step 1: Add translation section**

Add a `"translation"` key to `config/default_settings.json`. The full file should be:

```json
{
    "ollama": {
        "host": "http://localhost:11434",
        "timeout": 120
    },
    "model_defaults": {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "repeat_penalty": 1.1,
        "num_ctx": 4096,
        "num_gpu": -1
    },
    "ui": {
        "theme": "dark",
        "font_size": 14,
        "window_width": 1200,
        "window_height": 800
    },
    "paths": {
        "models_dir": "~/ai-models",
        "gguf_extensions": [".gguf", ".bin"]
    },
    "translation": {
        "enabled": true,
        "source_lang": "es",
        "target_lang": "en",
        "auto_translate_input": true
    }
}
```

**Step 2: Commit**

```bash
git add config/default_settings.json
git commit -m "feat: add translation config defaults"
```

---

### Task 4: Wire TranslationService into MainWindow startup

**Files:**
- Modify: `src/ui/main_window.py`

**Step 1: Import TranslationService**

At the top of `main_window.py`, add to the existing core import line (line 19):

Change:
```python
from ..core import OllamaClient, GGUFManager
```
To:
```python
from ..core import OllamaClient, GGUFManager, TranslationService
```

**Step 2: Initialize TranslationService in `_init_core`**

In `MainWindow._init_core()` (around line 377), after the `self.gguf_manager` line, add translation service initialization. Read translation config from settings and store it:

```python
        # Translation
        translation_config = settings.get("translation", {})
        self.translation_enabled = translation_config.get("enabled", True)
        self.translation_source = translation_config.get("source_lang", "es")
        self.translation_target = translation_config.get("target_lang", "en")
        self.auto_translate_input = translation_config.get("auto_translate_input", True)
        self.translator = TranslationService.get_instance()
```

**Step 3: Start translation initialization in `_startup_sequence`**

In `MainWindow._startup_sequence()`, inside the `startup()` inner function (around line 452), add translation init alongside the Ollama check. After `is_running = self.ollama.is_running()`, add:

```python
            # Initialize translation
            if self.translation_enabled:
                def on_trans_progress(msg):
                    self.after(0, lambda: self.sidebar.set_status("loading", msg))

                def on_trans_complete(success):
                    # Pass translator reference to chat panel
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
```

**Step 4: Update `_on_settings_changed` to handle translation config**

In `MainWindow._on_settings_changed()` (around line 619), before `self._startup_sequence()`, add:

```python
        translation_config = settings.get("translation", {})
        self.translation_enabled = translation_config.get("enabled", True)
        self.translation_source = translation_config.get("source_lang", "es")
        self.translation_target = translation_config.get("target_lang", "en")
        self.auto_translate_input = translation_config.get("auto_translate_input", True)
```

**Step 5: Update `_on_chat_send` to translate input**

In `MainWindow._on_chat_send()` (around line 638), after `self.current_model = model`, add translation logic before building the messages. The key change: translate the user message before sending to the API, but keep the original in the chat UI.

After the line `self.chat_panel.start_assistant_message()` and before `messages = self.chat_panel.get_messages()`, add:

```python
        # Translate input messages if auto-translate is enabled
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
```

And remove the existing `messages = self.chat_panel.get_messages()` line that comes after (to avoid duplicate).

**Step 6: Verify app launches without errors**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && source .venv/bin/activate && python main.py`

Expected: App opens normally. Translation initializes in background (check terminal for progress messages).

**Step 7: Commit**

```bash
git add src/ui/main_window.py
git commit -m "feat: wire TranslationService into MainWindow startup and chat flow"
```

---

### Task 5: Add translation toggle and translate button to ChatPanel

**Files:**
- Modify: `src/ui/chat_panel.py`

**Step 1: Add translator state to ChatPanel.__init__**

In `ChatPanel.__init__()`, after `self._system_prompt` (line 238), add:

```python
        self._translator = None
        self._translate_source = "es"
        self._translate_target = "en"
        self._auto_translate = False
```

**Step 2: Add `set_translator` method**

After the `set_system_prompt` method (around line 571), add:

```python
    def set_translator(self, translator, source_lang: str, target_lang: str, auto_translate: bool):
        """Set the translation service and update toggle state"""
        self._translator = translator
        self._translate_source = source_lang
        self._translate_target = target_lang
        self._auto_translate = auto_translate
        if hasattr(self, 'translate_switch'):
            if auto_translate:
                self.translate_switch.select()
            else:
                self.translate_switch.deselect()
            self._update_translate_label()

    def translate_toggle_on(self) -> bool:
        """Check if the translate toggle is active"""
        if hasattr(self, 'translate_switch'):
            return self.translate_switch.get() == 1
        return False
```

**Step 3: Add translation toggle to the input area UI**

In `ChatPanel._setup_ui()`, after the `self.clear_button.pack(...)` line (around line 343) and before the status bar section, add a translation toggle row:

```python
        # Translation toggle row
        self.translate_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.translate_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=15, pady=(0, 8))

        self.translate_label = ctk.CTkLabel(
            self.translate_frame,
            text=f" {DECORATIONS['block_med']} AUTO-TRANSLATE: ES {DECORATIONS['arrow_r']} EN",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"]
        )
        self.translate_label.pack(side="left", padx=(0, 10))

        self.translate_switch = ctk.CTkSwitch(
            self.translate_frame,
            text="",
            width=40,
            height=20,
            fg_color=COLORS["bg_tertiary"],
            progress_color=COLORS["matrix_green_dark"],
            button_color=COLORS["matrix_green"],
            button_hover_color=COLORS["matrix_green_bright"],
            command=self._update_translate_label
        )
        self.translate_switch.pack(side="left")

        self.translate_status = ctk.CTkLabel(
            self.translate_frame,
            text="OFF",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["text_muted"]
        )
        self.translate_status.pack(side="left", padx=(8, 0))
```

**Step 4: Add `_update_translate_label` helper**

After the `translate_toggle_on` method, add:

```python
    def _update_translate_label(self):
        """Update translation toggle label based on state"""
        if self.translate_switch.get() == 1:
            self.translate_status.configure(
                text="ON",
                text_color=COLORS["matrix_green"]
            )
            self.translate_label.configure(text_color=COLORS["matrix_green"])
        else:
            self.translate_status.configure(
                text="OFF",
                text_color=COLORS["text_muted"]
            )
            self.translate_label.configure(text_color=COLORS["text_muted"])
```

**Step 5: Add TRADUCIR button to ChatMessage (assistant only)**

In `ChatMessage.__init__()`, after the `self.copy_btn` grid line (line 115) and before the separator, add a translate button for assistant messages:

```python
        # Translate button (assistant messages only)
        self._translation_frame = None
        self._showing_translation = False
        self._translated_text = None

        if not is_user:
            self.translate_btn = ctk.CTkButton(
                header,
                text="TRADUCIR",
                font=ctk.CTkFont(family="Consolas", size=10),
                width=70,
                height=22,
                fg_color=COLORS["bg_tertiary"],
                hover_color=COLORS["bg_hover"],
                border_color=COLORS["accent_cyan"],
                border_width=1,
                text_color=COLORS["accent_cyan"],
                command=self._toggle_translation
            )
            self.translate_btn.grid(row=0, column=2, sticky="e", padx=(0, 5))
            # Shift copy button to column 3
            self.copy_btn.grid(row=0, column=3, sticky="e")
        else:
            self.translate_btn = None
```

Note: The copy_btn is currently in column 2. For assistant messages, we need translate in column 2, copy in column 3. For user messages, copy stays in column 2 (no change).

**Step 6: Add `_toggle_translation` method to ChatMessage**

After the `finish_content` method (around line 213), add:

```python
    def _toggle_translation(self):
        """Toggle translation display"""
        if self._showing_translation:
            # Show original
            if self._translation_frame:
                self._translation_frame.destroy()
                self._translation_frame = None
            self.translate_btn.configure(text="TRADUCIR")
            self._showing_translation = False
        else:
            # Translate and show
            self.translate_btn.configure(text="...", state="disabled")
            self._do_translate()

    def set_translator(self, translator):
        """Set the translator reference"""
        self._translator = translator

    def _do_translate(self):
        """Perform translation in background thread"""
        import threading

        translator = getattr(self, '_translator', None)
        if not translator or not translator.is_ready():
            self.translate_btn.configure(text="N/A", state="normal")
            self.after(1500, lambda: self.translate_btn.configure(text="TRADUCIR"))
            return

        def work():
            # Detect direction: if content looks English, translate to source lang
            # Default: translate from target (model lang) to source (user lang)
            source = getattr(self, '_translate_target', 'en')
            target = getattr(self, '_translate_source', 'es')
            translated = translator.translate(self.raw_content, source, target)

            def show():
                if not self.winfo_exists():
                    return
                self._translated_text = translated
                self._show_translation(translated)
                self.translate_btn.configure(text="ORIGINAL", state="normal")
                self._showing_translation = True

            self.after(0, show)

        threading.Thread(target=work, daemon=True).start()

    def _show_translation(self, text: str):
        """Display translated text below original"""
        from .theme import COLORS, DECORATIONS

        self._translation_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["accent_cyan"],
            border_width=1,
            corner_radius=4
        )
        self._translation_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 12))

        # Header
        ctk.CTkLabel(
            self._translation_frame,
            text=f" {DECORATIONS['h_line']*3} TRANSLATION {DECORATIONS['h_line']*3}",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["accent_cyan"]
        ).pack(anchor="w", padx=10, pady=(8, 4))

        # Translated text
        from .widgets import MatrixTextbox
        trans_textbox = MatrixTextbox(
            self._translation_frame,
            height=10,
            wrap="word",
            fg_color=COLORS["bg_tertiary"],
            border_width=0,
            text_color=COLORS["accent_cyan"],
            font=ctk.CTkFont(family="Consolas", size=13),
        )
        trans_textbox.pack(fill="x", padx=8, pady=(0, 8))

        try:
            trans_textbox._scrollbar.grid_forget()
        except Exception:
            pass

        display = parse_markdown_simple(text)
        trans_textbox.insert("1.0", display)
        trans_textbox.configure(state="disabled")

        # Auto-resize
        def resize():
            try:
                trans_textbox.configure(state="normal")
                inner = trans_textbox._textbox
                dl = inner.count("1.0", "end", "displaylines")
                if dl:
                    n = dl[0] if isinstance(dl, tuple) else dl
                else:
                    n = int(trans_textbox.index("end-1c").split(".")[0])
                trans_textbox.configure(height=max(30, n * 22 + 10), state="disabled")
            except Exception:
                pass

        self.after(50, resize)
```

**Step 7: Wire translator reference into ChatMessage when creating messages**

In `ChatPanel.add_message()` (around line 488), after creating the widget, pass the translator:

After `widget = ChatMessage(self.messages_frame, role, content)`, add:

```python
        if role == "assistant" and self._translator:
            widget._translator = self._translator
            widget._translate_source = self._translate_source
            widget._translate_target = self._translate_target
```

Also in `ChatPanel.start_assistant_message()` (around line 501), after creating `self.current_assistant_widget`, add the same:

```python
        if self._translator:
            self.current_assistant_widget._translator = self._translator
            self.current_assistant_widget._translate_source = self._translate_source
            self.current_assistant_widget._translate_target = self._translate_target
```

**Step 8: Verify the full translation flow**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && source .venv/bin/activate && python main.py`

Test:
1. Toggle "AUTO-TRANSLATE" to ON
2. Type a message in Spanish
3. Verify the model receives it in English (check terminal logs)
4. Click "TRADUCIR" on the model's response
5. Verify translation appears below the original

**Step 9: Commit**

```bash
git add src/ui/chat_panel.py
git commit -m "feat: add translation toggle and per-message translate button"
```

---

### Task 6: Add translation settings to Settings panel

**Files:**
- Modify: `src/ui/settings_panel.py`

**Step 1: Update `_load_settings` defaults**

In `SettingsPanel._load_settings()` (line 44), add translation to the defaults dict:

After `"paths": {"models_dir": "~/ai-models"}`, add:

```python
            "translation": {
                "enabled": True,
                "source_lang": "es",
                "target_lang": "en",
                "auto_translate_input": True
            }
```

**Step 2: Add translation section to UI**

In `SettingsPanel._setup_ui()`, after the PATHS section block (around line 167, after the browse button grid) and before the ABOUT section, add:

```python
        # === TRANSLATION SECTION ===
        trans_section = self._create_section(content, "TRANSLATION")
        trans_section.pack(fill="x", pady=(0, 15))

        trans_grid = MatrixFrame(trans_section)
        trans_grid.pack(fill="x", padx=15, pady=15)
        trans_grid.grid_columnconfigure(1, weight=1)

        # Enable translation
        MatrixLabel(trans_grid, text=f"{DECORATIONS['arrow_r']} Enabled:", size="sm").grid(
            row=0, column=0, padx=15, pady=10, sticky="w"
        )
        trans_config = self.settings.get("translation", {})
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

        # Source language
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

        # Target language (model language)
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
```

**Step 3: Update `_apply_settings` to save translation config**

In `SettingsPanel._apply_settings()` (around line 292), before `self._save_settings()`, add:

```python
        self.settings.setdefault("translation", {})
        self.settings["translation"]["enabled"] = self.trans_enabled_switch.get() == 1
        self.settings["translation"]["source_lang"] = self.source_lang_combo.get()
        self.settings["translation"]["target_lang"] = self.target_lang_combo.get()
        self.settings["translation"]["auto_translate_input"] = self.auto_translate_switch.get() == 1
```

**Step 4: Verify settings panel**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && source .venv/bin/activate && python main.py`

Test:
1. Go to CONFIG panel
2. See TRANSLATION section with 4 fields
3. Change settings, click SAVE
4. Verify `config/default_settings.json` updated

**Step 5: Commit**

```bash
git add src/ui/settings_panel.py
git commit -m "feat: add translation configuration to settings panel"
```

---

### Task 7: Fix dock icon (WM_CLASS + iconphoto)

**Files:**
- Modify: `src/ui/main_window.py`

**Step 1: Add Pillow import**

At the top of `main_window.py`, add:

```python
from PIL import Image, ImageTk
```

**Step 2: Set WM_CLASS and icon in MainWindow.__init__**

In `MainWindow.__init__()`, after the `super().__init__()` call (line 280) and before `self.config_path = config_path`, add:

```python
        # Set WM_CLASS to match .desktop StartupWMClass for dock icon
        self.tk.call('tk', 'appname', 'drago-model-runner')

        # Set window icon
        icon_path = Path(__file__).parent.parent.parent / "icon.png"
        if icon_path.exists():
            icon_image = Image.open(icon_path)
            self._icon_photo = ImageTk.PhotoImage(icon_image)
            self.iconphoto(True, self._icon_photo)
```

Note: `self._icon_photo` is stored as an instance attribute to prevent garbage collection.

**Step 3: Verify the icon fix**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && source .venv/bin/activate && python main.py`

Test:
1. App opens — check the window titlebar icon (should be icon.png, not default Tk icon)
2. Look at the Ubuntu dock (left bar) — should show icon.png instead of gear

**Step 4: Commit**

```bash
git add src/ui/main_window.py
git commit -m "fix: set WM_CLASS and iconphoto for correct dock icon on Ubuntu"
```

---

### Task 8: Final integration test

**Step 1: Full restart test**

Close the app completely, then:

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && source .venv/bin/activate && python main.py`

**Step 2: Verify checklist**

- [ ] App launches without errors
- [ ] Dock icon shows correctly (not gear)
- [ ] Window titlebar shows correct icon
- [ ] Translation toggle visible in chat panel input area
- [ ] Toggle label updates when switched ON/OFF
- [ ] With toggle ON: typing Spanish → model receives English
- [ ] Model response has "TRADUCIR" button
- [ ] Clicking "TRADUCIR" shows Spanish translation below
- [ ] Clicking "ORIGINAL" hides translation
- [ ] Settings panel has TRANSLATION section
- [ ] Changing settings and saving works
- [ ] "COPY" button still works on all messages

**Step 3: Commit any remaining fixes if needed**
