# UI Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Comprehensive UI polish, consistency fixes, and sidebar redesign while maintaining the Matrix aesthetic.

**Architecture:** Edit existing UI files only — no new files. Theme tokens expanded first, then widgets refined, then each panel updated top-down. Sidebar gets a structural redesign with horizontal nav tabs.

**Tech Stack:** Python, customtkinter, tkinter (no new deps)

---

### Task 1: Expand theme tokens

**Files:**
- Modify: `src/ui/theme.py`

**Step 1: Add RADIUS, NAV_ICONS, and focus color tokens**

Add after the `SPACING` dict and update `COLORS`:

```python
# In COLORS dict, add these new entries:
    # Focus/Active states
    "bg_focus": "#0a1f0a",
    "border_focus": "#00ff41",
    "bg_active_nav": "#0d2b0d",

# After SPACING dict, add:

RADIUS = {
    "sm": 4,
    "md": 6,
    "lg": 8,
    "xl": 12,
}

NAV_ICONS = {
    "chat": "\u2328",      # keyboard - neural chat
    "models": "\u2699",     # gear - model forge
    "system": "\u2630",     # trigram - system
    "help": "\u2753",       # question mark - help
    "settings": "\u2318",   # place of interest - config
}
```

**Step 2: Verify no import errors**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && python -c "from src.ui.theme import COLORS, RADIUS, NAV_ICONS; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add src/ui/theme.py
git commit -m "feat(ui): expand theme tokens with RADIUS, NAV_ICONS, focus colors"
```

---

### Task 2: Refine core widgets

**Files:**
- Modify: `src/ui/widgets.py`

**Step 1: Improve MatrixScrollableFrame scrollbar styling**

In `MatrixScrollableFrame.__init__`, add thinner scrollbar defaults:
```python
kwargs.setdefault("scrollbar_button_color", COLORS["matrix_green_dark"])
kwargs.setdefault("scrollbar_button_hover_color", COLORS["matrix_green_dim"])
# Existing ^^, keep them. No structural changes needed.
```

**Step 2: Improve TerminalHeader with subtle bottom border highlight**

In `TerminalHeader.__init__`, after the title_frame grid, add a subtle 1px accent line at bottom:

```python
# After the existing title_frame grid line, add:
accent = ctk.CTkFrame(self, fg_color=COLORS["matrix_green_dark"], height=1)
accent.grid(row=1, column=0, columnspan=3, sticky="ew")
```

**Step 3: Add MatrixIconButton widget class for nav tabs**

Add a new small widget class after MatrixButton:

```python
class MatrixIconButton(ctk.CTkButton):
    """Compact icon button for navigation tabs"""

    def __init__(self, parent, icon: str = "", label: str = "", active: bool = False, **kwargs):
        fg = COLORS["bg_active_nav"] if active else COLORS["bg_secondary"]
        border = COLORS["matrix_green"] if active else COLORS["border_green"]
        text_c = COLORS["matrix_green_bright"] if active else COLORS["matrix_green_dim"]

        kwargs.setdefault("width", 50)
        kwargs.setdefault("height", 44)
        kwargs.setdefault("corner_radius", RADIUS["md"])
        kwargs.setdefault("border_width", 1)

        display = f"{icon}\n{label}" if label else icon

        super().__init__(
            parent,
            text=display,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=fg,
            hover_color=COLORS["bg_hover"],
            border_color=border,
            text_color=text_c,
            **kwargs
        )
        self._is_active = active

    def set_active(self, active: bool):
        self._is_active = active
        if active:
            self.configure(
                fg_color=COLORS["bg_active_nav"],
                border_color=COLORS["matrix_green"],
                text_color=COLORS["matrix_green_bright"]
            )
        else:
            self.configure(
                fg_color=COLORS["bg_secondary"],
                border_color=COLORS["border_green"],
                text_color=COLORS["matrix_green_dim"]
            )
```

Update the import at top of widgets.py to include `RADIUS`:
```python
from .theme import COLORS, FONTS, DECORATIONS, BUTTON_STYLE, BUTTON_PRIMARY_STYLE, ENTRY_STYLE, RADIUS
```

**Step 4: Verify imports**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && python -c "from src.ui.widgets import MatrixIconButton; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add src/ui/widgets.py
git commit -m "feat(ui): add MatrixIconButton, improve TerminalHeader accent"
```

