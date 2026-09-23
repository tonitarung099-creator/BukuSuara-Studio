from pathlib import Path

from lib.conf_lang import default_language_code
from lib.conf_models import default_tts_engine, default_engine_settings


def main() -> int:
    errors = []

    supported = default_engine_settings.get(default_tts_engine, {}).get("languages", {})
    if default_language_code not in supported:
        errors.append(
            f"Default tidak kompatibel: bahasa={default_language_code}, engine={default_tts_engine}"
        )

    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    if "./ext/py/demucs" in requirements:
        errors.append("requirements.txt masih memakai dependency Demucs lokal yang tidak portable")

    for required in ("demucs==4.1.0", "psutil", "Pillow", "markdown", "uvicorn"):
        if required.lower() not in requirements.lower():
            errors.append(f"Dependency wajib belum ada: {required}")

    if errors:
        print("BukuSuara Studio smoke check: GAGAL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("BukuSuara Studio smoke check: OK")
    print(f"Bahasa default : {default_language_code}")
    print(f"Engine default : {default_tts_engine}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
