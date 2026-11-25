# Cialo instalatora Windows; build-anonagent.sh wkleja je do zainstaluj-anonagent.bat razem z paczka (base64).
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$spacyPl = "https://github.com/explosion/spacy-models/releases/download/pl_core_news_md-3.8.0/pl_core_news_md-3.8.0-py3-none-any.whl"

Write-Host "=== Instalacja AnonAgent ===" -ForegroundColor Cyan
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[1/4] Instaluje uv (menedzer Pythona)..."
    powershell -NoProfile -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
} else { Write-Host "[1/4] uv jest juz zainstalowany." }
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"

Write-Host "[2/4] Rozpakowuje paczke..."
$dir = Join-Path $env:TEMP "anonagent-install"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$wheel = Join-Path $dir "__WHEEL_NAME__"
[IO.File]::WriteAllBytes($wheel, [Convert]::FromBase64String($WHEEL_B64))

Write-Host "[3/4] Instaluje AnonAgent i model jezyka polskiego (pierwszy raz kilka minut)..."
uv tool install --force --python 3.12 "anon-agent[ner,mcp] @ $(([System.Uri]$wheel).AbsoluteUri)" --with $spacyPl
if ($LASTEXITCODE -ne 0) { throw "Instalacja nie powiodla sie (kod $LASTEXITCODE)." }

Write-Host "[4/4] Tworze foldery i podlaczam do Claude Desktop..."
anonagent init
anonagent claude-desktop
if ($LASTEXITCODE -ne 0) { throw "Nie udalo sie zapisac konfiguracji Claude Desktop." }

Write-Host ""
Write-Host "GOTOWE." -ForegroundColor Green
Write-Host "1. Zamknij Claude Desktop calkowicie (takze ikone przy zegarze) i uruchom ponownie."
Write-Host "2. Wrzucaj dokumenty do: $env:USERPROFILE\AnonAgent\1_wejscie"
Write-Host "3. Wynik z prawdziwymi danymi pojawi sie w: $env:USERPROFILE\AnonAgent\3_wyjscie"
