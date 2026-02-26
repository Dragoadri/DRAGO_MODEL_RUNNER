# Chat Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add persistent chat history with multi-session support, delete, search, and Markdown export.

**Architecture:** A `ChatStorage` class manages JSON files in `~/.drago-model-runner/chats/`. The Sidebar gets a chat list section. ChatPanel auto-saves on every message. MainWindow orchestrates chat lifecycle.

**Tech Stack:** Python 3, CustomTkinter, json, uuid, pathlib (all stdlib — no new dependencies)

---

### Task 1: Create ChatStorage module

**Files:**
- Create: `src/core/chat_storage.py`
- Modify: `src/core/__init__.py`

**Step 1: Create `src/core/chat_storage.py`**

```python
"""Persistent chat storage using JSON files"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class ChatStorage:
    """Manages chat sessions as JSON files in a local directory."""

    def __init__(self, chats_dir: Optional[str] = None):
        if chats_dir:
            self.chats_dir = Path(chats_dir).expanduser()
        else:
            self.chats_dir = Path.home() / ".drago-model-runner" / "chats"
        self.chats_dir.mkdir(parents=True, exist_ok=True)

    def new_chat(self, model: str = "", system_prompt: str = "") -> dict:
        """Create a new empty chat and return its data."""
        chat = {
            "id": str(uuid.uuid4()),
            "title": "New Chat",
            "model": model,
            "system_prompt": system_prompt,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
        }
        self._write(chat)
        return chat

    def save_chat(self, chat_data: dict) -> None:
        """Save/update a chat. Updates the updated_at timestamp."""
        chat_data["updated_at"] = datetime.now().isoformat()
        # Auto-generate title from first user message if still default
        if chat_data["title"] == "New Chat" and chat_data["messages"]:
            first_user = next(
                (m["content"] for m in chat_data["messages"] if m["role"] == "user"),
                None,
            )
            if first_user:
                chat_data["title"] = first_user[:40].strip()
                if len(first_user) > 40:
                    chat_data["title"] += "..."
        self._write(chat_data)

    def load_chat(self, chat_id: str) -> Optional[dict]:
        """Load a chat by ID. Returns None if not found."""
        path = self.chats_dir / f"{chat_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def list_chats(self) -> list[dict]:
        """List all chats (id, title, model, updated_at), newest first."""
        chats = []
        for path in self.chats_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                chats.append({
                    "id": data["id"],
                    "title": data.get("title", "Untitled"),
                    "model": data.get("model", ""),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len(data.get("messages", [])),
                })
            except Exception:
                continue
        chats.sort(key=lambda c: c["updated_at"], reverse=True)
        return chats

    def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat file. Returns True if deleted."""
        path = self.chats_dir / f"{chat_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def search_chats(self, query: str) -> list[dict]:
        """Search chats by title and message content."""
        query_lower = query.lower()
        results = []
        for path in self.chats_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                # Search title
                if query_lower in data.get("title", "").lower():
                    results.append({
                        "id": data["id"],
                        "title": data.get("title", "Untitled"),
                        "model": data.get("model", ""),
                        "updated_at": data.get("updated_at", ""),
                    })
                    continue
                # Search messages
                for msg in data.get("messages", []):
                    if query_lower in msg.get("content", "").lower():
                        results.append({
                            "id": data["id"],
                            "title": data.get("title", "Untitled"),
                            "model": data.get("model", ""),
                            "updated_at": data.get("updated_at", ""),
                        })
                        break
            except Exception:
                continue
        results.sort(key=lambda c: c["updated_at"], reverse=True)
        return results

    def export_chat(self, chat_id: str) -> Optional[str]:
        """Export a chat as Markdown. Returns None if not found."""
        chat = self.load_chat(chat_id)
        if not chat:
            return None

        lines = [
            f"# {chat['title']}",
            f"**Model:** {chat.get('model', 'N/A')} | **Date:** {chat.get('created_at', 'N/A')[:10]}",
            "",
            "---",
            "",
        ]
        for msg in chat.get("messages", []):
            role = "User" if msg["role"] == "user" else "DRAGO"
            lines.append(f"**{role}:** {msg['content']}")
            lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)

    def _write(self, chat_data: dict) -> None:
        """Write chat data to disk."""
        path = self.chats_dir / f"{chat_data['id']}.json"
        path.write_text(json.dumps(chat_data, indent=2, ensure_ascii=False), encoding="utf-8")
```

