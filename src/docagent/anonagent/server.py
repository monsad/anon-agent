"""Serwer MCP (stdio): model pracuje wyłącznie na 2_bezpieczne, prawdziwe dane zostają na dysku."""

import functools

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from docagent.anonagent.workspace import Workspace

INSTRUCTIONS = """Dokumenty są spseudonimizowane: dane osobowe i firmowe zastąpiono znacznikami w nawiasach \
kwadratowych, np. [PERSON_1a2b3c4d]. Używaj znaczników dosłownie i nie próbuj zgadywać prawdziwych wartości. \
Typowa kolejność: anonymize_inbox -> list_documents -> read_document -> docx_add_comment / create_document \
-> restore_document (prawdziwe dane trafiają wtedy do folderu wyników, a Ty dostajesz tylko potwierdzenie). \
Gdy użytkownik poda ścieżkę do pliku, użyj anonymize_file. Gdy nie wie, gdzie wrzucić umowę albo gdzie jest wynik, \
użyj open_folder. Nigdy nie proś o wklejenie treści umowy do czatu ani o dołączenie jej spinaczem."""

server = MCPServer("anon-agent", instructions=INSTRUCTIONS)
workspace = Workspace()


def _tool(fn):
    """Błędy użytkowe (zła nazwa, brak fragmentu) trafiają do modelu jako czytelny komunikat."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (FileNotFoundError, ValueError) as e:
            raise ToolError(str(e)) from e

    return server.tool()(wrapper)


@_tool
def anonymize_inbox() -> list[dict]:
    """Pseudonimizuje nowe pliki z folderu z umowami i zapisuje je jako DOK_nnn w folderze zanonimizowanych.
    Zwraca nazwy dokumentów i liczbę ukrytych danych każdego rodzaju."""
    return workspace.anonymize_inbox()


@_tool
def anonymize_file(path: str) -> list[dict]:
    """Pseudonimizuje plik wskazany pełną ścieżką z dowolnego miejsca na dysku, np. 'C:\\Users\\Anna\\Desktop\\umowa.pdf'.
    Kopiuje go do folderu z umowami; oryginał zostaje na miejscu."""
    return workspace.import_file(path)


@_tool
def open_folder(which: str = "umowy") -> str:
    """Otwiera folder w Eksploratorze plików u użytkownika: 'umowy' (tu wrzuca dokumenty),
    'zanonimizowane' (wersje ze znacznikami) albo 'wyniki' (gotowe dokumenty z prawdziwymi danymi)."""
    return workspace.open_folder(which)


@_tool
def list_documents() -> list[str]:
    """Lista dokumentów w folderze zanonimizowanych (już na znacznikach)."""
    return workspace.list_documents()


@_tool
def read_document(name: str) -> str:
    """Treść dokumentu z folderu zanonimizowanych, np. name='DOK_002.docx'. Dla .docx dołącza istniejące komentarze."""
    return workspace.read_document(name)


@_tool
def docx_add_comment(name: str, quote: str, comment: str) -> str:
    """Dodaje komentarz Worda do akapitu, który zawiera dokładny fragment `quote` (skopiuj go z read_document)."""
    return workspace.add_comment(name, quote, comment)


@_tool
def create_document(name: str, text: str) -> str:
    """Tworzy nowy .docx w folderze zanonimizowanych, np. raport z analizy. Linie zaczynające się od '# ' / '## ' to nagłówki,
    od '- ' to punkty listy. Pisz na znacznikach — zostaną podmienione przy restore_document."""
    return workspace.create_document(name, text)


@_tool
def restore_document(name: str) -> str:
    """Przywraca prawdziwe dane w dokumencie i zapisuje wynik w folderze wyników. Treści z prawdziwymi danymi nie zwraca."""
    return workspace.restore_document(name)


def main() -> None:
    workspace.init()
    server.run("stdio")


if __name__ == "__main__":
    main()
