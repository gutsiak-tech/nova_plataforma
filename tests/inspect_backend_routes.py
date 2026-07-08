from pathlib import Path
import re

print("=" * 100)
print("TESTE 7 — INVENTÁRIO ESTÁTICO DAS ROTAS DO BACKEND")
print("=" * 100)

root = Path("app")
patterns = [
    re.compile(r'@\w+\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'),
    re.compile(r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'),
    re.compile(r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'),
]

routes = []

for path in sorted(root.rglob("*.py")):
    text = path.read_text(encoding="utf-8", errors="ignore")

    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                method = match.group(1).upper()
                route = match.group(2)
                routes.append((path.as_posix(), line_no, method, route))

print(f"Rotas encontradas: {len(routes)}")

for file, line_no, method, route in routes:
    print(f"{method:6} {route:40} | {file}:{line_no}")

print("\n" + "=" * 100)
print("FIM DO TESTE 7")
print("=" * 100)
