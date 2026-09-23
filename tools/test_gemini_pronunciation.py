from pathlib import Path
from tempfile import TemporaryDirectory

from lib.classes.gemini_agent import MAX_API_KEYS, parse_api_keys
from lib.classes.gemini_pronunciation import GeminiPronunciationProcessor


def main() -> None:
    keys = [f"key-{i:03d}" for i in range(105)]
    assert len(parse_api_keys(",".join(keys))) == MAX_API_KEYS == 100

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
        processed = processor.apply_dictionary(source)
        assert "Jorj pergi ke Grenij" in processed[0]
        assert "Yu-tub" in processed[0]
        assert "rumah tanpa mengubah isi cerita" in processed[1]

        processor._save_cache()
        assert Path(tmp, "gemini_pronunciation_map.json").exists()
        restored = GeminiPronunciationProcessor("ci-test", tmp)
        assert restored.cache["George"] == "Jorj"
        assert "George" in restored.reviewed

    print("Gemini pronunciation logic: OK")


if __name__ == "__main__":
    main()
