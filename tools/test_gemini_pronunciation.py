from pathlib import Path
from tempfile import TemporaryDirectory
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.classes.gemini_agent import (
    MAX_API_KEYS,
    available_api_keys,
    mark_api_key_failure,
    parse_api_keys,
)
from lib.classes.gemini_pronunciation import (
    GeminiPronunciationProcessor,
    PRONUNCIATION_MAX_OUTPUT_TOKENS,
)


def main() -> None:
    assert PRONUNCIATION_MAX_OUTPUT_TOKENS >= 4096
    keys = [f"key-{i:03d}" for i in range(105)]
    parsed = parse_api_keys(",".join(keys))
    assert len(parsed) == MAX_API_KEYS == 100

    # A limited key must not be retried immediately; the next ready key is used.
    limited, ready = parsed[0], parsed[1]
    mark_api_key_failure(limited, "quota")
    available = available_api_keys([limited, ready])
    assert available == [(1, ready)], "cooldown must prevent immediate reuse of limited key"

    with TemporaryDirectory() as tmp:
        processor = GeminiPronunciationProcessor("ci-test", tmp)
        source = [
            "George pergi ke Greenwich. Ia membuka YouTube menggunakan Microsoft Edge.",
            "George lalu kembali ke rumah tanpa mengubah isi cerita.",
        ]
        candidates = processor.collect_candidates(source)
        for term in ("George", "Greenwich", "YouTube"):
            assert term in candidates, f"kandidat asing tidak terdeteksi: {term}"

        processor.cache = {
            "George": "Jorj",
            "Greenwich": "Grenij",
            "YouTube": "Yu-tub",
            "Microsoft Edge": "Mai-kro-soft Ej",
        }
        processor.reviewed = set(candidates)
        processor.reviewed_context = {
            term: processor._context_fingerprint(context)
            for term, context in candidates.items()
        }
        processed = processor.apply_dictionary(source)
        assert "Jorj pergi ke Grenij" in processed[0]
        assert "Yu-tub" in processed[0]
        assert "rumah tanpa mengubah isi cerita" in processed[1]

        processor.cache = {"George": "Jorj", "Jorj": "Yor"}
        collision = processor.apply_dictionary(["George bertemu Jorj."])[0]
        assert collision == "Jorj bertemu Yor.", "replacement must be atomic, not recursive"

        processor.cache = {
            "George": "Jorj",
            "Greenwich": "Grenij",
            "YouTube": "Yu-tub",
            "Microsoft Edge": "Mai-kro-soft Ej",
        }

        processor._save_cache()
        assert Path(tmp, "gemini_pronunciation_map.json").exists()
        restored = GeminiPronunciationProcessor("ci-test", tmp)
        assert restored.cache["George"] == "Jorj"
        assert "George" in restored.reviewed
        assert restored.reviewed_context["George"] == processor.reviewed_context["George"]

        changed_context = "George Washington berbicara di acara berbeda."
        old_fingerprint = restored.reviewed_context["George"]
        new_fingerprint = restored._context_fingerprint(restored._context(changed_context, "George"))
        assert old_fingerprint != new_fingerprint, "context fingerprint must detect changed usage"

        stale_payload = {
            "version": 1,
            "aliases": {"George": "Alias-Lama"},
            "reviewed": ["George"],
            "reviewed_context": {"George": "deadbeef"},
        }
        cache_path = Path(tmp, "gemini_pronunciation_map.json")
        cache_path.write_text(__import__("json").dumps(stale_payload), encoding="utf-8")
        stale = GeminiPronunciationProcessor("ci-test", tmp)
        assert stale.cache == {}, "old pronunciation cache version must be invalidated"
        assert not stale.reviewed
        assert not stale.reviewed_context

    print("Gemini pronunciation logic: OK")


if __name__ == "__main__":
    main()
