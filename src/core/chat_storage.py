"""Persistent chat storage using JSON files with in-memory metadata cache"""
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..utils.logger import get_logger
log = get_logger("chat_storage")

# Maximum number of chats returned by list_chats / search_chats
_MAX_LIST = 50


class ChatStorage:
    """Manages chat sessions as JSON files in a local directory.

    Keeps a lightweight in-memory cache of chat metadata so that
    list_chats() never has to re-read every file on disk.
    """

    def __init__(self, chats_dir: Optional[str] = None):
        if chats_dir:
            self.chats_dir = Path(chats_dir).expanduser()
        else:
            self.chats_dir = Path.home() / ".drago-model-runner" / "chats"
        self.chats_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()

        # {chat_id: {id, title, model, updated_at, message_count}}
        self._cache: dict[str, dict] = {}
        self._build_cache()

    # ── Cache helpers ─────────────────────────────────────────────

    def _build_cache(self) -> None:
        """One-time scan of all JSON files to populate the metadata cache.

        Corrupted files are quarantined (renamed .corrupt) so they don't
        keep causing errors on every startup.
        """
        with self._lock:
            for path in self.chats_dir.glob("*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if "id" not in data:
                        raise ValueError("Missing 'id' field")
                    self._cache[data["id"]] = self._extract_meta(data)
                except (json.JSONDecodeError, ValueError) as exc:
                    log.warning("Corrupted chat file %s: %s — quarantining", path.name, exc)
                    try:
                        path.rename(path.with_suffix(".json.corrupt"))
                    except OSError:
                        pass
                except (KeyError, OSError) as exc:
                    log.warning("Failed to load chat file %s: %s", path.name, exc)
                    continue

    @staticmethod
    def _extract_meta(data: dict) -> dict:
        return {
            "id": data["id"],
            "title": data.get("title", "Untitled"),
            "model": data.get("model", ""),
            "updated_at": data.get("updated_at", ""),
            "message_count": len(data.get("messages", [])),
        }

    # ── Public API ────────────────────────────────────────────────

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
        with self._lock:
            self._write(chat)
            self._cache[chat["id"]] = self._extract_meta(chat)
        return chat

    def save_chat(self, chat_data: dict) -> None:
        """Save/update a chat. Updates the updated_at timestamp."""
        with self._lock:
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
            self._cache[chat_data["id"]] = self._extract_meta(chat_data)

    def load_chat(self, chat_id: str) -> Optional[dict]:
        """Load a chat by ID. Returns None if not found.

        Handles corrupted files by renaming them with a .corrupt suffix
        and removing them from the cache.
        """
        with self._lock:
            path = self.chats_dir / f"{chat_id}.json"
            if not path.exists():
                return None
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                # Validate minimal structure
                if "id" not in data or "messages" not in data:
                    raise ValueError("Missing required fields (id, messages)")
                return data
            except (json.JSONDecodeError, ValueError) as exc:
                log.warning("Corrupted chat file %s: %s — quarantining", chat_id, exc)
                # Quarantine the corrupted file
                try:
                    corrupt_path = path.with_suffix(".json.corrupt")
                    path.rename(corrupt_path)
                except OSError:
                    pass
                self._cache.pop(chat_id, None)
                return None
            except OSError as exc:
                log.warning("Failed to read chat %s: %s", chat_id, exc)
                return None

    def list_chats(self, limit: int = _MAX_LIST) -> list[dict]:
        """List chats (id, title, model, updated_at), newest first.

        Only returns chats that have at least one message (skips empty
        "New Chat" entries).  Returns at most *limit* entries from the
        in-memory cache (no disk I/O).
        """
        with self._lock:
            chats = sorted(
                (c for c in self._cache.values() if c.get("message_count", 0) > 0),
                key=lambda c: c["updated_at"],
                reverse=True,
            )
            return chats[:limit]

    def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat file. Returns True if deleted."""
        with self._lock:
            path = self.chats_dir / f"{chat_id}.json"
            self._cache.pop(chat_id, None)
            if path.exists():
                path.unlink()
                return True
            return False

    def search_chats(self, query: str, limit: int = _MAX_LIST) -> list[dict]:
        """Search chats by title (from cache) and message content (from disk).

        Title matches come from the fast in-memory cache.  Only when a title
        doesn't match do we fall back to reading the file from disk.
        """
        with self._lock:
            query_lower = query.lower()
            results: list[dict] = []

            # Fast pass: title matches from cache (skip empty chats)
            title_matched_ids: set[str] = set()
            for meta in self._cache.values():
                if meta.get("message_count", 0) == 0:
                    continue
                if query_lower in meta.get("title", "").lower():
                    results.append(meta)
                    title_matched_ids.add(meta["id"])
                    if len(results) >= limit:
                        break

            # Slow pass: content search (only for chats not already matched)
            if len(results) < limit:
                for path in self.chats_dir.glob("*.json"):
                    chat_id = path.stem
                    if chat_id in title_matched_ids:
                        continue
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                        for msg in data.get("messages", []):
                            if query_lower in msg.get("content", "").lower():
                                results.append(self._extract_meta(data))
                                break
                    except (json.JSONDecodeError, KeyError, OSError) as exc:
                        log.warning("Failed to search chat file %s: %s", path.name, exc)
                        continue
                    if len(results) >= limit:
                        break

            results.sort(key=lambda c: c["updated_at"], reverse=True)
            return results[:limit]

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
        """Write chat data to disk atomically.

        Writes to a temp file first, then renames.  This prevents partial
        writes from corrupting the file if the app crashes mid-save.
        """
        path = self.chats_dir / f"{chat_data['id']}.json"
        tmp_path = path.with_suffix(".json.tmp")
        try:
            tmp_path.write_text(
                json.dumps(chat_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            tmp_path.replace(path)  # atomic on POSIX
        except OSError as exc:
            log.error("Failed to write chat %s: %s", chat_data.get("id"), exc)
            # Clean up temp file if it exists
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
