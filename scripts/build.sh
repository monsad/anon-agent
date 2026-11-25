#!/bin/sh
# Buduje paczki instalacyjne AnonAgenta.
# Wynik w dist/: anon-agent.mcpb, zainstaluj-anonagent.bat i anon-agent.zip (oba + instrukcja).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp "$ROOT/pyproject.toml" "$ROOT/README.md" "$ROOT/LICENSE" "$STAGE/"
mkdir -p "$STAGE/src/docagent"
cp "$ROOT/src/docagent/__init__.py" "$STAGE/src/docagent/"
cp -R "$ROOT/src/docagent/anonymizer" "$ROOT/src/docagent/anonagent" "$STAGE/src/docagent/"
find "$STAGE" -name __pycache__ -prune -exec rm -rf {} +
(cd "$STAGE" && uv build --wheel -q -o "$STAGE/dist")
mkdir -p "$ROOT/dist"

# Windows: jeden plik .bat z wbudowaną paczką — dwuklik i gotowe.
WHEEL="$(ls "$STAGE"/dist/*.whl | head -1)"
BAT="$ROOT/dist/zainstaluj-anonagent.bat"
{
  printf '@echo off\r\nset "ANON_BAT=%%~f0"\r\n'
  printf 'rem Instalator AnonAgent dla Windows. Dwuklik, potem uruchom ponownie Claude Desktop.\r\n'
  printf 'powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=[IO.File]::ReadAllText($env:ANON_BAT); iex $s.Substring($s.IndexOf(\x27#PS\x27+\x27START\x27))"\r\n'
  printf 'pause\r\nexit /b\r\n'
  printf '#PSSTART\r\n'
  printf '$WHEEL_B64 = \x27%s\x27\r\n' "$(base64 < "$WHEEL" | tr -d '\n')"
  sed "s/__WHEEL_NAME__/$(basename "$WHEEL")/" "$ROOT/packaging/windows-installer.ps1" | sed 's/$/\r/'
} > "$BAT"
echo "$BAT"

# Rozszerzenie Claude Desktop (.mcpb, runtime uv): Ustawienia -> Rozszerzenia -> Zainstaluj.
BUNDLE="$STAGE/mcpb"
mkdir -p "$BUNDLE/src"
cp "$ROOT"/packaging/mcpb/manifest.json "$ROOT"/packaging/mcpb/pyproject.toml "$ROOT"/packaging/mcpb/.mcpbignore "$BUNDLE/"
cp "$ROOT/packaging/mcpb/server.py" "$BUNDLE/src/server.py"
cp -R "$STAGE/src/docagent" "$BUNDLE/src/"
npx -y @anthropic-ai/mcpb@2.1.2 pack "$BUNDLE" "$ROOT/dist/anon-agent.mcpb" >/dev/null
echo "$ROOT/dist/anon-agent.mcpb"

# Jedna paczka do wysłania: oba instalatory + instrukcja.
PACK="$STAGE/anon-agent"
mkdir -p "$PACK"
cp "$ROOT/dist/anon-agent.mcpb" "$BAT" "$PACK/"
sed 's/$/\r/' "$ROOT/packaging/CZYTAJ-MNIE.txt" > "$PACK/CZYTAJ-MNIE.txt"
rm -f "$ROOT/dist/anon-agent.zip"
(cd "$STAGE" && zip -qr "$ROOT/dist/anon-agent.zip" anon-agent)
echo "$ROOT/dist/anon-agent.zip"
