import os
import ast

findings = []

for root, dirs, files in os.walk('.'):
    if any(s in root for s in ['.venv', '__pycache__', '.git', 'staticfiles']):
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
                if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                    # Check if denominator is a constant 0 or variable without guard
                    if isinstance(node.right, ast.Constant) and node.right.value == 0:
                        findings.append((path, node.lineno, "Division by constant 0!"))
                elif isinstance(node, ast.FunctionDef):
                    # Check for clean methods or save methods
                    pass

print(f"Direct division by zero found: {len(findings)}")
for p, l, m in findings:
    print(f"{p}:{l} -> {m}")
