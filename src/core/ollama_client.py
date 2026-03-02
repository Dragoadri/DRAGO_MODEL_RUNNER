"""Ollama API client wrapper"""
import re
import subprocess
from typing import Optional, List, Generator, Callable
from dataclasses import dataclass
from pathlib import Path
import threading

from ..utils.logger import get_logger
from ..utils.helpers import format_size
log = get_logger("ollama_client")


def _validate_model_name(name: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_:.\-]*$', name)) and len(name) <= 100

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
        return format_size(self.size)


class OllamaClient:
    """Client for interacting with Ollama"""

    def __init__(self, host: str = "http://localhost:11434", timeout: int = 120):
        self.host = host
        self.timeout = timeout
        self._client = None

        if OLLAMA_AVAILABLE:
            self._client = ollama.Client(host=host)

    def is_installed(self) -> bool:
        """Check if the Ollama binary is installed on the system."""
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False

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

    def get_status(self) -> str:
        """Get a descriptive status string: 'running', 'stopped', or 'not_installed'."""
        if not self.is_installed():
            return "not_installed"
        if self.is_running():
            return "running"
        return "stopped"

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
            log.error("Error with ollama client: %s", e)

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
                log.error("Error listing models via subprocess: %s", e)

        return models

    @staticmethod
    def _clean_ollama_output(line: str) -> str:
        """Extract clean status text from ollama CLI output with ANSI codes and spinners."""
        import re
        # Strip all ANSI escape sequences
        clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
        # Strip terminal control sequences like [?25l, [1G, [K, [2K, [A
        clean = re.sub(r'\[\?[0-9]*[a-zA-Z]', '', clean)
        clean = re.sub(r'\[\d*[A-Z]', '', clean)
        # Strip spinner characters
        clean = re.sub(r'[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏⠋⠉⠈⠐⠠⠤⠆]', '', clean)
        # Collapse whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()

        # Extract most meaningful part: prefer lines with percentage
        # e.g. "gathering model components copying file sha256:abc... 45%"
        pct_match = re.search(r'(\d+%)', clean)
        # Find the last meaningful status phrase
        parts = clean.split('gathering model components')
        last_part = parts[-1].strip() if len(parts) > 1 else clean

        if not last_part and len(parts) > 1:
            last_part = "gathering model components"

        # Truncate long sha256 hashes for display
        last_part = re.sub(r'sha256:[a-f0-9]{20,}', 'sha256:...', last_part)

        return last_part.strip()

    def create_model(
        self,
        name: str,
        modelfile_path: Path,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """Create a new model from a Modelfile.

        Always uses subprocess with 'ollama create -f' because Ollama >= 0.15
        removed the 'modelfile' API parameter and the new 'from_' parameter
        only accepts model names, not filesystem paths to GGUF files.
        """
        if not _validate_model_name(name):
            raise ValueError(f"Invalid model name: {name!r}")
        try:
            process = subprocess.Popen(
                ["ollama", "create", name, "-f", str(modelfile_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            last_status = ""
            for line in iter(process.stdout.readline, ''):
                if not line.strip():
                    continue
                clean = self._clean_ollama_output(line)
                if clean and clean != last_status and progress_callback:
                    last_status = clean
                    progress_callback(clean)

            process.wait(timeout=600)
            return process.returncode == 0
        except Exception as e:
            log.error("Error creating model: %s", e)
            return False

    def delete_model(self, name: str) -> bool:
        """Delete a model"""
        if not _validate_model_name(name):
            raise ValueError(f"Invalid model name: {name!r}")
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
            log.error("Error pulling model: %s", e)
            return False

    def chat(
        self,
        model: str,
        messages: List[dict],
        stream: bool = True,
        options: Optional[dict] = None
    ) -> Generator[str, None, None]:
        """Send chat message and stream response.

        Raises on error instead of yielding error strings, so callers
        (like chat_async) can distinguish tokens from failures.
        """
        if self._client:
            try:
                response = self._client.chat(
                    model=model,
                    messages=messages,
                    stream=stream,
                    options=options or {}
                )
            except Exception as e:
                raise ConnectionError(f"Ollama chat failed: {e}") from e

            if stream:
                try:
                    for chunk in response:
                        if isinstance(chunk, dict):
                            content = chunk.get("message", {}).get("content", "")
                        else:
                            content = getattr(
                                getattr(chunk, "message", None), "content", ""
                            ) or ""
                        if content:
                            yield content
                except Exception as e:
                    # Server crashed or connection lost mid-stream
                    log.error("Stream interrupted: %s", e)
                    raise ConnectionError(f"Stream interrupted: {e}") from e
            else:
                if isinstance(response, dict):
                    yield response.get("message", {}).get("content", "")
                else:
                    yield getattr(
                        getattr(response, "message", None), "content", ""
                    ) or ""
        else:
            # Fallback without streaming
            try:
                result = subprocess.run(
                    ["ollama", "run", model, messages[-1].get("content", "")],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                if result.returncode == 0:
                    yield result.stdout
                else:
                    raise RuntimeError(
                        f"ollama run exited with code {result.returncode}: "
                        f"{result.stderr.strip()}"
                    )
            except subprocess.TimeoutExpired:
                raise TimeoutError(
                    f"Model response timed out after {self.timeout}s"
                )

    def chat_async(
        self,
        model: str,
        messages: List[dict],
        on_token: Callable[[str], None],
        on_complete: Callable[[], None],
        on_error: Callable[[str], None],
        options: Optional[dict] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> threading.Thread:
        """Async chat that calls callbacks on token/complete/error.

        If cancel_event is provided and set, streaming stops immediately.
        Handles mid-stream server crashes gracefully by calling on_error.
        """
        def run():
            try:
                for token in self.chat(model, messages, stream=True, options=options):
                    if cancel_event and cancel_event.is_set():
                        return
                    on_token(token)
                if cancel_event and cancel_event.is_set():
                    return
                on_complete()
            except (ConnectionError, TimeoutError) as e:
                if cancel_event and cancel_event.is_set():
                    return
                log.error("Chat stream error: %s", e)
                on_error(str(e))
            except Exception as e:
                if cancel_event and cancel_event.is_set():
                    return
                log.error("Unexpected chat error: %s", e)
                on_error(str(e))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread
