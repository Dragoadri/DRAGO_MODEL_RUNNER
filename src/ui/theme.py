"""Matrix Theme Configuration"""

# ============================================
# MATRIX COLOR PALETTE
# ============================================

COLORS = {
    # Backgrounds
    "bg_dark": "#0a0a0a",
    "bg_primary": "#0d0d0d",
    "bg_secondary": "#111111",
    "bg_tertiary": "#1a1a1a",
    "bg_card": "#141414",
    "bg_input": "#0f0f0f",
    "bg_hover": "#1f1f1f",

    # Matrix Greens
    "matrix_green": "#00ff41",
    "matrix_green_dim": "#00cc33",
    "matrix_green_bright": "#33ff66",
    "matrix_green_dark": "#008f11",
    "matrix_glow": "#003311",

    # Accents
    "accent_cyan": "#00d4ff",
    "accent_red": "#ff0040",
    "accent_orange": "#ff6600",
    "accent_purple": "#9d00ff",

    # Text
    "text_primary": "#00ff41",
    "text_secondary": "#00cc33",
    "text_muted": "#006622",
    "text_white": "#e0e0e0",
    "text_dim": "#404040",

    # Borders
    "border_green": "#004411",
    "border_bright": "#00ff41",
    "border_dim": "#1a3a1a",

    # Focus/Active states
    "bg_focus": "#0a1f0a",
    "border_focus": "#00ff41",
    "bg_active_nav": "#0d2b0d",

    # Status
    "success": "#00ff41",
    "warning": "#ffcc00",
    "error": "#ff0040",
    "info": "#00d4ff",
}

# ============================================
# FONTS
# ============================================

FONTS = {
    "family_mono": "JetBrains Mono",
    "family_mono_fallback": "Consolas",
    "family_mono_fallback2": "Courier New",

    "size_xs": 12,
    "size_sm": 14,
    "size_md": 16,
    "size_lg": 18,
    "size_xl": 24,
    "size_xxl": 32,
    "size_title": 42,
}

# ============================================
# SPACING
# ============================================

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "xxl": 32,
}

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

# ============================================
# ASCII ART & DECORATIONS
# ============================================

ASCII_LOGO = """
██████╗ ██████╗  █████╗  ██████╗  ██████╗
██╔══██╗██╔══██╗██╔══██╗██╔════╝ ██╔═══██╗
██║  ██║██████╔╝███████║██║  ███╗██║   ██║
██║  ██║██╔══██╗██╔══██║██║   ██║██║   ██║
██████╔╝██║  ██║██║  ██║╚██████╔╝╚██████╔╝
╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝
"""

ASCII_LOGO_SMALL = """╔═══════════════════╗
║  ▓▓ DRAGO ▓▓     ║
║  MODEL RUNNER    ║
╚═══════════════════╝"""

DECORATIONS = {
    "corner_tl": "╔",
    "corner_tr": "╗",
    "corner_bl": "╚",
    "corner_br": "╝",
    "h_line": "═",
    "v_line": "║",
    "dot": "●",
    "arrow_r": "▶",
    "arrow_d": "▼",
    "block": "█",
    "block_light": "░",
    "block_med": "▒",
    "block_dark": "▓",
    "cursor": "▌",
    "prompt": "❯",
    "check": "✓",
    "cross": "✗",
    "star": "★",
    "circle": "○",
    "circle_filled": "●",
}

# ============================================
# WIDGET STYLES
# ============================================

BUTTON_STYLE = {
    "fg_color": COLORS["bg_tertiary"],
    "hover_color": COLORS["bg_hover"],
    "border_color": COLORS["matrix_green_dim"],
    "border_width": 1,
    "text_color": COLORS["matrix_green"],
    "corner_radius": 4,
}

BUTTON_PRIMARY_STYLE = {
    "fg_color": COLORS["matrix_green_dark"],
    "hover_color": COLORS["matrix_green_dim"],
    "border_color": COLORS["matrix_green"],
    "border_width": 1,
    "text_color": COLORS["bg_dark"],
    "corner_radius": 4,
}

BUTTON_DANGER_STYLE = {
    "fg_color": "#330011",
    "hover_color": "#550022",
    "border_color": COLORS["error"],
    "border_width": 1,
    "text_color": COLORS["error"],
    "corner_radius": 4,
}

ENTRY_STYLE = {
    "fg_color": COLORS["bg_input"],
    "border_color": COLORS["border_green"],
    "border_width": 1,
    "text_color": COLORS["matrix_green"],
    "corner_radius": 4,
}

FRAME_STYLE = {
    "fg_color": COLORS["bg_card"],
    "border_color": COLORS["border_green"],
    "border_width": 1,
    "corner_radius": 6,
}

LABEL_STYLE = {
    "text_color": COLORS["matrix_green"],
}

# ============================================
# STATUS INDICATORS
# ============================================

def get_status_color(status: str) -> str:
    """Get color for status indicator"""
    status_colors = {
        "connected": COLORS["success"],
        "disconnected": COLORS["error"],
        "loading": COLORS["warning"],
        "idle": COLORS["text_muted"],
    }
    return status_colors.get(status, COLORS["text_muted"])

def get_status_text(status: str) -> str:
    """Get formatted status text"""
    indicators = {
        "connected": f"{DECORATIONS['circle_filled']} ONLINE",
        "disconnected": f"{DECORATIONS['circle']} OFFLINE",
        "loading": f"{DECORATIONS['block_med']} LOADING",
        "idle": f"{DECORATIONS['circle']} IDLE",
    }
    return indicators.get(status, f"{DECORATIONS['circle']} UNKNOWN")
