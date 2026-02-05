"""Ollama API client wrapper"""
import subprocess
import json
from typing import Optional, List, Generator, Callable
from dataclasses import dataclass
from pathlib import Path
import threading

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@dataclass
class OllamaModel:
    """Represents an Ollama model"""
    name: str
    size: int
    modified_at: str
    digest: str

    @property
    def size_human(self) -> str:
        size = self.size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class OllamaClient:
    """Client for interacting with Ollama"""

    def __init__(self, host: str = "http://localhost:11434", timeout: int = 120):
        self.host = host
        self.timeout = timeout
        self._client = None

        if OLLAMA_AVAILABLE:
            self._client = ollama.Client(host=host)

    def is_running(self) -> bool:
        """Check if Ollama server is running"""
        try:
            if HTTPX_AVAILABLE:
                with httpx.Client(timeout=5) as client:
                    response = client.get(f"{self.host}/api/tags")
                    return response.status_code == 200
            else:
                # Fallback to subprocess
                result = subprocess.run(
                    ["curl", "-s", f"{self.host}/api/tags"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
        except Exception:
            return False

    def start_server(self) -> bool:
        """Attempt to start Ollama server"""
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            # Wait a bit for startup
            import time
            for _ in range(10):
                time.sleep(0.5)
                if self.is_running():
                    return True
            return False
        except Exception:
            return False

    def list_models(self) -> List[OllamaModel]:
        """List all available models"""
        models = []
        try:
            if self._client:
                response = self._client.list()
                # Handle both dict and object response formats
                model_list = response.get("models", []) if isinstance(response, dict) else getattr(response, 'models', [])
                for model in model_list:
                    # Handle both dict and object model formats
                    if isinstance(model, dict):
                        name = model.get("name", "")
                        size = model.get("size", 0)
                        modified = model.get("modified_at", "")
                        digest = model.get("digest", "")
                    else:
                        name = getattr(model, 'model', '') or getattr(model, 'name', '')
                        size = getattr(model, 'size', 0) or 0
                        modified = str(getattr(model, 'modified_at', ''))
                        digest = getattr(model, 'digest', '') or ''

                    if name:
                        models.append(OllamaModel(
                            name=name,
                            size=size if isinstance(size, int) else 0,
                            modified_at=modified,
                            digest=digest
                        ))
        except Exception as e:
            print(f"Error with ollama client: {e}")

        # Fallback to subprocess if no models found
        if not models:
            try:
                result = subprocess.run(
                    ["ollama", "list"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")[1:]  # Skip header
                    for line in lines:
                        parts = line.split()
                        if parts:
                            models.append(OllamaModel(
                                name=parts[0],
                                size=0,
                                modified_at="",
                                digest=parts[1] if len(parts) > 1 else ""
                            ))
            except Exception as e:
                print(f"Error listing models via subprocess: {e}")

        return models

    def create_model(
        self,
        name: str,
        modelfile_path: Path,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """Create a new model from a Modelfile"""
        try:
            modelfile_content = Path(modelfile_path).read_text()

            if self._client:
                # Use streaming to get progress
                for progress in self._client.create(
                    model=name,
                    modelfile=modelfile_content,
                    stream=True
                ):
                    if progress_callback:
                        status = progress.get("status", "")
                        progress_callback(status)
                return True
            else:
                # Fallback to subprocess
                result = subprocess.run(
                    ["ollama", "create", name, "-f", str(modelfile_path)],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                return result.returncode == 0
        except Exception as e:
            print(f"Error creating model: {e}")
            return False

    def delete_model(self, name: str) -> bool:
        """Delete a model"""
        try:
            if self._client:
                self._client.delete(name)
                return True
            else:
                result = subprocess.run(
                    ["ollama", "rm", name],
                    capture_output=True,
                    timeout=30
                )
                return result.returncode == 0
        except Exception:
            return False

    def pull_model(
        self,
        name: str,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """Pull a model from Ollama registry"""
        try:
            if self._client:
                for progress in self._client.pull(name, stream=True):
                    if progress_callback:
                        status = progress.get("status", "")
                        completed = progress.get("completed", 0)
                        total = progress.get("total", 1)
                        pct = (completed / total * 100) if total > 0 else 0
                        progress_callback(status, pct)
                return True
            else:
                result = subprocess.run(
                    ["ollama", "pull", name],
                    capture_output=True,
                    text=True,
                    timeout=3600
                )
                return result.returncode == 0
        except Exception as e:
            print(f"Error pulling model: {e}")
            return False

    def chat(
        self,
        model: str,
        messages: List[dict],
        stream: bool = True,
        options: Optional[dict] = None
    ) -> Generator[str, None, None]:
        """Send chat message and stream response"""
        try:
            if self._client:
                response = self._client.chat(
                    model=model,
                    messages=messages,
                    stream=stream,
                    options=options or {}
                )

                if stream:
                    for chunk in response:
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                else:
                    yield response.get("message", {}).get("content", "")
            else:
                # Fallback without streaming
                messages_json = json.dumps(messages)
                result = subprocess.run(
                    ["ollama", "run", model, messages[-1].get("content", "")],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                if result.returncode == 0:
                    yield result.stdout
        except Exception as e:
            yield f"Error: {e}"

    def chat_async(
        self,
        model: str,
        messages: List[dict],
        on_token: Callable[[str], None],
        on_complete: Callable[[], None],
        on_error: Callable[[str], None],
        options: Optional[dict] = None
    ) -> threading.Thread:
        """Async chat that calls callbacks on token/complete/error"""
        def run():
            try:
                for token in self.chat(model, messages, stream=True, options=options):
                    on_token(token)
                on_complete()
            except Exception as e:
                on_error(str(e))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread
