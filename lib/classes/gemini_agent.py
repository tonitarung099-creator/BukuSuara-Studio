from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Any, Iterable

from google import genai
from google.genai import types

from lib.conf import output_formats
from lib.conf_models import TTS_ENGINES


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
MAX_API_KEYS = 100
FREE_TIER_MODELS = [
    ("Gemini 3.5 Flash-Lite — hemat (disarankan)", "gemini-3.5-flash-lite"),
    ("Gemini 3.1 Flash-Lite — hemat", "gemini-3.1-flash-lite"),
    ("Gemini 3 Flash Preview — lebih pintar, kuota biasanya lebih ketat", "gemini-3-flash-preview"),
]

_RETRY_MARKERS = (
    "429",
    "resource_exhausted",
    "quota",
    "rate limit",
    "rate_limit",
    "503",
    "unavailable",
    "overloaded",
)
_KEY_COOLDOWN: dict[str, float] = {}
_KEY_DISABLED_UNTIL: dict[str, float] = {}
_SESSION_API_KEYS: dict[str, list[str]] = {}
_SESSION_MODELS: dict[str, str] = {}


def _fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def parse_api_keys(value: str | Iterable[str] | None) -> list[str]:
    """Parse up to MAX_API_KEYS unique Gemini keys without logging them."""
    if value is None:
        env = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or ""
        value = env
    if isinstance(value, str):
        normalized = value.replace(";", "\n").replace(",", "\n")
        items = normalized.splitlines()
    else:
        items = list(value)
    result: list[str] = []
    seen: set[str] = set()
    for raw in items:
        key = str(raw).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
        if len(result) >= MAX_API_KEYS:
            break
    return result


def set_session_api_keys(session_id: str | None, value: str | Iterable[str] | None) -> int:
    """Keep Gemini keys in process memory only; never serialize them into audiobook sessions."""
    if not session_id:
        return 0
    keys = parse_api_keys(value)
    if keys:
        _SESSION_API_KEYS[str(session_id)] = keys
    else:
        _SESSION_API_KEYS.pop(str(session_id), None)
    return len(keys)


def get_session_api_keys(session_id: str | None) -> list[str]:
    if session_id:
        stored = _SESSION_API_KEYS.get(str(session_id))
        if stored:
            return list(stored)
    return parse_api_keys(None)


