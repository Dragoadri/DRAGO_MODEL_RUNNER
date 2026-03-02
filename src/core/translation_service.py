"""Offline translation service using Argos Translate (ES<->EN)"""
import threading
from typing import Optional, Callable

from ..utils.logger import get_logger
log = get_logger("translation_service")


class TranslationService:
    """Singleton service wrapping Argos Translate for offline ES<->EN translation.

    Usage:
        service = TranslationService.get_instance()
        service.initialize("es", "en", on_progress=..., on_complete=...)
        # After on_complete(True):
        result = service.translate("Hola mundo", "es", "en")
    """

    _instance: Optional["TranslationService"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._ready = False
        self._installed_pairs: dict[tuple[str, str], object] = {}
        self._translation_cache: dict[tuple[str, str, str], str] = {}
        self._cache_max = 500
        self._init_error: Optional[str] = None
        self._initializing = False

    @classmethod
    def get_instance(cls) -> "TranslationService":
        """Return the singleton instance, creating it if necessary (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization (background)
    # ------------------------------------------------------------------

    def initialize(
        self,
        source_lang: str,
        target_lang: str,
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[bool], None]] = None,
    ) -> None:
        """Download language packs (if needed) in a background thread.

        Installs both directions: source->target AND target->source.
        Calls *on_progress* with human-readable status strings and
        *on_complete(True/False)* when finished.
        """
        self._initializing = True
        self._init_error = None
        thread = threading.Thread(
            target=self._initialize_worker,
            args=(source_lang, target_lang, on_progress, on_complete),
            daemon=True,
        )
        thread.start()

    def _initialize_worker(
        self,
        source_lang: str,
        target_lang: str,
        on_progress: Optional[Callable[[str], None]],
        on_complete: Optional[Callable[[bool], None]],
    ) -> None:
        """Worker executed in a background thread by *initialize*."""
        try:
            import argostranslate.package as package
            import argostranslate.translate as translate

            def _progress(msg: str) -> None:
                if on_progress is not None:
                    on_progress(msg)

            needed_pairs = [
                (source_lang, target_lang),
                (target_lang, source_lang),
            ]

            # Check what's already installed FIRST (fast, no network)
            _progress("Checking installed language packs...")
            installed = package.get_installed_packages()
            missing_pairs = []
            for from_code, to_code in needed_pairs:
                already = any(
                    ip.from_code == from_code and ip.to_code == to_code
                    for ip in installed
                )
                if already:
                    _progress(f"Language pack {from_code}->{to_code} already installed")
                else:
                    missing_pairs.append((from_code, to_code))

            # Only hit the network if we need to download something
            if missing_pairs:
                _progress("Updating Argos Translate package index...")
                index_ok = False
                try:
                    package.update_package_index()
                    index_ok = True
                except Exception as exc:
                    log.warning("Index update failed (offline?): %s", exc)
                    _progress("No internet - cannot download language packs")

                available = package.get_available_packages()

                if not available and not index_ok:
                    missing_labels = ", ".join(
                        f"{f}->{t}" for f, t in missing_pairs
                    )
                    err_msg = (
                        f"Language packs ({missing_labels}) not installed. "
                        "Internet required for first-time download."
                    )
                    self._init_error = err_msg
                    _progress(err_msg)
                    self._initializing = False
                    if on_complete is not None:
                        on_complete(False)
                    return

                for from_code, to_code in missing_pairs:
                    pair_label = f"{from_code}->{to_code}"
                    pkg = next(
                        (
                            p
                            for p in available
                            if p.from_code == from_code and p.to_code == to_code
                        ),
                        None,
                    )

                    if pkg is None:
                        err_msg = f"Language pack {pair_label} not found in index"
                        self._init_error = err_msg
                        _progress(err_msg)
                        self._initializing = False
                        if on_complete is not None:
                            on_complete(False)
                        return

                    _progress(f"Downloading language pack {pair_label}...")
                    try:
                        download_path = pkg.download()
                        _progress(f"Installing language pack {pair_label}...")
                        package.install_from_path(download_path)
                    except Exception as exc:
                        err_msg = f"Failed to download {pair_label}: {exc}"
                        self._init_error = err_msg
                        log.error(err_msg)
                        _progress(err_msg)
                        self._initializing = False
                        if on_complete is not None:
                            on_complete(False)
                        return

            # Cache installed translation objects for fast lookups
            installed_languages = translate.get_installed_languages()
            lang_map = {lang.code: lang for lang in installed_languages}

            for from_code, to_code in needed_pairs:
                src = lang_map.get(from_code)
                dst = lang_map.get(to_code)
                if src is not None and dst is not None:
                    translation = src.get_translation(dst)
                    if translation is not None:
                        with self._lock:
                            self._installed_pairs[(from_code, to_code)] = translation

            self._ready = True
            self._initializing = False
            _progress("Translation service ready")
            if on_complete is not None:
                on_complete(True)

        except ImportError:
            err_msg = "argostranslate not installed. Run: pip install argostranslate"
            self._init_error = err_msg
            log.error(err_msg)
            if on_progress is not None:
                on_progress(err_msg)
            self._initializing = False
            if on_complete is not None:
                on_complete(False)

        except Exception as exc:
            err_msg = f"Translation init error: {exc}"
            self._init_error = err_msg
            log.error("Translation initialization failed: %s", exc)
            if on_progress is not None:
                on_progress(err_msg)
            self._initializing = False
            if on_complete is not None:
                on_complete(False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def translate(self, text: str, from_lang: str, to_lang: str) -> str:
        """Translate *text* between languages.

        Returns the translated string, or the original *text* unchanged
        if the service is not ready or an error occurs.
        """
        if not self._ready:
            return text

        if not text or not text.strip():
            return text

        # Check cache first
        cache_key = (text, from_lang, to_lang)
        cached = self._translation_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            with self._lock:
                translation = self._installed_pairs.get((from_lang, to_lang))
            if translation is not None:
                result = translation.translate(text)
                self._cache_translation(cache_key, result)
                return result

            # Fallback: look up via argostranslate.translate at runtime
            import argostranslate.translate as translate

            installed_languages = translate.get_installed_languages()
            lang_map = {lang.code: lang for lang in installed_languages}
            src = lang_map.get(from_lang)
            dst = lang_map.get(to_lang)
            if src is not None and dst is not None:
                tr = src.get_translation(dst)
                if tr is not None:
                    with self._lock:
                        self._installed_pairs[(from_lang, to_lang)] = tr
                    result = tr.translate(text)
                    self._cache_translation(cache_key, result)
                    return result

            return text
        except Exception as exc:
            log.warning("Translation failed for %s->%s: %s", from_lang, to_lang, exc)
            return text

    def _cache_translation(self, key: tuple, value: str) -> None:
        """Add a translation to the cache, evicting oldest if full."""
        if len(self._translation_cache) >= self._cache_max:
            # Remove oldest entry (first key)
            try:
                oldest = next(iter(self._translation_cache))
                del self._translation_cache[oldest]
            except StopIteration:
                pass
        self._translation_cache[key] = value

    def clear_cache(self) -> None:
        """Clear the translation cache."""
        self._translation_cache.clear()

    def is_ready(self) -> bool:
        """Return True when the translation engine is initialized and usable."""
        return self._ready

    def is_initializing(self) -> bool:
        """Return True while background initialization is running."""
        return self._initializing

    def get_error(self) -> Optional[str]:
        """Return the last initialization error, or None if no error."""
        return self._init_error
