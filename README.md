# BukuSuara Studio

**BukuSuara Studio** adalah aplikasi pembuat audiobook yang difokuskan untuk Bahasa Indonesia.

Proyek ini menggunakan `DrewThomasson/ebook2audiobook` sebagai fondasi teknis karena sudah menyediakan pemrosesan e-book, chapter, metadata, banyak engine TTS, voice cloning, dan export audiobook. Kode upstream menggunakan lisensi Apache-2.0.

## Target BukuSuara Studio

- Bahasa Indonesia sebagai bahasa utama aplikasi dan TTS.
- Import EPUB, PDF, DOCX, TXT, MOBI, dan format buku lain.
- Deteksi dan pengelolaan bab.
- Preview dan generate audio per bab.
- Voice cloning opsional.
- Export MP3, M4B, WAV, M4A, dan format audio lain.
- Alur penggunaan sederhana untuk pengguna Windows.
- Distribusi akhir berupa **portable folder multi-file dalam ZIP**: extract lalu jalankan, tanpa installer wajib.
- Model/runtime/data ditempatkan terstruktur agar folder aplikasi dapat dipindah.

## Status

Fondasi core upstream sudah diimpor. Tahap berikutnya adalah:
1. audit runtime Windows,
2. memilih engine suara Indonesia terbaik,
3. mengubah default bahasa ke Indonesia,
4. merombak UI,
5. membuat sistem portable Windows,
6. menguji proses buku -> chapter -> audio -> export.

## Upstream

- Repository: https://github.com/DrewThomasson/ebook2audiobook
- License: Apache License 2.0
- Upstream tree saat basis diambil: `3a56c25c5c839306f765bcf0334b5af078e66684`

Dokumentasi asli disimpan di `docs/UPSTREAM_README.md`.
