# UI Overhaul - Design Document

## Goal
Comprehensive UI audit and improvement across all panels while maintaining the Matrix green/dark aesthetic. Combines polish/consistency fixes (Enfoque A) with a sidebar redesign (Enfoque B).

## Problems Identified

### Visual Consistency
- Spacing hardcoded everywhere instead of using SPACING tokens
- Corner radius inconsistent (0, 4, 6, 8 mixed)
- Border colors inconsistent between panels

### UX/Layout
- Sidebar too dense: logo, model selector, status, chat list, nav, version all competing
- Nav buttons use generic block/arrow icons - hard to distinguish
- Chat input lacks focus state visual feedback
- Welcome message is plain text without visual hierarchy
- Status bar blends into input area

### Typography
- Everything in Consolas monospace - reduces readability for long text
- Font sizes too similar (12, 13, 14) - weak hierarchy

## Design Decisions

### 1. Theme Enhancements (theme.py)
- Add `RADIUS` dict: `sm=4, md=6, lg=8, xl=12`
- Add differentiated nav icons using Unicode symbols
- Add `NAV_ICONS` dict with distinct Unicode per section
- Add focus/active color variants

### 2. Sidebar Redesign (main_window.py)
**New layout (top to bottom):**
1. Compact logo + inline status dot
2. Model selector (compact, inline label)
3. Horizontal tab-style navigation (5 icon buttons in a row)
4. Separator
5. Chat list section (expands to fill) with fixed header: title + NEW + search
6. Version info removed (moved to Settings)

**Chat list items improved:**
- Better hover highlighting
- Cleaner truncation
- Timestamp on hover only (cleaner default view)

### 3. Chat Panel (chat_panel.py)
- Chat bubbles: increased internal padding, subtler separator, consistent radius
- Input area: green glow border on focus, clear visual separation from messages
- Welcome: centered ASCII art, command hints in styled cards
- Status bar: subtle top border separator, improved layout
- Translate toggle: inline in status bar area

### 4. Widgets (widgets.py)
- TerminalHeader: subtle styling refinements
- MatrixButton: improved hover transitions
- MatrixScrollableFrame: thinner scrollbar

### 5. All Panels
- Consistent section header pattern
- Consistent spacing using SPACING tokens
- Settings panel gets version info from sidebar

## Files Modified
- `src/ui/theme.py` - new tokens
- `src/ui/widgets.py` - widget refinements
- `src/ui/main_window.py` - sidebar redesign
- `src/ui/chat_panel.py` - chat UI polish
- `src/ui/settings_panel.py` - consistency + version info
- `src/ui/help_panel.py` - consistency
- `src/ui/system_panel.py` - consistency
- `src/ui/model_manager.py` - consistency

## Constraints
- Maintain all Matrix green/dark color palette
- No functional changes - only visual/layout
- No new dependencies