---

### Task 3: Redesign Sidebar layout

**Files:**
- Modify: `src/ui/main_window.py`

This is the biggest task. The Sidebar class gets restructured:

**New layout:**
```
┌────────────────────────┐
│  DR  DRAGO RUNNER  ●   │  <- compact logo + status dot
├────────────────────────┤
│  MODEL: [combo____▼]   │  <- inline model selector
│  [▒ Refresh]           │
├────────────────────────┤
│ [⌨][⚙][☰][❓][⌘]     │  <- horizontal nav tabs
├────────────────────────┤
│ ═══ CHATS ═══  [❯ NEW] │
│ [Search chats...     ] │
│ ┌────────────────────┐ │
│ │ Chat title...      │ │  <- scrollable list fills rest
│ │ Chat title...      │ │
│ └────────────────────┘ │
└────────────────────────┘
```

**Step 1: Update Sidebar imports**

At top of `main_window.py`, update the widgets import to include `MatrixIconButton`:
```python
from .widgets import (
    MatrixFrame, MatrixButton, MatrixLabel, MatrixComboBox,
    StatusIndicator, GlowingTitle, MatrixScrollableFrame, MatrixEntry,
    MatrixIconButton
)
```

Also import NAV_ICONS and RADIUS from theme:
```python
from .theme import COLORS, DECORATIONS, ASCII_LOGO, NAV_ICONS, RADIUS
```

**Step 2: Rewrite Sidebar._setup_ui method**

Replace the entire `_setup_ui` method with the new layout. Key changes:

1. **Compact header** — logo text reduced to one-line with status dot inline
2. **Model selector** — kept but with inline "MODELO" label
3. **Horizontal nav row** — 5 MatrixIconButtons in a horizontal frame
4. **Chat list** — takes remaining space, with search ABOVE the list
5. **Remove** version footer (moves to settings)

