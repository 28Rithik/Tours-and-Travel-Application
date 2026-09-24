import os
import ast
import re

issues = []

for root, dirs, files in os.walk('.'):
    if any(skip in root for skip in ['.venv', '__pycache__', '.git', 'staticfiles']):
        continue
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                try:
                    tree = ast.parse(fp.read(), filename=path)
                except Exception:
                    continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr
                    if func_name == 'format_html':
                        if len(node.args) < 2:
                            issues.append((path, node.lineno, "format_html with < 2 args"))
                        elif isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                            if re.search(r'\{[^}]*:[^}]*\}', node.args[0].value):
                                issues.append((path, node.lineno, f"format_html format specifier: {repr(node.args[0].value[:60])}"))

for p, l, m in issues:
    print(f"{p}:{l} -> {m}".encode('ascii', errors='replace').decode('ascii'))
print(f"Total issues: {len(issues)}")