**Step 2: Export from `src/core/__init__.py`**

Add `ChatStorage` to the imports and `__all__`:

```python
from .chat_storage import ChatStorage
```

Add `"ChatStorage"` to the `__all__` list.

**Step 3: Verify**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && source .venv/bin/activate && python -c "from src.core import ChatStorage; s = ChatStorage('/tmp/test-chats'); c = s.new_chat('test'); print('OK:', c['id']); s.delete_chat(c['id'])"`

**Step 4: Commit**

```bash
git add src/core/chat_storage.py src/core/__init__.py
git commit -m "feat: add ChatStorage for persistent chat history"
```

---

### Task 2: Add chat list to Sidebar

**Files:**
- Modify: `src/ui/main_window.py` (Sidebar class only)

**Step 1: Restructure Sidebar grid layout**

Current layout uses rows 0-6. We need to insert a CHATS section. New layout:
- Row 0: Logo
- Row 1: Separator
- Row 2: Model selector
- Row 3: Status
- Row 4: Separator
- Row 5: **CHATS section (NEW)** — gets `weight=1` for expansion
- Row 6: Navigation buttons (fixed height, no weight)
- Row 7: Version info

Change `self.grid_rowconfigure(5, weight=1)` to `self.grid_rowconfigure(5, weight=1)` (same row, but now it's the chats section).

Move nav buttons from row 5 to row 6, version from row 6 to row 7.

**Step 2: Add CHATS section in `_setup_ui()`**

After the separator at row 4 and BEFORE the nav buttons, add:

```python
        # Chat list section
        chats_frame = ctk.CTkFrame(self, fg_color="transparent")
        chats_frame.grid(row=5, column=0, sticky="nsew", padx=10, pady=5)
        chats_frame.grid_rowconfigure(1, weight=1)
        chats_frame.grid_columnconfigure(0, weight=1)

        # Header with NEW CHAT button
        chats_header = ctk.CTkFrame(chats_frame, fg_color="transparent")
        chats_header.grid(row=0, column=0, sticky="ew")
        chats_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            chats_header,
            text=f" {DECORATIONS['h_line']*3} CHATS {DECORATIONS['h_line']*3}",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))

        new_chat_btn = MatrixButton(
            chats_header,
            text=f"{DECORATIONS['prompt']} NEW",
            height=24,
            width=60,
            command=lambda: self.on_nav("new_chat")
        )
        new_chat_btn.grid(row=0, column=1, sticky="e", pady=(0, 5))

        # Scrollable chat list
        self.chat_list_frame = MatrixScrollableFrame(
            chats_frame,
            fg_color=COLORS["bg_dark"],
            border_width=1,
            border_color=COLORS["border_green"],
        )
        self.chat_list_frame.grid(row=1, column=0, sticky="nsew")
        self.chat_list_frame.grid_columnconfigure(0, weight=1)

        # Search field
        self.chat_search = MatrixEntry(
            chats_frame,
            placeholder_text="Search chats...",
            height=28,
            width=200,
        )
        self.chat_search.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        self.chat_search.bind("<KeyRelease>", lambda e: self.on_nav("search_chats"))
```

Move nav_frame to row 6, version_frame to row 7. Update `self.grid_rowconfigure`:
```python
        self.grid_rowconfigure(5, weight=1)  # chats section expands