```python
def _setup_ui(self):
    """Setup sidebar UI"""
    # Row weights: 0=logo, 1=model, 2=nav, 3=sep, 4=chats(expand), no version row
    self.grid_rowconfigure(4, weight=1)
    self.grid_columnconfigure(0, weight=1)

    # ── Compact Logo + Status ──
    logo_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
    logo_frame.grid(row=0, column=0, sticky="ew")
    logo_frame.grid_columnconfigure(0, weight=1)

    logo_row = ctk.CTkFrame(logo_frame, fg_color="transparent")
    logo_row.pack(fill="x", padx=12, pady=10)
    logo_row.grid_columnconfigure(1, weight=1)

    # Small ASCII logo
    logo_text = f"{DECORATIONS['block_dark']}{DECORATIONS['block']}{DECORATIONS['block_dark']}"
    ctk.CTkLabel(
        logo_row,
        text=logo_text,
        font=ctk.CTkFont(family="Consolas", size=16),
        text_color=COLORS["matrix_green"],
    ).grid(row=0, column=0, padx=(0, 8))

    ctk.CTkLabel(
        logo_row,
        text="DRAGO RUNNER",
        font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
        text_color=COLORS["matrix_green_bright"],
        anchor="w",
    ).grid(row=0, column=1, sticky="w")

    # Inline status dot
    self.status_indicator = StatusIndicator(logo_row)
    self.status_indicator.grid(row=0, column=2, padx=(4, 0))

    # GPU info (small, under logo)
    self.gpu_label = ctk.CTkLabel(
        logo_frame,
        text=f"  {DECORATIONS['arrow_r']} GPU: Detecting...",
        font=ctk.CTkFont(family="Consolas", size=10),
        text_color=COLORS["text_muted"],
        anchor="w",
    )
    self.gpu_label.pack(fill="x", padx=12, pady=(0, 6))

    # ── Model Selector ──
    model_frame = ctk.CTkFrame(self, fg_color="transparent")
    model_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(8, 4))
    model_frame.grid_columnconfigure(0, weight=1)

    MatrixLabel(
        model_frame,
        text=f"{DECORATIONS['block']} MODELO",
        size="xs",
        bright=True,
    ).grid(row=0, column=0, sticky="w", pady=(0, 4))

    self.model_combo = MatrixComboBox(model_frame, values=["Loading..."])
    self.model_combo.grid(row=1, column=0, sticky="ew")

    refresh_btn = MatrixButton(
        model_frame,
        text=f"{DECORATIONS['block_med']} Refresh",
        height=26,
        command=lambda: self.on_nav("refresh_models"),
    )
    refresh_btn.grid(row=2, column=0, sticky="ew", pady=(4, 0))

    # ── Horizontal Nav Tabs ──
    nav_frame = ctk.CTkFrame(
        self,
        fg_color=COLORS["bg_dark"],
        corner_radius=0,
    )
    nav_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=(8, 0))

    nav_inner = ctk.CTkFrame(nav_frame, fg_color="transparent")
    nav_inner.pack(fill="x", padx=6, pady=6)
    # 5 columns, equal weight
    for i in range(5):
        nav_inner.grid_columnconfigure(i, weight=1)

    self.nav_buttons = {}
    nav_items = [
        ("chat", NAV_ICONS["chat"], "CHAT"),
        ("models", NAV_ICONS["models"], "FORGE"),
        ("system", NAV_ICONS["system"], "SYS"),
        ("help", NAV_ICONS["help"], "HELP"),
        ("settings", NAV_ICONS["settings"], "CFG"),
    ]

    for idx, (name, icon, label) in enumerate(nav_items):
        is_active = (name == "chat")
        btn = MatrixIconButton(
            nav_inner,
            icon=icon,
            label=label,
            active=is_active,
            command=lambda n=name: self._on_nav_click(n),
        )
        btn.grid(row=0, column=idx, padx=2, sticky="ew")
        self.nav_buttons[name] = btn

    # ── Separator ──
    sep = ctk.CTkFrame(self, fg_color=COLORS["border_green"], height=1)
    sep.grid(row=3, column=0, sticky="ew", padx=10, pady=6)

    # ── Chat List Section (fills remaining space) ──
    chats_frame = ctk.CTkFrame(self, fg_color="transparent")
    chats_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))
    chats_frame.grid_rowconfigure(2, weight=1)
    chats_frame.grid_columnconfigure(0, weight=1)

    # Header row: title + NEW button
    chats_header = ctk.CTkFrame(chats_frame, fg_color="transparent")
    chats_header.grid(row=0, column=0, sticky="ew")
    chats_header.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        chats_header,
        text=f" {DECORATIONS['h_line']*3} CHATS {DECORATIONS['h_line']*3}",
        font=ctk.CTkFont(family="Consolas", size=10),
        text_color=COLORS["text_muted"],
    ).grid(row=0, column=0, sticky="w")

    new_chat_btn = MatrixButton(
        chats_header,
        text=f"{DECORATIONS['prompt']} NEW",
        height=24,
        width=60,
        command=lambda: self.on_nav("new_chat"),
    )
    new_chat_btn.grid(row=0, column=1, sticky="e")

    # Search field (above list now)
    self.chat_search = MatrixEntry(
        chats_frame,
        placeholder_text="Search chats...",
        height=28,
    )
    self.chat_search.grid(row=1, column=0, sticky="ew", pady=(6, 4))
    self.chat_search.bind("<KeyRelease>", lambda e: self.on_nav("search_chats"))

    # Scrollable chat list
    self.chat_list_frame = MatrixScrollableFrame(
        chats_frame,
        fg_color=COLORS["bg_dark"],
        border_width=1,
        border_color=COLORS["border_green"],
    )
    self.chat_list_frame.grid(row=2, column=0, sticky="nsew")
    self.chat_list_frame.grid_columnconfigure(0, weight=1)
```

**Step 3: Update `_on_nav_click` to use new MatrixIconButton API**

```python
def _on_nav_click(self, panel_name: str):
    """Handle navigation click"""
    self.current_panel = panel_name

    for name, btn in self.nav_buttons.items():
        btn.set_active(name == panel_name)

    self.on_nav(panel_name)
```

