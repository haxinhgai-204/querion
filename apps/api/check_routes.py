import ast, re
content = open('app/routers/workflows.py', encoding='utf-8-sig').read()
ast.parse(content)
print("Syntax: OK")
routes = re.findall(r'@router\.(get|post|patch|delete)\("([^"]+)"', content)
for method, path in routes:
    print("  " + method.upper().ljust(6) + " " + path)
