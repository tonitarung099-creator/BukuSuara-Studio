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

    for source in (
        "lib/classes/gemini_agent.py",
        "lib/classes/gemini_pronunciation.py",
        "lib/core.py",
        "lib/gradio.py",
    ):
        try:
            py_compile.compile(source, doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"Syntax error {source}: {exc.msg}")

    gemini_source = Path("lib/classes/gemini_agent.py").read_text(encoding="utf-8")
    pronunciation_source = Path("lib/classes/gemini_pronunciation.py").read_text(encoding="utf-8")
    core_source = Path("lib/core.py").read_text(encoding="utf-8")
    if "existing_model_path" not in core_source or "existing_valid" not in core_source:
        errors.append("Custom model cache belum memvalidasi folder hasil ekstraksi")
    if "runtime_model_files" not in core_source or "cached_voice" not in core_source:
        errors.append("Custom model cache belum mendukung reuse setelah ref.wav dinormalisasi")
    if "Duplicate required filenames in ZIP are not allowed" not in core_source:
        errors.append("Custom model ZIP belum menolak required filename yang ambigu")
    if "Headless/CLI custom_model" not in core_source:
        errors.append("Custom model headless masih berisiko menghapus ZIP asli pengguna")
    if "progress_bar(t.n / files_length" not in core_source:
        errors.append("Progress ekstraksi custom model masih berisiko melewati 100%")
    if "Missing required audio tool(s)" not in core_source:
        errors.append("Export audio belum memvalidasi ffmpeg/ffprobe sebelum subprocess")
    if "never the active session" not in core_source or "if dir_name in current_user_dirs:" not in core_source:
        errors.append("Cleanup session lama masih berisiko menghapus sesi aktif")
    if "def commit_checksum(" not in core_source or "without committing a changed value prematurely" not in core_source:
        errors.append("Checksum sumber masih berisiko dikomit sebelum parse berhasil")
    if "def preprocess_gemini_pronunciation(" not in core_source:
        errors.append("Pipeline DOCX/TXT belum terhubung ke Gemini pronunciation")
    if "cover_result is not False" not in core_source:
        errors.append("Buku tanpa cover masih berisiko menghentikan konversi")
    if "isinstance(session.get('cover'), str) and os.path.isfile(session['cover'])" not in core_source:
        errors.append("Cover export belum memvalidasi path file")
    if "MAX_TERMS_PER_REQUEST = 60" not in pronunciation_source:
        errors.append("Batch pronunciation Gemini belum dibatasi")
    if '"reviewed": sorted(self.reviewed)' not in pronunciation_source:
        errors.append("Cache keputusan pronunciation belum menyimpan istilah yang sudah diperiksa")
    if '"reviewed_context": dict(sorted(self.reviewed_context.items()))' not in pronunciation_source:
        errors.append("Cache pronunciation belum melacak perubahan konteks istilah")
    if "MAX_API_KEYS = 100" not in gemini_source:
        errors.append("Gemini agent belum membatasi maksimal 100 API key")
    if "time.time() + 300" not in gemini_source:
        errors.append("Gemini agent belum memiliki cooldown rotasi key limit")

    conf_source = Path("lib/conf.py").read_text(encoding="utf-8")
    if "Portable runtime directories must exist" not in conf_source:
        errors.append("Startup belum membuat folder runtime portable secara otomatis")
    if "os.makedirs(runtime_dir, exist_ok=True)" not in conf_source:
        errors.append("Folder runtime portable belum dibuat secara defensif")
    if "_project_dir = os.path.dirname(_lib_dir)" not in conf_source:
        errors.append("Path portable belum dipatok ke lokasi aplikasi")
    if "open(os.path.join(_project_dir, 'VERSION.txt')" not in conf_source:
        errors.append("VERSION.txt masih bergantung pada working directory")

    app_source = Path("app.py").read_text(encoding="utf-8")
    if "name.lower().endswith(str(ext).lower())" not in app_source:
        errors.append("Headless Directory Mode masih case-sensitive untuk ekstensi ebook")
    if "The provided --custom_model" not in app_source:
        errors.append("Headless custom model belum divalidasi sebelum konversi")
    if "--output_dir must be an existing directory" not in app_source:
        errors.append("Headless output_dir belum divalidasi sebagai directory")
    if "elif not error and args.get('ebook'" not in app_source:
        errors.append("Headless source branch masih bisa lanjut setelah validasi gagal")
    if "standalone/static FFmpeg" not in app_source or "if ffmpeg and ffprobe:" not in app_source:
        errors.append("Startup Windows masih menolak FFmpeg standalone/static")

    gradio_source = Path("lib/gradio.py").read_text(encoding="utf-8")
    if "Missing voice must not invalidate the selected ebook." not in gradio_source:
        errors.append("Restore session masih berisiko menghapus ebook_src ketika voice hilang")
    if "The process copy may be cleaned while the original source still exists." not in gradio_source:
        errors.append("Restore session masih berisiko menghapus source asli saat cache ebook hilang")
    if "data = data if isinstance(data, Mapping) else {}" not in gradio_source:
        errors.append("Restore session belum aman saat data awal None/tidak valid")
    if "if not os.path.exists(session['custom_model']):" not in gradio_source:
        errors.append("Restore session belum memvalidasi path custom model secara langsung")

    for engine_source in (
        "lib/classes/tts_engines/fairseq.py",
        "lib/classes/tts_engines/vits.py",
        "lib/classes/tts_engines/piper.py",
    ):
        engine_text = Path(engine_source).read_text(encoding="utf-8")
        if "if semitones > 0:" in engine_text:
            errors.append(f"{engine_source}: pitch negatif masih diabaikan")
        if "SoX is required for voice pitch adaptation" not in engine_text:
            errors.append(f"{engine_source}: dependency SoX belum divalidasi")
        if "check=True" not in engine_text:
            errors.append(f"{engine_source}: kegagalan SoX masih bisa lolos diam-diam")

    device_installer_source = Path("lib/classes/device_installer.py").read_text(encoding="utf-8")
    if "DEVICE_INSTALLER_ROOT = Path(__file__).resolve().parents[2]" not in device_installer_source:
        errors.append("DeviceInstaller masih bergantung pada working directory")
    if "DEVICE_INSTALLER_ROOT / 'voices'" not in device_installer_source:
        errors.append("Bootstrap voice belum dipatok ke folder aplikasi")
    if "DEVICE_INSTALLER_ROOT / 'detect_gpus.py'" not in device_installer_source:
        errors.append("GPU probe masih mencari detect_gpus.py dari working directory")
    if "Unsafe voice ZIP path" not in device_installer_source:
        errors.append("Ekstraksi ZIP voice belum melindungi path traversal")

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
