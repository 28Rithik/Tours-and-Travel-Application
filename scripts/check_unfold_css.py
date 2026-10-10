import re

with open('staticfiles/unfold/css/styles.css', 'r', encoding='utf-8', errors='ignore') as f:
    css = f.read()

# Check td, th, table, result-list rules
matches = re.findall(r'([^}{]*?(?:result-list|table|\btd\b|\bth\b)[^}{]*?\{[^}]*?\})', css)
print(f"Total matching rules: {len(matches)}")
for m in matches[:15]:
    print(m.strip())
    print("=" * 40)
