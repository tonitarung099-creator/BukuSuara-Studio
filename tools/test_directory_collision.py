from pathlib import Path
import ast
import hashlib
import os
import re


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "lib" / "core.py"


def get_sanitized(value: str) -> str:
    value = re.sub(r"[^\w.-]+", "_", str(value), flags=re.UNICODE)
    return value.strip("._") or "file"


def strip_invalid_filename_characters(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", str(value)).strip()


class EbookModes:
    DIRECTORY = "directory"


ebook_modes = {"DIRECTORY": EbookModes.DIRECTORY}


def load_function():
    source = CORE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "disambiguate_directory_ebook_name"
    )
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {
        "Any": object,
        "Path": Path,
        "os": os,
        "hashlib": hashlib,
        "ebook_modes": ebook_modes,
        "get_sanitized": get_sanitized,
        "strip_invalid_filename_characters": strip_invalid_filename_characters,
    }
    exec(compile(module, str(CORE), "exec"), namespace)
    return namespace["disambiguate_directory_ebook_name"]


class ProxyLike:
    def __init__(self, values):
        self.values = list(values)

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)


def main() -> None:
    disambiguate = load_function()
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

    a = disambiguate(session, "Buku", files[0], files)
    b = disambiguate(session, "Buku", files[1], files)
    c = disambiguate(session, "Buku", files[2], files)
    d = disambiguate(session, "Lain", files[3], files)

    # Even if the live session queue shrinks, the original batch must keep
    # collision naming stable for later books.
    session["ebook_list"] = ProxyLike([files[2], files[3]])
    c_after_shrink = disambiguate(session, "Buku", files[2], files)

    assert a.startswith("Buku_docx_"), a
    assert c.startswith("Buku_docx_"), c
    assert a != c, (a, c)
    assert c_after_shrink == c, (c_after_shrink, c)
    assert b == "Buku_txt", b
    assert d == "Lain", d
    print("Directory collision logic: OK")


if __name__ == "__main__":
    main()