**Step 4: Verify the app launches**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && timeout 5 python -c "from src.ui.main_window import Sidebar; print('OK')" 2>&1 || true`
Expected: `OK` (or timeout, which is fine since tk mainloop)

**Step 5: Commit**

```bash
git add src/ui/main_window.py
git commit -m "feat(ui): redesign sidebar with horizontal nav tabs and compact layout"
```

---

### Task 4: Polish chat panel

**Files:**
- Modify: `src/ui/chat_panel.py`

**Step 1: Improve ChatMessage bubble styling**

In `ChatMessage.__init__`, increase `corner_radius` from 4 to `RADIUS["lg"]` (8), increase internal padding. Add import of RADIUS at top:

```python
from .theme import COLORS, DECORATIONS, RADIUS
```

Change the frame init to use `corner_radius=RADIUS["lg"]`.

Make the separator more subtle: change `height=1` to a frame using `COLORS["border_dim"]` instead of the full `border_color`.

Increase content padding from `padx=8` to `padx=12`.

**Step 2: Improve input area with focus glow**

In `ChatPanel._setup_ui`, after creating `self.input_text`, bind focus events:

```python
self.input_text.bind("<FocusIn>", lambda e: self.input_text.configure(
    border_color=COLORS["matrix_green"]
))
self.input_text.bind("<FocusOut>", lambda e: self.input_text.configure(
    border_color=COLORS["matrix_green_dim"]
))
```

**Step 3: Improve status bar with top border**

In the status bar creation, add a separator frame above it:

```python
# Status bar separator
status_sep = ctk.CTkFrame(self, fg_color=COLORS["border_green"], height=1)
status_sep.grid(row=2, column=0, sticky="ew")  # between input and status

# Shift status_bar to row 4 (input=row 2 -> row 3, status_sep=row 3 -> before status)
```

Actually simpler: just add a top border to the status_bar by wrapping it or adding border_width.

**Step 4: Improve welcome screen**

Replace the welcome text with a better visual hierarchy:

```python
welcome_text = f"""
  {DECORATIONS['block_dark']*3} {DECORATIONS['block']*3} {DECORATIONS['block_dark']*3}

  DRAGO MODEL RUNNER v1.0
  {DECORATIONS['h_line'] * 32}

  Sistema de inferencia local.

  {DECORATIONS['prompt']} ENTER        Enviar mensaje
  {DECORATIONS['prompt']} SHIFT+ENTER  Nueva linea
  {DECORATIONS['prompt']} CLEAR        Reiniciar sesion
  {DECORATIONS['prompt']} COPY         Copiar mensajes

  {DECORATIONS['h_line'] * 32}
  Selecciona un modelo para comenzar.
"""
```

**Step 5: Verify import works**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && python -c "from src.ui.chat_panel import ChatPanel; print('OK')"`

**Step 6: Commit**

```bash
git add src/ui/chat_panel.py
git commit -m "feat(ui): polish chat bubbles, input focus glow, welcome screen"
```

---

### Task 5: Polish settings panel + move version info

**Files:**
- Modify: `src/ui/settings_panel.py`

**Step 1: Improve section header consistency**

Update `_create_section` to use `RADIUS["lg"]` for corner_radius and consistent padding.

**Step 2: Move version info here**

The ABOUT section already exists with version info - just ensure it's complete. Add the version line that was in the sidebar footer.

**Step 3: Commit**

```bash
git add src/ui/settings_panel.py
git commit -m "feat(ui): polish settings panel consistency"
```

---

### Task 6: Polish help panel

**Files:**
- Modify: `src/ui/help_panel.py`

**Step 1: Improve section spacing**

Add more padding between sections (`pady=(0, 20)` instead of `(0, 15)`).
Use consistent `_create_section` pattern.

**Step 2: Commit**

```bash
git add src/ui/help_panel.py
git commit -m "feat(ui): improve help panel spacing and readability"
```

---

### Task 7: Polish system panel and model manager

**Files:**
- Modify: `src/ui/system_panel.py`
- Modify: `src/ui/model_manager.py`

**Step 1: System panel - consistent section headers**

Ensure SpecCard uses `RADIUS["lg"]` for corner_radius.

**Step 2: Model manager - improve step section headers**

Use consistent header pattern.

**Step 3: Commit**

```bash
git add src/ui/system_panel.py src/ui/model_manager.py
git commit -m "feat(ui): polish system panel and model manager consistency"
```

---

### Task 8: Final visual verification

**Step 1: Launch the app and visually verify all panels**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && python -m src.main`

Check:
- [ ] Sidebar: compact logo, horizontal nav tabs work, chat list fills space
- [ ] Chat: improved bubbles, input focus glow, welcome screen
- [ ] All panels: consistent section headers, spacing
- [ ] No visual regressions

**Step 2: Fix any issues found**

**Step 3: Final commit if needed**

```bash
git add -A
git commit -m "fix(ui): address visual verification issues"
```