```

**Step 3: Add chat list management methods to Sidebar**

```python
    def update_chat_list(self, chats: list, active_id: str = None):
        """Update the chat list display.

        Args:
            chats: List of dicts with id, title, updated_at
            active_id: ID of the currently active chat
        """
        # Clear existing items
        for widget in self.chat_list_frame.winfo_children():
            widget.destroy()

        self._chat_items = {}

        for chat in chats:
            item = self._create_chat_item(chat, is_active=(chat["id"] == active_id))
            item.pack(fill="x", pady=2, padx=4)
            self._chat_items[chat["id"]] = item

    def _create_chat_item(self, chat: dict, is_active: bool = False) -> ctk.CTkFrame:
        """Create a single chat list item."""
        bg = COLORS["bg_tertiary"] if is_active else COLORS["bg_dark"]
        border = COLORS["matrix_green"] if is_active else COLORS["border_green"]

        item = ctk.CTkFrame(
            self.chat_list_frame,
            fg_color=bg,
            border_color=border,
            border_width=1,
            corner_radius=4,
            height=40,
        )
        item.grid_columnconfigure(0, weight=1)
        item.grid_propagate(False)

        # Title
        title = chat.get("title", "Untitled")
        if len(title) > 22:
            title = title[:22] + "..."
        title_label = ctk.CTkLabel(
            item,
            text=title,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["matrix_green"] if is_active else COLORS["matrix_green_dim"],
            anchor="w",
        )
        title_label.grid(row=0, column=0, sticky="w", padx=8, pady=(4, 0))

        # Date
        date_str = chat.get("updated_at", "")[:10]
        ctk.CTkLabel(
            item,
            text=date_str,
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 4))

        # Delete button (always visible for simplicity)
        del_btn = ctk.CTkButton(
            item,
            text=DECORATIONS["cross"],
            font=ctk.CTkFont(family="Consolas", size=11),
            width=24,
            height=24,
            fg_color="transparent",
            hover_color="#330011",
            text_color=COLORS["text_muted"],
            command=lambda cid=chat["id"]: self.on_nav(f"delete_chat:{cid}"),
        )
        del_btn.grid(row=0, column=1, rowspan=2, sticky="e", padx=4)

        # Click to load chat
        chat_id = chat["id"]
        for widget in [item, title_label]:
            widget.bind("<Button-1>", lambda e, cid=chat_id: self.on_nav(f"load_chat:{cid}"))

        return item

    def get_search_query(self) -> str:
        """Get current search text."""
        return self.chat_search.get().strip()
```

**Step 4: Commit**

```bash
git add src/ui/main_window.py
git commit -m "feat: add chat list section to sidebar"
```

---

### Task 3: Add auto-save and export to ChatPanel

**Files:**
- Modify: `src/ui/chat_panel.py`

**Step 1: Add chat state tracking to ChatPanel.__init__()**

After `self._auto_translate = False`, add:

```python
        self._current_chat: Optional[dict] = None
        self._on_chat_updated: Optional[Callable[[dict], None]] = None
```

**Step 2: Add chat management methods**

After the translation-related methods, add:

```python
    def set_chat_callback(self, callback: Callable[[dict], None]):
        """Set callback for when chat data changes (for auto-save)."""
        self._on_chat_updated = callback

    def load_chat(self, chat_data: dict):
        """Load a chat session into the panel."""
        # Clear current messages
        for widget in self.message_widgets:
            widget.destroy()
        self.message_widgets.clear()
        self.messages.clear()

        if hasattr(self, '_welcome_widget') and self._welcome_widget.winfo_exists():
            self._welcome_widget.destroy()

        self._current_chat = chat_data

        # Load messages
        for msg in chat_data.get("messages", []):
            widget = ChatMessage(self.messages_frame, msg["role"], msg["content"])
            widget.pack(fill="x", pady=8, padx=5)
            self.message_widgets.append(widget)
            self.messages.append(msg)
            # Wire translator for assistant messages
            if msg["role"] == "assistant" and self._translator:
                widget._translator = self._translator
                widget._translate_source = self._translate_source
                widget._translate_target = self._translate_target

        if not chat_data.get("messages"):
            self._show_welcome()

        # Set system prompt if stored
        if chat_data.get("system_prompt"):
            self._system_prompt = chat_data["system_prompt"]

        self._set_status("ready", "Chat loaded")
        self._update_token_count()
        self.after(50, self._scroll_to_bottom)

    def get_current_chat(self) -> Optional[dict]:
        """Get current chat data with latest messages."""
        if self._current_chat:
            self._current_chat["messages"] = self.messages.copy()
            if self._system_prompt:
                self._current_chat["system_prompt"] = self._system_prompt
        return self._current_chat

    def set_current_chat(self, chat_data: dict):
        """Set current chat reference (used when creating new chat)."""
        self._current_chat = chat_data

    def _notify_chat_updated(self):
        """Notify parent that chat data changed (for auto-save)."""
        if self._on_chat_updated and self._current_chat:
            self._current_chat["messages"] = self.messages.copy()
            self._on_chat_updated(self._current_chat)
```

**Step 3: Hook auto-save into message flow**

In `add_message()`, after `self._update_token_count()`, add:
```python
        self._notify_chat_updated()
```

In `finish_assistant_message()`, after `self._update_token_count()`, add:
```python
        self._notify_chat_updated()
```

**Step 4: Add export button to the header area**

In `_setup_ui()`, after creating the `TerminalHeader`, add an export button. Change the header line to store a reference:

Find: `header = TerminalHeader(self, "NEURAL INTERFACE", "chat.session")`
Replace with:
```python
        # Header with export button
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        header = TerminalHeader(header_frame, "NEURAL INTERFACE", "chat.session")
        header.grid(row=0, column=0, sticky="ew")

        self.export_btn = ctk.CTkButton(
            header_frame,
            text=f"{DECORATIONS['arrow_r']} EXPORT",
            font=ctk.CTkFont(family="Consolas", size=10),
            width=70,
            height=24,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["matrix_green_dim"],
            border_width=1,
            text_color=COLORS["matrix_green"],
            command=self._export_chat,
        )
        self.export_btn.grid(row=0, column=1, padx=10, pady=5, sticky="e")
```

Note: This means `header.grid(row=0...)` now goes in `header_frame`, not `self`. Update the main content grid row references: messages_container should now be at row=1 (it already is), input_frame at row=2, status_bar at row=3.

**Step 5: Add export method**

```python
    def _export_chat(self):
        """Export current chat as Markdown file."""
        from tkinter import filedialog

        if not self._current_chat or not self.messages:
            return

        title = self._current_chat.get("title", "chat")
        # Sanitize filename
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:50].strip()

        path = filedialog.asksaveasfilename(
            title="Export Chat",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")],
            initialfile=f"{safe_title}.md",
        )
        if not path:
            return

        # Build markdown
        lines = [
            f"# {title}",
            f"**Model:** {self._current_chat.get('model', 'N/A')} | "
            f"**Date:** {self._current_chat.get('created_at', '')[:10]}",
            "",
            "---",
            "",
        ]
        for msg in self.messages:
            role = "User" if msg["role"] == "user" else "DRAGO"
            lines.append(f"**{role}:** {msg['content']}")
            lines.append("")
            lines.append("---")
            lines.append("")

        Path(path).write_text("\n".join(lines), encoding="utf-8")
        self._set_status("ready", f"Exported to {Path(path).name}")
```

**Step 6: Update `clear_chat` to notify parent**

In `clear_chat()`, after `self._show_welcome()`, add:
```python
        self._current_chat = None
        if self._on_chat_updated:
            self._on_chat_updated(None)  # Signal to parent to create new chat
```

**Step 7: Commit**

```bash
git add src/ui/chat_panel.py
git commit -m "feat: add auto-save, load, export, and chat lifecycle to ChatPanel"
```

---

### Task 4: Wire chat management into MainWindow

**Files:**
- Modify: `src/ui/main_window.py` (MainWindow class)

**Step 1: Import ChatStorage**

Change: `from ..core import OllamaClient, GGUFManager, TranslationService`
To: `from ..core import OllamaClient, GGUFManager, TranslationService, ChatStorage`

**Step 2: Initialize ChatStorage in `_init_core()`**

After the translator initialization block, add:

```python
        # Chat storage
        self.chat_storage = ChatStorage()
        self.active_chat_id: Optional[str] = None
```

**Step 3: Wire chat callback and load last chat in `_setup_ui()`**

After creating `self.chat_panel`, add:

```python
        self.chat_panel.set_chat_callback(self._on_chat_data_updated)
```

**Step 4: Load last chat and refresh chat list at startup**

In `_startup_sequence()`, inside the `update()` function (after setting status and refreshing models), add:

```python
                    # Load last chat or create new
                    self._load_last_or_new_chat()
                    self._refresh_chat_list()
