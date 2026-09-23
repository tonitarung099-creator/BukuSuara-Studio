from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "lib" / "gradio.py"


def find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def find_list_assignment(tree: ast.AST, name: str) -> ast.List | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                if isinstance(node.value, ast.List):
                    return node.value
    return None


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    checks = [
        ("_start_conversion", "inputs_start_conversion"),
        ("_run_gemini_agent", "gemini_inputs"),
    ]
    errors: list[str] = []
    for function_name, input_name in checks:
        fn = find_function(tree, function_name)
        inputs = find_list_assignment(tree, input_name)
        if fn is None:
            errors.append(f"Callback tidak ditemukan: {function_name}")
            continue
        if inputs is None:
            errors.append(f"Daftar input tidak ditemukan: {input_name}")
            continue
        parameter_count = len(fn.args.posonlyargs) + len(fn.args.args)
        input_count = len(inputs.elts)
        if parameter_count != input_count:
            errors.append(
                f"{function_name}: parameter={parameter_count}, input Gradio={input_count}"
            )

    if errors:
        print("Callback audit: GAGAL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Callback audit: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
