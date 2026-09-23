from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "lib" / "gradio.py"


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    errors: list[str] = []

    required = [
        "BukuSuara responsive safety",
        "@media (max-width: 1000px)",
        "@media (max-width: 700px)",
        "gr_row_gemini_config",
        "gr_row_gemini_prompt",
        "gr_gemini_send",
        ".no-wrap",
        "flex-wrap: wrap !important",
    ]
    for needle in required:
        if needle not in text:
            errors.append(f"Responsive UI marker hilang: {needle}")

    occurrences: dict[str, list[int]] = {}
    for match in re.finditer(r"elem_id\s*=\s*['\"]([^'\"]+)['\"]", text):
        before = text[max(0, match.start() - 100):match.start()]
        if "gr.update(" in before:
            continue
        occurrences.setdefault(match.group(1), []).append(match.start())

    duplicates = {key: pos for key, pos in occurrences.items() if len(pos) > 1}
    if duplicates:
        errors.append(f"Duplicate elem_id: {', '.join(sorted(duplicates))}")

    gemini_section_start = text.find("with gr.Tab('🤖 Agen Gemini'")
    gemini_section_end = text.find("gr_blocks_page =", gemini_section_start)
    if gemini_section_start < 0 or gemini_section_end < 0:
        errors.append("Tab Agen Gemini tidak ditemukan")
    else:
        section = text[gemini_section_start:gemini_section_end]
        for required_id in (
            "gr_row_gemini_config",
            "gr_col_gemini_keys",
            "gr_gemini_model",
            "gr_row_gemini_prompt",
            "gr_gemini_send",
        ):
            if required_id not in section:
                errors.append(f"Komponen Gemini tanpa selector responsif: {required_id}")

    if errors:
        print("BukuSuara UI audit: GAGAL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("BukuSuara UI audit: OK")
    print(f"Literal elem_id unik: {len(occurrences)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
