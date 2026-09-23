from pathlib import Path
import sys
import py_compile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.conf_lang import default_language_code
from lib.conf_models import default_tts_engine, default_engine_settings


def main() -> int:
    errors = []

    supported = default_engine_settings.get(default_tts_engine, {}).get("languages", {})
    if default_language_code not in supported:
        errors.append(
            f"Default tidak kompatibel: bahasa={default_language_code}, engine={default_tts_engine}"
        )

    for source in ("lib/classes/gemini_agent.py", "lib/gradio.py"):
        try:
            py_compile.compile(source, doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"Syntax error {source}: {exc.msg}")

    gemini_source = Path("lib/classes/gemini_agent.py").read_text(encoding="utf-8")
    if "MAX_API_KEYS = 100" not in gemini_source:
        errors.append("Gemini agent belum membatasi maksimal 100 API key")
    if "time.time() + 300" not in gemini_source:
        errors.append("Gemini agent belum memiliki cooldown rotasi key limit")

    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    if "./ext/py/demucs" in requirements:
        errors.append("requirements.txt masih memakai dependency Demucs lokal yang tidak portable")

    for required in ("demucs==4.1.0", "psutil", "Pillow", "markdown", "uvicorn", "google-genai"):
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
