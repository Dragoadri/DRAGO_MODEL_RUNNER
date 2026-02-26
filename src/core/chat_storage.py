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
