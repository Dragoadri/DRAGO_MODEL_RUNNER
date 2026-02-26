# Chat Management Design

## Overview

Full chat management: persistent history, multiple sessions, delete chats, search, and export to Markdown. Stored as JSON files.

## Storage

- Directory: `~/.drago-model-runner/chats/`
- One `.json` file per chat, named `{uuid}.json`
- Chat schema:

```json
{
  "id": "uuid",
  "title": "First 40 chars of first user message...",
  "model": "model-name",
  "system_prompt": "...",
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

- Title auto-generated from first user message (~40 chars), renamable via double-click
- Chats listed in reverse chronological order (most recent first)

## New Module: `src/core/chat_storage.py`

```
ChatStorage
├── __init__(chats_dir)
├── save_chat(chat_data: dict)
├── load_chat(chat_id: str) -> dict
├── list_chats() -> list[dict]        # Returns id, title, model, updated_at
├── delete_chat(chat_id: str)
├── search_chats(query: str) -> list   # Searches title + message content
└── export_chat(chat_id: str, format: str) -> str   # "md" format
```

## UI Changes

### Sidebar

New CHATS section between STATUS and NAV buttons:

- `[+ NUEVO CHAT]` button
- Scrollable list of chats (compact items: title + date)
- Active chat highlighted in matrix green
- Hover reveals X button for delete (with confirmation dialog)
- Search field at bottom of list

### ChatPanel

- Auto-saves on every message send/receive
- On app launch, loads last active chat
- CLEAR button: saves current chat, creates new one
- Export button in chat header

### MainWindow

- Manages chat lifecycle (create, load, switch, delete)
- Passes ChatStorage to relevant panels
- Tracks active chat ID

## Export Format (Markdown)

```markdown
# Chat: [title]
**Model:** [model] | **Date:** [created_at]

---

**User:** [message]

**DRAGO:** [message]

---
...
```

## Files Modified

- `src/ui/main_window.py` — Chat lifecycle management, ChatStorage integration
- `src/ui/chat_panel.py` — Auto-save hooks, export button
- `src/ui/main_window.py` (Sidebar class) — Chat list UI, new chat button, search, delete

## Files Created

- `src/core/chat_storage.py` — Chat persistence layer
