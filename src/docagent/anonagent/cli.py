"""anonagent init | run | review | check PLIK | dodaj RODZAJ "tekst" | claude-desktop — obsługa bez modelu."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from docagent.anonagent.workspace import Workspace
from docagent.anonymizer import Kind


def main() -> None:
    parser = argparse.ArgumentParser(prog="anonagent")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="tworzy foldery ~/AnonAgent")
    sub.add_parser("run", help="pseudonimizuje nowe pliki z 1_wejscie")
    sub.add_parser("review", help="tabela: znacznik -> prawdziwa wartość")
    check = sub.add_parser("check", help="pokazuje, co wykrywacz znajdzie w pliku (nic nie zapisuje)")
    check.add_argument("path", type=Path)
    add = sub.add_parser("dodaj", help="dopisuje nazwę do słownika, żeby zawsze ją ukrywać")
    add.add_argument("kind", choices=[k.value for k in Kind])
    add.add_argument("text")
    desktop = sub.add_parser("claude-desktop", help="wpisuje serwer anon-agent do konfiguracji Claude Desktop")
    desktop.add_argument("--config", type=Path, default=None, help="inna ścieżka pliku konfiguracyjnego")
    args = parser.parse_args()

    ws = Workspace()
    if args.cmd == "init":
        ws.init()
        print(f"Gotowe. Wrzucaj pliki do {ws.inbox}")
    elif args.cmd == "run":
        for row in ws.anonymize_inbox() or [{"info": "brak nowych plików w 1_wejscie"}]:
            print(row)
    elif args.cmd == "review":
        for token, value in ws.review().items():
            print(f"{token}\t{value}")
    elif args.cmd == "check":
        for span in ws.check(args.path):
            print(f"{span.kind.value:12} {span.text}")
    elif args.cmd == "dodaj":
        ws.add_to_dictionary(args.text, Kind(args.kind))
        print(f"Dopisano do {ws.dictionary_file}")
    elif args.cmd == "claude-desktop":
        path = args.config or Path(os.environ.get("ANONAGENT_CLAUDE_CONFIG") or claude_desktop_config_path())
        register_in_claude_desktop(path)
        print(f"Dodano anon-agent do {path}\nZamknij Claude Desktop całkowicie i uruchom go ponownie.")


def claude_desktop_config_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / "Claude/claude_desktop_config.json"
    return Path.home() / ".config/Claude/claude_desktop_config.json"


def register_in_claude_desktop(path: Path) -> None:
    """Dopisuje serwer, nie ruszając pozostałych ustawień; poprzednią wersję zostawia jako .bak."""
    config = {}
    if path.exists():
        config = json.loads(path.read_text(encoding="utf-8") or "{}")
        shutil.copy2(path, path.with_name(path.name + ".bak"))
    # Ten sam Python, w którym zainstalowano paczkę — nie zależy od PATH w Claude Desktop.
    config.setdefault("mcpServers", {})["anon-agent"] = {
        "command": sys.executable,
        "args": ["-m", "docagent.anonagent.server"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
