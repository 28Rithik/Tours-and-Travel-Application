with open('packages/static/packages/js/package_dynamic_form.js', 'r', encoding='utf-8') as f:
    content = f.read()

i = 0
n = len(content)
stack = []
line = 1
col = 1
while i < n:
    ch = content[i]
    if ch == '\n':
        line += 1
        col = 1
        i += 1
        continue
    # single line comment
    if ch == '/' and i + 1 < n and content[i+1] == '/':
        while i < n and content[i] != '\n':
            i += 1
        continue
    # multi line comment
    if ch == '/' and i + 1 < n and content[i+1] == '*':
        i += 2
        while i + 1 < n and not (content[i] == '*' and content[i+1] == '/'):
            if content[i] == '\n':
                line += 1
            i += 1
        i += 2
        continue
    # strings
    if ch in ('"', "'"):
        quote = ch
        i += 1
        while i < n and content[i] != quote:
            if content[i] == '\\':
                i += 2
            else:
                if content[i] == '\n':
                    line += 1
                i += 1
        i += 1
        continue
    # template literal
    if ch == '`':
        i += 1
        while i < n and content[i] != '`':
            if content[i] == '\\':
                i += 2
            else:
                if content[i] == '\n':
                    line += 1
                i += 1
        i += 1
        continue
    if ch == '(':
        stack.append((line, col))
    elif ch == ')':
        if stack:
            stack.pop()
        else:
            print(f"Extra ) at line {line}, col {col}")
    i += 1

print(f"Total unclosed parens outside strings: {len(stack)}")
for l, c in stack:
    print(f"Unclosed ( at line {l}, col {c}")
