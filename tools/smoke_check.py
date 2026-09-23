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
    if "input_channels == target_channels" not in core_source:
        errors.append("Stream-copy audio masih dapat mengabaikan pilihan mono/stereo")
    if "Unsupported output format:" not in core_source or "Unsupported output channel:" not in core_source:
        errors.append("Core belum memvalidasi format/channel output")
    if "Output split hours must be at least 1." not in core_source or "Invalid output split hours:" not in core_source:
        errors.append("Core belum memvalidasi output_split_hours sebelum proses TTS")
    if "never the active session" not in core_source or "if dir_name in current_user_dirs:" not in core_source:
        errors.append("Cleanup session lama masih berisiko menghapus sesi aktif")
    if "def commit_checksum(" not in core_source or "without committing a changed value prematurely" not in core_source:
        errors.append("Checksum sumber masih berisiko dikomit sebelum parse berhasil")
    if "def ffmeta_escape(" not in core_source:
        errors.append("Metadata FFmpeg belum meng-escape karakter khusus")
    if "published_value = session['metadata'].get('published') or session['metadata'].get('date')" not in core_source:
        errors.append("Exporter metadata belum membaca key date dari schema session")
    if "raw_identifier = session['metadata'].get('identifier')" not in core_source:
        errors.append("Exporter metadata belum membaca identifier EPUB dari schema session")
    if "session['language_iso1'] = args.get('language_iso1')" not in core_source:
        errors.append("ISO1 None masih berisiko berubah menjadi string 'None'")
    if "return _fail(msg)" not in core_source or "return _fail(error)" not in core_source:
        errors.append("Finalize masih bisa meninggalkan status CONVERTING setelah pembatalan/error awal")
    if "clean_title = ffmeta_escape(" not in core_source:
        errors.append("Judul chapter FFmpeg belum memakai escaping metadata yang konsisten")
    if "def ffconcat_quote_path(" not in core_source or "def ffconcat_unquote_path(" not in core_source:
        errors.append("Path FFmpeg concat belum aman untuk apostrof")
    if core_source.count('f.write(f"file {ffconcat_quote_path(path)}') < 3:
        errors.append("Semua generator FFmpeg concat belum memakai path quoting aman")
    if "Metadata generation failed for part" not in core_source or "Metadata generation failed." not in core_source:
        errors.append("Kegagalan metadata FFmpeg masih bisa diteruskan ke tahap export")
    if "should_stop=lambda: bool(session.get('cancellation_requested'))" not in core_source:
        errors.append("FFmpeg merge/export belum terhubung ke cancellation session")
    if "def preprocess_gemini_pronunciation(" not in core_source:
        errors.append("Pipeline DOCX/TXT belum terhubung ke Gemini pronunciation")
    if "def disambiguate_directory_ebook_name(" not in core_source:
        errors.append("Directory Mode belum melindungi cache/output dari stem ebook yang sama")
    if "Ebook source is not a readable file." not in core_source:
        errors.append("Core masih bisa menerima directory sebagai ebook source")
    if "ebook_name = disambiguate_directory_ebook_name" not in core_source:
        errors.append("Disambiguasi nama Directory Mode belum terhubung ke convert_ebook")
    if "def session_has_active_client(" not in core_source:
        errors.append("Sesi GUI belum punya guard untuk client aktif ganda")
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
    if "authoritative queue in the session" not in app_source:
        errors.append("Headless Directory Mode belum menyinkronkan ebook_list ke session")
    if "The provided --custom_model" not in app_source:
        errors.append("Headless custom model belum divalidasi sebelum konversi")
    if "--output_dir must be an existing directory" not in app_source:
        errors.append("Headless output_dir belum divalidasi sebagai directory")
    if "choices=output_formats" not in app_source or "choices=['mono', 'stereo']" not in app_source:
        errors.append("Argumen headless format/channel belum dibatasi")
    if "voice_map_dir = os.path.dirname(voice_map_path)" not in app_source:
        errors.append("Relative voice_map voice path belum dipatok ke lokasi JSON")
    if "elif not error and args.get('ebook'" not in app_source:
        errors.append("Headless source branch masih bisa lanjut setelah validasi gagal")
    if "standalone/static FFmpeg" not in app_source or "if ffmpeg and ffprobe:" not in app_source:
        errors.append("Startup Windows masih menolak FFmpeg standalone/static")
    if "APP_ROOT = Path(__file__).resolve().parent" not in app_source:
        errors.append("Asset GUI masih berisiko bergantung pada working directory")
    if "favicon_value = str(favicon_file) if favicon_file.is_file() else None" not in app_source:
        errors.append("GUI belum aman ketika favicon.ico tidak tersedia")
    if "0.0.0.0 is a bind address" not in app_source or "127.0.0.1" not in app_source:
        errors.append("Deteksi port GUI masih memakai target connect yang tidak reliabel")

    gradio_source = Path("lib/gradio.py").read_text(encoding="utf-8")
    if "Missing voice must not invalidate the selected ebook." not in gradio_source:
        errors.append("Restore session masih berisiko menghapus ebook_src ketika voice hilang")
    if "The process copy may be cleaned while the original source still exists." not in gradio_source:
        errors.append("Restore session masih berisiko menghapus source asli saat cache ebook hilang")
    if "data = data if isinstance(data, Mapping) else {}" not in gradio_source:
        errors.append("Restore session belum aman saat data awal None/tidak valid")
    if "requested_session_id = data.get('id')" not in gradio_source or "session_has_active_client(existing_session" not in gradio_source:
        errors.append("Restore session masih dapat menimpa sesi yang aktif di tab lain")
    if "seen_paths = set()" not in gradio_source:
        errors.append("GUI Directory Mode belum mencegah ebook path duplikat")
    if "'error': str(e)" not in gradio_source:
        errors.append("Autosave session masih mencoba menyerialisasi object Exception mentah")
    if "classes = list(attr) if attr is not None" not in gradio_source:
        errors.append("Glassmask UI masih memakai mutable default list")
    if "if not os.path.exists(session['custom_model']):" not in gradio_source:
        errors.append("Restore session belum memvalidasi path custom model secara langsung")

    for engine_source in (
        "lib/classes/tts_engines/fairseq.py",
        "lib/classes/tts_engines/vits.py",
        "lib/classes/tts_engines/piper.py",
    ):
        engine_text = Path(engine_source).read_text(encoding="utf-8")
        if "ZeroShot voice-conversion is expensive" not in engine_text or "self.engine_zs = None" not in engine_text:
            errors.append(f"{engine_source}: ZeroShot model masih dimuat eager")
        if "self.engine_zs = self._load_engine_zs(self.device)" not in engine_text:
            errors.append(f"{engine_source}: lazy ZeroShot loader tidak terhubung saat cloning dibutuhkan")
        if "def _refresh_voice_mode()->bool:" not in engine_text or "use_zs = _refresh_voice_mode()" not in engine_text:
            errors.append(f"{engine_source}: mode cloning belum dihitung ulang setelah inline voice berubah")
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

    subprocess_source = Path("lib/classes/subprocess_pipe.py").read_text(encoding="utf-8")
    if "def _cancellation_requested(" not in subprocess_source or "self.stop()" not in subprocess_source:
        errors.append("SubprocessPipe belum dapat menghentikan proses saat cancel")
    if "executable_name = os.path.basename(str(self.cmd[0])).lower()" not in subprocess_source:
        errors.append("Deteksi executable FFmpeg masih case-sensitive di Windows")
    if "self.process.wait(timeout=2)" not in subprocess_source:
        errors.append("SubprocessPipe terminate belum punya fallback kill")

    browser_helper_path = Path(".bh.ps1")
    if not browser_helper_path.is_file():
        errors.append("Helper browser Windows .bh.ps1 belum tersedia")
        browser_helper_source = ""
    else:
        browser_helper_source = browser_helper_path.read_text(encoding="utf-8", errors="ignore")
        if "ConnectAsync" not in browser_helper_source or "TimeoutSeconds" not in browser_helper_source:
            errors.append("Helper browser belum menunggu server dengan timeout")

    launcher_source = Path("ebook2audiobook.cmd").read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n")
    if 'where.exe /Q python >nul 2>&1' not in launcher_source:
        errors.append("Launcher Windows masih memanggil Python sebelum bootstrap")
    if ':check_scoop_buckets\nsetlocal EnableDelayedExpansion' not in launcher_source:
        errors.append("Pemeriksaan Scoop bucket belum mengaktifkan delayed expansion")
    if ':check_programs\nsetlocal EnableDelayedExpansion\nset "missing_prog_array="' not in launcher_source:
        errors.append("Pemeriksaan dependency Windows belum mereset daftar paket yang hilang")
    if 'Portable mode: never create Start Menu/Desktop shortcuts' not in launcher_source:
        errors.append("Launcher GUI masih memiliki side-effect installer pada mode portable")
    if 'if /i "%HEADLESS_FOUND%"=="%ARGS%" (' not in launcher_source:
        errors.append("Deteksi --headless launcher masih terbalik")
    if 'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall' in launcher_source:
        errors.append("Launcher portable masih menulis registry uninstall")
    if ':make_shortcut' in launcher_source:
        errors.append("Launcher portable masih membuat shortcut sistem")
    if "reg add HKCU\\Console" in launcher_source:
        errors.append("Launcher portable masih mengubah HKCU\\Console")
    if 'set "HOST_PROGRAMS=cmake rustup calibre ffmpeg-shared' in launcher_source:
        errors.append("Launcher masih memaksa ffmpeg-shared walau static FFmpeg didukung")
    if 'set "PORTABLE_BIN=%SAFE_SCRIPT_DIR%\\tools\\bin"' not in launcher_source:
        errors.append("Launcher belum memprioritaskan tool portable lokal")
    if 'ifi "%PODMAN_DESKTOP%"=="0"' in launcher_source:
        errors.append("Launcher masih memiliki typo perintah 'ifi' pada jalur help")
    if 'supported range is %MIN_PYTHON_VERSION% through %MAX_PYTHON_VERSION%' not in launcher_source:
        errors.append("Launcher belum menolak Python di atas MAX_PYTHON_VERSION")
    if "-RunAsAdmin" in launcher_source:
        errors.append("Launcher fallback Scoop masih meminta RunAsAdmin")
    if "SetEnvironmentVariable('Path',$np,'User')" in launcher_source:
        errors.append("Launcher portable masih menulis PATH permanen ke user profile")
    if ":restart_script_admin" in launcher_source:
        errors.append("Launcher portable masih menyimpan jalur restart admin yang tidak dipakai")
    if 'set "RUNTIME_PROGRAMS=calibre ffmpeg mediainfo espeak-ng sox tesseract"' not in launcher_source:
        errors.append("Launcher belum memisahkan runtime dan bootstrap tools")
    if 'if "!PROVISIONED_VERSION!"=="%APP_VERSION%" set "program_list=%RUNTIME_PROGRAMS%"' not in launcher_source:
        errors.append("Launcher masih mengecek build tools pada env yang sudah current")
    if 'if not "%PROVISIONED_VERSION%"=="%APP_VERSION%" (' not in launcher_source:
        errors.append("Versi .provisioned belum dipakai untuk reprovision dependency")
    if 'if exist "%SAFE_SCRIPT_DIR%\\%PYTHON_ENV%" if not exist "%SAFE_SCRIPT_DIR%\\%PYTHON_ENV%\\.provisioned" (' not in launcher_source:
        errors.append("Env tanpa .provisioned tidak lagi direcreate dengan aman")

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
