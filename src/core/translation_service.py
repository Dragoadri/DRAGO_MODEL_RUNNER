"""Offline translation service using Argos Translate (ES<->EN)"""
import threading
from typing import Optional, Callable


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
                try:
                    package.update_package_index()
                except Exception:
                    _progress("Index update failed (offline?), using cached...")

                available = package.get_available_packages()

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
                        _progress(f"Language pack {pair_label} not found in index")
                        if on_complete is not None:
                            on_complete(False)
                        return

                    _progress(f"Downloading language pack {pair_label}...")
                    download_path = pkg.download()
                    _progress(f"Installing language pack {pair_label}...")
                    package.install_from_path(download_path)

            # Cache installed translation objects for fast lookups
            installed_languages = translate.get_installed_languages()
            lang_map = {lang.code: lang for lang in installed_languages}

            for from_code, to_code in needed_pairs:
                src = lang_map.get(from_code)
                dst = lang_map.get(to_code)
                if src is not None and dst is not None:
                    translation = src.get_translation(dst)
                    if translation is not None:
                        self._installed_pairs[(from_code, to_code)] = translation

            self._ready = True
            _progress("Translation service ready")
            if on_complete is not None:
                on_complete(True)

        except Exception as exc:
            if on_progress is not None:
                on_progress(f"Translation init error: {exc}")
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

        try:
            translation = self._installed_pairs.get((from_lang, to_lang))
            if translation is not None:
                return translation.translate(text)

            # Fallback: look up via argostranslate.translate at runtime
            import argostranslate.translate as translate

            installed_languages = translate.get_installed_languages()
            lang_map = {lang.code: lang for lang in installed_languages}
            src = lang_map.get(from_lang)
            dst = lang_map.get(to_lang)
            if src is not None and dst is not None:
                tr = src.get_translation(dst)
                if tr is not None:
                    self._installed_pairs[(from_lang, to_lang)] = tr
                    return tr.translate(text)

            return text
        except Exception:
            return text

    def is_ready(self) -> bool:
        """Return True when the translation engine is initialized and usable."""
        return self._ready
