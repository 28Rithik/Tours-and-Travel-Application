import os
import ast

divisions = []

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
                if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv)):
                    line_text = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
                    divisions.append((path, node.lineno, line_text))

for p, l, t in divisions:
    msg = f"{p}:{l} -> {t}".encode('ascii', errors='replace').decode('ascii')
    print(msg)
print(f"Total divisions: {len(divisions)}")
