# Translation Layer + Icon Fix Design

## Overview

Two features for DRAGO Model Runner:
1. **Translation layer** — Auto-translate Spanish prompts to English before sending to the LLM, with per-message translate button for responses
2. **Dock icon fix** — Fix WM_CLASS mismatch so the correct icon shows in the Ubuntu dock

## Feature 1: Translation Layer

### Library

**Argos Translate** — 100% local, offline, MIT license, ~100MB per language pair.

Dependency: `argostranslate>=1.9.0`

### Architecture

New module: `src/core/translation_service.py`

```
TranslationService (singleton)
├── __init__(source_lang, target_lang)
├── ensure_packages_installed()  # Downloads language packs if needed
├── translate(text, from_lang, to_lang) -> str
├── is_ready() -> bool
└── get_available_languages() -> list
```

- Initialized during app startup (`_startup_sequence`)
- Language pack download happens in background thread with progress indication
- Translation calls are fast (~100ms) and run in threads to avoid UI blocking

### Input Translation Flow

```
User types in Spanish
  → Toggle "ES→EN" active?
    → YES: TranslationService.translate(text, "es", "en")
           → English prompt sent to LLM
    → NO:  Original text sent as-is
```

- Toggle is a CTkSwitch in the input area, Matrix-styled
- Translation happens transparently — user doesn't see the intermediate English text
- The original Spanish text is shown in the chat as the user message

### Response Translation Flow

```
LLM responds
  → Original response displayed
  → "TRADUCIR" button in message header (assistant messages only)
    → Click: translate in thread → show translation below with separator
    → Button changes to "ORIGINAL" to toggle back
```

### UI Changes

**Input area** — Add translation toggle:
- CTkSwitch next to the input field, labeled with Matrix styling
- State persisted in config

**Chat message bubbles (assistant only)** — Add "TRADUCIR" button:
- Placed in the header row next to existing "COPY" button
- On click: translates, shows result below original with visual separator
- Toggles between "TRADUCIR" and "ORIGINAL"

### Configuration

In `config/default_settings.json`:
```json
{
  "translation": {
    "enabled": true,
    "source_lang": "es",
    "target_lang": "en",
    "auto_translate_input": true
  }
}
```

In Settings panel: new "Translation" section with:
- Enable/disable toggle
- Source language selector
- Target language selector (default: en)

## Feature 2: Dock Icon Fix

### Problem

`.desktop` file has `StartupWMClass=drago-model-runner` but CustomTkinter sets `WM_CLASS="Tk"` by default. GNOME Shell can't match the running window to the `.desktop` entry.

### Fix

In `MainWindow.__init__`, after `super().__init__()`:

1. Set WM_CLASS: `self.tk.call('tk', 'appname', 'drago-model-runner')`
2. Set window icon: `self.iconphoto(True, photo)` using `icon.png`

## Files Modified

- `main_window.py` — WM_CLASS fix, iconphoto, translation toggle wiring
- `chat_panel.py` — Translation toggle UI, translate button per message
- `settings_panel.py` — Translation configuration section
- `config/default_settings.json` — Translation settings
- `requirements.txt` — Add argostranslate

## Files Created

- `src/core/translation_service.py` — Translation service wrapper