```

**Step 5: Add chat management methods to MainWindow**

```python
    def _load_last_or_new_chat(self):
        """Load the most recent chat or create a new one."""
        chats = self.chat_storage.list_chats()
        if chats:
            chat_data = self.chat_storage.load_chat(chats[0]["id"])
            if chat_data:
                self.active_chat_id = chat_data["id"]
                self.chat_panel.load_chat(chat_data)
                return
        # No chats exist, create new
        self._create_new_chat()

    def _create_new_chat(self):
        """Create a new empty chat session."""
        model = self.sidebar.get_selected_model()
        if model in ["No models", "Loading..."]:
            model = ""
        chat = self.chat_storage.new_chat(model=model)
        self.active_chat_id = chat["id"]
        self.chat_panel.clear_chat()
        self.chat_panel.set_current_chat(chat)
        self._refresh_chat_list()

    def _on_chat_data_updated(self, chat_data):
        """Called by ChatPanel when messages change (auto-save)."""
        if chat_data is None:
            # Chat was cleared — create new
            self._create_new_chat()
            return
        chat_data["model"] = self.current_model or ""
        self.chat_storage.save_chat(chat_data)
        self._refresh_chat_list()

    def _refresh_chat_list(self):
        """Refresh the chat list in the sidebar."""
        query = self.sidebar.get_search_query()
        if query:
            chats = self.chat_storage.search_chats(query)
        else:
            chats = self.chat_storage.list_chats()
        self.sidebar.update_chat_list(chats, self.active_chat_id)

    def _load_chat(self, chat_id: str):
        """Load a specific chat."""
        chat_data = self.chat_storage.load_chat(chat_id)
        if chat_data:
            self.active_chat_id = chat_id
            self.chat_panel.load_chat(chat_data)
            self._refresh_chat_list()
            # Switch to chat panel if not already there
            self._show_panel("chat")
            self.sidebar._on_nav_click("chat")

    def _delete_chat(self, chat_id: str):
        """Delete a chat with confirmation."""
        from tkinter import messagebox
        if not messagebox.askyesno("Delete Chat", "Are you sure you want to delete this chat?"):
            return
        self.chat_storage.delete_chat(chat_id)
        if chat_id == self.active_chat_id:
            self._load_last_or_new_chat()
        self._refresh_chat_list()
```

**Step 6: Handle new nav events in `_on_nav()`**

Update `_on_nav()` to handle chat-related events:

```python
    def _on_nav(self, panel_name: str):
        """Handle navigation"""
        if panel_name == "refresh_models":
            self._refresh_models()
        elif panel_name == "new_chat":
            self._create_new_chat()
            self._show_panel("chat")
            self.sidebar._on_nav_click("chat")
        elif panel_name == "search_chats":
            self._refresh_chat_list()
        elif panel_name.startswith("load_chat:"):
            chat_id = panel_name.split(":", 1)[1]
            self._load_chat(chat_id)
        elif panel_name.startswith("delete_chat:"):
            chat_id = panel_name.split(":", 1)[1]
            self._delete_chat(chat_id)
        else:
            self._show_panel(panel_name)
```

**Step 7: Verify app launches and chat management works**

Run: `cd /home/drago/Escritorio/PROYECTS/SCRIPTS/DRAGO_MODEL_RUNNER && source .venv/bin/activate && python main.py`

Test:
1. App creates a new chat on first launch
2. Send a message — chat auto-saves
3. Click "+ NEW" — new chat created, old one in list
4. Click on old chat in list — loads it
5. Click X on a chat — confirmation → deletes
6. Type in search — filters the list

**Step 8: Commit**

```bash
git add src/ui/main_window.py
git commit -m "feat: wire chat management into MainWindow lifecycle"
```

---

### Task 5: Final integration test

**Step 1: Full test**

Run the app and verify:
- [ ] First launch creates a new chat
- [ ] Messages auto-save (check `~/.drago-model-runner/chats/` for JSON files)
- [ ] Chat list shows in sidebar with titles and dates
- [ ] "+ NEW" creates a new empty chat
- [ ] Clicking a chat in the list loads it
- [ ] X button deletes chat (with confirmation)
- [ ] Search field filters chats
- [ ] Export button saves Markdown file
- [ ] CLEAR button creates a new chat (old one stays in list)
- [ ] App remembers last chat on restart
- [ ] Translation features still work
- [ ] Dock icon still shows correctly

**Step 2: Fix any issues found during testing**
