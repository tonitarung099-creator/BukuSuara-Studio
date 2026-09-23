from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from lib.classes.gemini_agent import (
    DEFAULT_GEMINI_MODEL,
    available_api_keys,
    classify_api_error,
    get_session_api_keys,
    get_session_model,
    mark_api_key_failure,
)

CACHE_FILENAME = "gemini_pronunciation_map.json"
MAX_TERMS_PER_REQUEST = 60
MAX_CONTEXT_CHARS = 180

_CAPITALIZED_PHRASE = re.compile(
    r"(?<!\w)(?:[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’.-]{1,})(?:\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’.-]{1,}){0,2}(?!\w)"
)
_ACRONYM = re.compile(r"(?<!\w)[A-Z]{2,8}(?!\w)")
_MIXED_CASE = re.compile(r"(?<!\w)[A-Za-z]*[a-z][A-Z][A-Za-z]*(?!\w)")
_SUSPICIOUS = re.compile(
    r"(?<!\w)[A-Za-zÀ-ÖØ-öø-ÿ'’-]{3,}(?:tion|sion|ough|augh|eigh|tch|dge|ph|th|sh|ch|wh|qu|ck|ee|oo|ea|ow|igh)[A-Za-zÀ-ÖØ-öø-ÿ'’-]*(?!\w)",
    re.IGNORECASE,
)
_URLISH = re.compile(r"(?:https?://|www\.|@|\.(?:com|net|org|id)\b)", re.IGNORECASE)
_ALLOWED_ALIAS = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ'’ -]{1,120}$")


class PronunciationError(RuntimeError):
    pass


