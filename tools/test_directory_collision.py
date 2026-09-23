from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.core import disambiguate_directory_ebook_name, ebook_modes


class ProxyLike:
    def __init__(self, values):
        self.values = list(values)
    def __iter__(self):
        return iter(self.values)
    def __len__(self):
        return len(self.values)


def main() -> None:
    files = [
        "/books/Buku.docx",
        "/books/Buku.txt",
        "/other/Buku.docx",
        "/books/Lain.docx",
    ]
    session = {
        "ebook_mode": ebook_modes["DIRECTORY"],
        "ebook_list": ProxyLike(files),
    }

    a = disambiguate_directory_ebook_name(session, "Buku", files[0])
    b = disambiguate_directory_ebook_name(session, "Buku", files[1])
    c = disambiguate_directory_ebook_name(session, "Buku", files[2])
    d = disambiguate_directory_ebook_name(session, "Lain", files[3])

    assert a.startswith("Buku_docx_"), a
    assert c.startswith("Buku_docx_"), c
    assert a != c, (a, c)
    assert b == "Buku_txt", b
    assert d == "Lain", d
    print("Directory collision logic: OK")


if __name__ == "__main__":
    main()