def set_session_model(session_id: str | None, model: str | None) -> str:
    selected = (model or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    if session_id:
        _SESSION_MODELS[str(session_id)] = selected
    return selected


def get_session_model(session_id: str | None) -> str:
    if session_id:
        return _SESSION_MODELS.get(str(session_id), DEFAULT_GEMINI_MODEL)
    return DEFAULT_GEMINI_MODEL


def clear_session_gemini(session_id: str | None) -> None:
    if session_id:
        _SESSION_API_KEYS.pop(str(session_id), None)
        _SESSION_MODELS.pop(str(session_id), None)


def classify_api_error(exc: Exception) -> str:
    text = str(exc).lower()
    if any(marker in text for marker in _RETRY_MARKERS):
        return "quota"
    if any(marker in text for marker in (
        "api_key_invalid", "api key not valid", "invalid api key",
        "401", "unauthenticated", "403", "permission_denied",
    )):
        return "invalid_key"
    return "fatal"


def available_api_keys(api_keys: str | Iterable[str] | None) -> list[tuple[int, str]]:
    keys = parse_api_keys(api_keys)
    now = time.time()
    ready: list[tuple[int, str]] = []
    cooling: list[tuple[int, str]] = []
    for index, key in enumerate(keys[:MAX_API_KEYS]):
        fingerprint = _fingerprint(key)
        if _KEY_DISABLED_UNTIL.get(fingerprint, 0.0) > now:
            continue
        cooldown_until = _KEY_COOLDOWN.get(fingerprint, 0.0)
        (ready if cooldown_until <= now else cooling).append((index, key))
    return ready or cooling


def mark_api_key_failure(key: str, error_kind: str) -> None:
    fingerprint = _fingerprint(key)
    if error_kind == "quota":
        _KEY_COOLDOWN[fingerprint] = time.time() + 300
    elif error_kind == "invalid_key":
        _KEY_DISABLED_UNTIL[fingerprint] = time.time() + 86400


@dataclass
class AgentResult:
    reply: str
    status: str
    model: str
    key_number: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class GeminiAgent:
    """Gemini agent with a small, whitelisted set of local BukuSuara controls."""

    def __init__(
        self,
        api_keys: str | Iterable[str] | None = None,
        model: str = DEFAULT_GEMINI_MODEL,
        max_remote_calls: int = 3,
        max_output_tokens: int = 900,
    ) -> None:
        self.api_keys = parse_api_keys(api_keys)
        self.model = model or DEFAULT_GEMINI_MODEL
        self.max_remote_calls = max(2, min(int(max_remote_calls), 5))
        self.max_output_tokens = max(128, min(int(max_output_tokens), 2048))

    @staticmethod
    def _compact_history(history: list[dict[str, Any]] | None) -> str:
        if not history:
            return ""
        compact: list[str] = []
        for item in history[-6:]:
            role = str(item.get("role", "user"))
            content = str(item.get("content", ""))[:1800]
            if content:
                compact.append(f"{role}: {content}")
        return "\n".join(compact)

    @staticmethod
    def _session_snapshot(session: Any) -> dict[str, Any]:
        if not session:
            return {}
        keys = (
            "language",
            "tts_engine",
            "output_format",
            "output_channel",
            "output_split",
            "output_split_hours",
            "blocks_preview",
            "device",
            "xtts_speed",
            "ebook_mode",
            "status",
        )
        return {key: session.get(key) for key in keys}

    def _available_keys(self) -> list[tuple[int, str]]:
        return available_api_keys(self.api_keys)

    @staticmethod
    def _error_kind(exc: Exception) -> str:
        return classify_api_error(exc)

    def run(
        self,
        session: Any,
        prompt: str,
        history: list[dict[str, Any]] | None = None,
    ) -> AgentResult:
        prompt = (prompt or "").strip()
        if not prompt:
            return AgentResult(
                reply="Tulis perintah untuk Agen Gemini.",
                status="Tidak ada perintah.",
                model=self.model,
            )
        if not self.api_keys:
            return AgentResult(
                reply=(
                    "API key Gemini belum diisi. Masukkan API key gratis di tab Agen Gemini "
                    "atau set GEMINI_API_KEYS di environment."
                ),
                status="API key belum tersedia.",
                model=self.model,
            )

        def lihat_status_bukusuara() -> str:
            """Lihat setting BukuSuara Studio saat ini tanpa membaca isi buku."""
            return str(self._session_snapshot(session))

        def atur_format_hasil(format_audio: str) -> str:
            """Ubah format output audiobook. Contoh: mp3, m4b, m4a, wav, flac."""
            value = str(format_audio).lower().strip().lstrip(".")
            if value not in output_formats:
                return f"Format tidak didukung. Pilihan: {', '.join(output_formats)}"
            session["output_format"] = value
            return f"Format hasil diubah menjadi {value}."

        def atur_kanal_audio(kanal: str) -> str:
            """Ubah kanal audio menjadi mono atau stereo."""
            value = str(kanal).lower().strip()
            if value not in {"mono", "stereo"}:
                return "Kanal harus mono atau stereo."
            session["output_channel"] = value
            return f"Kanal audio diubah menjadi {value}."

        def atur_pratinjau_bab(aktif: bool) -> str:
            """Aktifkan atau nonaktifkan pratinjau/editor bab sebelum konversi."""
            session["blocks_preview"] = bool(aktif)
            return f"Pratinjau bab {'aktif' if aktif else 'nonaktif'}."

        def atur_kecepatan_xtts(kecepatan: float) -> str:
            """Ubah kecepatan narasi XTTS antara 0.5 sampai 3.0."""
            try:
                value = float(kecepatan)
            except (TypeError, ValueError):
                return "Kecepatan harus berupa angka."
            value = max(0.5, min(3.0, value))
            session["xtts_speed"] = value
            if session.get("tts_engine") != TTS_ENGINES["XTTS"]:
                return (
                    f"Kecepatan XTTS disimpan {value:.2f}, tetapi engine aktif "
                    f"saat ini {session.get('tts_engine')}."
                )
            return f"Kecepatan XTTS diubah menjadi {value:.2f}."

        tools = [
            lihat_status_bukusuara,
            atur_format_hasil,
            atur_kanal_audio,
            atur_pratinjau_bab,
            atur_kecepatan_xtts,
        ]

        system_instruction = (
            "Kamu adalah Agen Gemini di aplikasi BukuSuara Studio, aplikasi pembuat audiobook "
            "yang fokus Bahasa Indonesia. Jawab selalu dalam Bahasa Indonesia yang ringkas dan "
            "operasional. Gunakan tool lokal jika pengguna meminta perubahan setting yang didukung. "
            "Jangan mengaku mengubah setting jika tool tidak dipanggil. Jangan meminta atau "
            "menampilkan API key. Hemat token. Kamu tidak menerima isi buku secara otomatis; "
            "jangan mengarang isi buku. Jika tindakan belum tersedia sebagai tool, jelaskan secara "
            "singkat bahwa fitur kontrol itu belum tersedia dan beri langkah yang bisa dilakukan."
        )

        history_text = self._compact_history(history)
        snapshot = self._session_snapshot(session)
        contents = (
            f"SETTING SAAT INI: {snapshot}\n"
            + (f"RIWAYAT RINGKAS:\n{history_text}\n" if history_text else "")
            + f"PERINTAH PENGGUNA:\n{prompt}"
        )

        last_error: Exception | None = None
        for index, key in self._available_keys():
            try:
                client = genai.Client(api_key=key)
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=tools,
                    temperature=0.2,
                    max_output_tokens=self.max_output_tokens,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        maximum_remote_calls=self.max_remote_calls
                    ),
                )
                chat = client.chats.create(model=self.model, config=config)
                response = chat.send_message(contents)
                reply = (response.text or "").strip() or "Perintah selesai."
                usage = getattr(response, "usage_metadata", None)
                input_tokens = getattr(usage, "prompt_token_count", None) if usage else None
                output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
                status_parts = [
                    f"Model: {self.model}",
                    f"Key aktif: #{index + 1}/{len(self.api_keys)}",
                ]
                if input_tokens is not None or output_tokens is not None:
                    status_parts.append(
                        f"Token: masuk {input_tokens or 0} / keluar {output_tokens or 0}"
                    )
                return AgentResult(
                    reply=reply,
                    status=" • ".join(status_parts),
                    model=self.model,
                    key_number=index + 1,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            except Exception as exc:
                last_error = exc
                error_kind = self._error_kind(exc)
                if error_kind in {"quota", "invalid_key"}:
                    mark_api_key_failure(key, error_kind)
                    continue
                break

        error_text = str(last_error) if last_error else "Kesalahan tidak diketahui."
        if len(error_text) > 320:
            error_text = error_text[:320] + "…"
        return AgentResult(
            reply=(
                "Semua API key Gemini yang tersedia belum berhasil dipakai. Jika key-key "
                "tersebut berasal dari project yang sama, kuotanya memang tetap berbagi."
            ),
            status=f"Gemini error setelah mencoba hingga {len(self.api_keys)} key: {error_text}",
            model=self.model,
        )