class GeminiPronunciationProcessor:
    """Build and apply a Gemini-generated Indonesian pronunciation dictionary."""

    def __init__(self, session_id: str, process_dir: str, model: str | None = None) -> None:
        self.session_id = str(session_id)
        self.process_dir = process_dir
        self.model = model or get_session_model(session_id) or DEFAULT_GEMINI_MODEL
        self.api_keys = get_session_api_keys(session_id)
        self.cache_path = os.path.join(process_dir, CACHE_FILENAME)
        self.cache: dict[str, str] = self._load_cache()

    def _load_cache(self) -> dict[str, str]:
        try:
            if os.path.exists(self.cache_path):
                data = json.loads(Path(self.cache_path).read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {
                        str(k): str(v)
                        for k, v in data.items()
                        if self._valid_alias(str(k), str(v))
                    }
        except Exception:
            pass
        return {}

    def _save_cache(self) -> None:
        Path(self.process_dir).mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path + ".tmp"
        Path(tmp).write_text(
            json.dumps(dict(sorted(self.cache.items())), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, self.cache_path)

    @staticmethod
    def _valid_alias(original: str, alias: str) -> bool:
        original = original.strip()
        alias = alias.strip()
        if not original or not alias or original == alias:
            return False
        if len(alias) > max(120, len(original) * 4):
            return False
        if not _ALLOWED_ALIAS.fullmatch(alias):
            return False
        return True

    @staticmethod
    def _context(text: str, term: str) -> str:
        pos = text.find(term)
        if pos < 0:
            return ""
        start = max(0, pos - 70)
        end = min(len(text), pos + len(term) + 70)
        return " ".join(text[start:end].split())[:MAX_CONTEXT_CHARS]

    def collect_candidates(self, blocks: list[str]) -> dict[str, str]:
        candidates: dict[str, str] = {}
        for text in blocks:
            if not text:
                continue
            plain = re.sub(r"\[(?:break|pause)(?::[^\]]+)?\]", " ", text, flags=re.IGNORECASE)
            for pattern in (_CAPITALIZED_PHRASE, _ACRONYM, _MIXED_CASE, _SUSPICIOUS):
                for match in pattern.finditer(plain):
                    term = match.group(0).strip(" .,:;!?()[]{}\"")
                    if len(term) < 2 or len(term) > 80:
                        continue
                    if term.isdigit() or _URLISH.search(term):
                        continue
                    candidates.setdefault(term, self._context(plain, term))
        return candidates

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        cleaned = (text or "").strip()
        fence = chr(96) * 3
        if cleaned.startswith(fence):
            cleaned = re.sub(r"^" + re.escape(fence) + r"(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*" + re.escape(fence) + r"$", "", cleaned)
        try:
            data = json.loads(cleaned)
            return data if isinstance(data, dict) else {}
        except Exception:
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start >= 0 and end > start:
                data = json.loads(cleaned[start:end + 1])
                return data if isinstance(data, dict) else {}
            raise

    def _request_chunk(self, chunk: list[tuple[str, str]]) -> dict[str, str]:
        if not self.api_keys:
            raise PronunciationError(
                "API key Gemini belum tersedia. Isi API key pada tab Agen Gemini sebelum generate DOCX/TXT."
            )

        items = [{"term": term, "context": context} for term, context in chunk]
        prompt = (
            "Anda membuat kamus pengucapan untuk audiobook Bahasa Indonesia. "
            "Nilai setiap istilah kandidat. Jika istilah/nama asing berpotensi salah dibaca oleh TTS Indonesia, "
            "buat ejaan bunyi yang nyaman dibaca penutur Indonesia. Jangan menerjemahkan arti. "
            "Jangan mengubah istilah Indonesia yang sudah wajar. Jangan gunakan IPA. "
            "Kembalikan HANYA objek JSON dengan format {\"istilah asli\": \"ejaan bunyi\"}. "
            "Omit istilah yang tidak perlu diubah. Key JSON harus sama persis dengan term input.\n\n"
            f"KANDIDAT:\n{json.dumps(items, ensure_ascii=False)}"
        )

        last_error: Exception | None = None
        for _, key in available_api_keys(self.api_keys):
            try:
                client = genai.Client(api_key=key)
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=1800,
                        response_mime_type="application/json",
                    ),
                )
                raw = self._extract_json(response.text or "{}")
                allowed = {term for term, _ in chunk}
                result: dict[str, str] = {}
                for original, alias in raw.items():
                    original = str(original).strip()
                    alias = str(alias).strip()
                    if original in allowed and self._valid_alias(original, alias):
                        result[original] = alias
                return result
            except Exception as exc:
                last_error = exc
                kind = classify_api_error(exc)
                if kind in {"quota", "invalid_key"}:
                    mark_api_key_failure(key, kind)
                    continue
                break

        raise PronunciationError(
            f"Gemini pronunciation gagal setelah rotasi API key: {str(last_error)[:300]}"
        )

    def build_dictionary(self, blocks: list[str], progress_callback=None) -> dict[str, str]:
        candidates = self.collect_candidates(blocks)
        pending = [(term, ctx) for term, ctx in candidates.items() if term not in self.cache]
        if not pending:
            return dict(self.cache)

        total_chunks = (len(pending) + MAX_TERMS_PER_REQUEST - 1) // MAX_TERMS_PER_REQUEST
        for chunk_index in range(total_chunks):
            start = chunk_index * MAX_TERMS_PER_REQUEST
            chunk = pending[start:start + MAX_TERMS_PER_REQUEST]
            updates = self._request_chunk(chunk)
            self.cache.update(updates)
            self._save_cache()
            if progress_callback:
                progress_callback(chunk_index + 1, total_chunks, len(self.cache))
        return dict(self.cache)

    def apply_dictionary(self, blocks: list[str]) -> list[str]:
        if not self.cache:
            return list(blocks)
        items = sorted(self.cache.items(), key=lambda kv: len(kv[0]), reverse=True)
        out: list[str] = []
        for text in blocks:
            result = text
            for original, alias in items:
                pattern = re.compile(rf"(?<!\w){re.escape(original)}(?!\w)")
                result = pattern.sub(alias, result)
            out.append(result)
        return out

    def process_blocks(self, blocks: list[str], progress_callback=None) -> tuple[list[str], dict[str, str]]:
        self.build_dictionary(blocks, progress_callback=progress_callback)
        return self.apply_dictionary(blocks), dict(self.cache)
