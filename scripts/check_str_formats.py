import os
import ast
import re

issues = []

for root, dirs, files in os.walk('.'):
    if any(s in root for s in ['.venv', '__pycache__', '.git', 'staticfiles', 'scripts']):
        continue
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                lines = fp.readlines()
                try:
                    tree = ast.parse("".join(lines), filename=path)
                except Exception:
                    continue
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == '__str__':
                    for n in ast.walk(node):
                        if isinstance(n, ast.JoinedStr):
                            # f-string in __str__
                            line_text = lines[n.lineno - 1].strip() if n.lineno <= len(lines) else ""
                            if re.search(r'\{[^}]*:[^}]*\}', line_text):
                                issues.append((path, n.lineno, line_text))

for p, l, t in issues:
    msg = f"{p}:{l} -> {t}".encode('ascii', errors='replace').decode('ascii')
    print(msg)
print(f"Total f-string format specifiers in __str__: {len(issues)}")
