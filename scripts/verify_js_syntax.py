import re

with open('packages/static/packages/js/package_dynamic_form.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Check with regex for unmatched parentheses
# Check in Python using basic state machine
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

    # Comments
    if content[i:i+2] == '//':
        while i < n and content[i] != '\n':
            i += 1
        continue
    elif content[i:i+2] == '/*':
        i += 2
        while i < n and content[i:i+2] != '*/':
            if content[i] == '\n':
                line += 1
            i += 1
        i += 2
        continue

    # Strings
    if ch in ("'", '"', '`'):
        q = ch
        start_line = line
        i += 1
        while i < n:
            if content[i] == '\\':
                i += 2
                continue
            if content[i] == q:
                i += 1
                break
            if content[i] == '\n':
                line += 1
            i += 1
        continue

    # Regex literal heuristics
    if ch == '/' and i + 1 < n and content[i+1] not in ('/', '*'):
        # Check if previous non-whitespace char is operator
        prev_idx = i - 1
        while prev_idx >= 0 and content[prev_idx] in (' ', '\t', '\r', '\n'):
            prev_idx -= 1
        if prev_idx >= 0 and content[prev_idx] in ('=', '(', ',', ':', '[', '!', '&', '|', ';', '?'):
            i += 1
            while i < n and content[i] != '/':
                if content[i] == '\\':
                    i += 2
                    continue
                if content[i] == '\n':
                    break
                i += 1
            if i < n and content[i] == '/':
                i += 1
            continue

    if ch in ('(', '{', '['):
        stack.append((ch, line, col))
    elif ch in (')', '}', ']'):
        if not stack:
            print(f"Unexpected closing {ch} at line {line}:{col}")
        else:
            top, tl, tc = stack.pop()
            pairs = {')': '(', '}': '{', ']': '['}
            if pairs[ch] != top:
                print(f"Mismatched {top} at line {tl}:{tc} closed by {ch} at line {line}:{col}")

    col += 1
    i += 1

if stack:
    print(f"Unclosed items: {len(stack)}")
    for item in stack[:5]:
        print(f"  {item[0]} at line {item[1]}:{item[2]}")
else:
    print("ALL BRACES, PARENS, AND BRACKETS MATCH PERFECTLY (0 ERRORS)!")
