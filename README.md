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


## Agen AI Gemini

BukuSuara Studio memiliki tab **🤖 Agen Gemini** yang dirancang untuk API Gemini Free Tier.

Fitur awal agent:
- chat Bahasa Indonesia di dalam aplikasi;
- membaca setting ringkas BukuSuara tanpa membaca isi buku secara otomatis;
- mengubah format output (MP3/M4B/WAV/dll.);
- mengubah kanal mono/stereo;
- mengaktifkan/nonaktifkan pratinjau bab;
- mengubah kecepatan XTTS;
- menampilkan model, key aktif, dan penggunaan token bila metadata tersedia;
- mendukung beberapa API key dan pindah key pada error kuota/server yang dapat dicoba ulang.

Default model: `gemini-3.5-flash-lite`.

### API key

Masukkan API key langsung pada tab Agen Gemini. Beberapa key dapat dipisahkan dengan koma, titik koma, atau baris baru. Key tidak dimasukkan ke session audiobook dan tidak disimpan ke repository.

Alternatif untuk pemakaian lokal adalah environment variable:

```text
GEMINI_API_KEY=AIza...
```

atau:

```text
GEMINI_API_KEYS=AIza_key1,AIza_key2,AIza_key3
```

**Catatan kuota:** rate limit Gemini berlaku per Google Cloud/AI Studio project, bukan per API key. Banyak key dari project yang sama tidak menambah kuota project.

### Hemat Free Tier

Agent membatasi automatic function-calling agar satu perintah tidak membuat rantai request yang terlalu panjang. Riwayat chat yang dikirim juga dipotong. File/isi buku tidak dikirim otomatis; hanya perintah yang diketik pengguna, riwayat chat ringkas, dan setting aplikasi. Jika ingin meminta Gemini memproses isi buku, fitur tersebut harus dibuat sebagai tindakan eksplisit agar penggunaan token dapat dikontrol.
