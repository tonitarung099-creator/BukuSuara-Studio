from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def probe_title(ffprobe: str, path: Path) -> str | None:
    result = run([
        ffprobe,
        "-v", "error",
        "-show_entries", "format_tags=title",
        "-of", "json",
        str(path),
    ])
    data = json.loads(result.stdout or "{}")
    return (data.get("format", {}).get("tags", {}) or {}).get("title")


def main() -> int:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        print("SKIP: ffmpeg/ffprobe tidak tersedia.")
        return 0

    title = "Buku = Tes; #1"
    with tempfile.TemporaryDirectory(prefix="bukusuara-audio-smoke-") as td:
        root = Path(td)
        src = root / "source.flac"
        meta = root / "metadata.txt"
        meta.write_text(
            ";FFMETADATA1\n"
            "title=Buku \\= Tes\\; \\#1\n"
            "artist=BukuSuara Studio\n",
            encoding="utf-8",
        )

        run([
            ffmpeg, "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-ar", "24000", "-ac", "1",
            "-c:a", "flac", "-y", str(src),
        ])

        outputs: dict[str, list[str]] = {
            "flac": [
                ffmpeg, "-hide_banner", "-loglevel", "error",
                "-i", str(src),
                "-f", "ffmetadata", "-i", str(meta),
                "-map", "0:a",
                "-c:a", "flac", "-compression_level", "5", "-ar", "44100",
                "-map_metadata", "1",
                "-y", str(root / "out.flac"),
            ],
            "wav": [
                ffmpeg, "-hide_banner", "-loglevel", "error",
                "-i", str(src),
                "-f", "ffmetadata", "-i", str(meta),
                "-map", "0:a",
                "-ar", "44100", "-sample_fmt", "s16",
                "-map_metadata", "1",
                "-y", str(root / "out.wav"),
            ],
            "aac": [
                ffmpeg, "-hide_banner", "-loglevel", "error",
                "-i", str(src),
                "-f", "ffmetadata", "-i", str(meta),
                "-map", "0:a",
                "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
                "-map_metadata", "1",
                "-write_id3v2", "1",
                "-y", str(root / "out.aac"),
            ],
        }

        failures: list[str] = []
        for fmt, cmd in outputs.items():
            out = root / f"out.{fmt}"
            try:
                run(cmd)
                actual = probe_title(ffprobe, out)
                if actual != title:
                    failures.append(f"{fmt}: title={actual!r}, expected={title!r}")
            except subprocess.CalledProcessError as exc:
                failures.append(f"{fmt}: ffmpeg/ffprobe gagal: {exc.stderr.strip()}")

        if failures:
            print("BukuSuara audio metadata smoke: GAGAL")
            for failure in failures:
                print(f"- {failure}")
            return 1

    print("BukuSuara audio metadata smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
