"""Foldery AnonAgenta: 1_wejscie (oryginały) -> 2_bezpieczne (na znacznikach) -> 3_wyjscie (przywrócone).

Mapa znacznik -> prawdziwa wartość leży tylko na dysku (.mapa.json) i nigdy nie trafia do modelu.
"""

import json
import os
import secrets
from collections import Counter
from collections.abc import Callable, Iterator
from pathlib import Path

import docx
import openpyxl
from docx.oxml.ns import qn
from pypdf import PdfReader

from docagent.anonymizer import AnonymizationSettings, Anonymizer, DictionaryDetector, Kind, LeakDetected, PatternDetector, Span, restore
from docagent.anonymizer.core import MAX_PASSES
from docagent.anonymizer.tokens import TOKEN_RE, make_token

W_P, W_T = qn("w:p"), qn("w:t")
TEXT_SUFFIXES = {".txt", ".md"}
SUPPORTED = {".docx", ".xlsx", ".pdf", *TEXT_SUFFIXES}
# Umowy: wartość kontraktu to tajemnica handlowa, więc kwoty też ukrywamy (domyślnie anonimizator ich nie ukrywa).
SETTINGS = AnonymizationSettings(enabled_kinds=frozenset(Kind))


def _build_detectors() -> list:
    detectors: list = [PatternDetector()]
    try:
        from docagent.anonymizer.detectors.ner import SpacyNerDetector

        detectors.append(SpacyNerDetector(model="pl_core_news_md"))
    except Exception:  # bez spaCy działają wzorce i słownik
        pass
    return detectors


def _env_path(name: str) -> Path | None:
    """Folder z ustawień rozszerzenia; pusta wartość albo nierozwinięta zmienna (${...}) = domyślny."""
    value = os.environ.get(name, "").strip()
    return Path(value).expanduser() if value and "${" not in value else None


class Workspace:
    def __init__(self, root: Path | None = None, inbox: Path | None = None, safe: Path | None = None,
                 out: Path | None = None):
        self.root = Path(root or _env_path("ANONAGENT_HOME") or Path.home() / "AnonAgent")
        self.inbox = Path(inbox or _env_path("ANONAGENT_INBOX") or self.root / "1_wejscie")
        self.safe = Path(safe or _env_path("ANONAGENT_SAFE") or self.root / "2_bezpieczne")
        self.out = Path(out or _env_path("ANONAGENT_OUT") or self.root / "3_wyjscie")
        self._state_file = self.root / ".mapa.json"
        self._secret_file = self.root / ".sekret"
        self.dictionary_file = self.root / "slownik.txt"
        self._detectors: list | None = None

    # --- przygotowanie ---

    def init(self) -> None:
        for folder in (self.root, self.inbox, self.safe, self.out):
            folder.mkdir(parents=True, exist_ok=True)
        if not self._secret_file.exists():
            self._secret_file.write_text(secrets.token_hex(32))
            self._secret_file.chmod(0o600)
        if not self.dictionary_file.exists():
            self.dictionary_file.write_text(
                "# Znane nazwy, które zawsze ukrywać. Jedna na linię: RODZAJ<TAB>tekst, np.\n"
                "# PERSON\tJan Kowalski\n# ORG\tHurtownia Paliw Sp. z o.o.\n"
            )

    def _secret(self) -> bytes:
        if not self._secret_file.exists():
            self.init()
        return self._secret_file.read_text().strip().encode()

    def _dictionary(self) -> list[tuple[str, Kind]]:
        if not self.dictionary_file.exists():
            return []
        entries = []
        for line in self.dictionary_file.read_text().splitlines():
            kind, sep, text = line.partition("\t")
            if sep and not line.startswith("#") and kind.strip() in Kind.__members__.values():
                entries.append((text.strip(), Kind(kind.strip())))
        return entries

    def add_to_dictionary(self, text: str, kind: Kind) -> None:
        self.init()
        with self.dictionary_file.open("a") as f:
            f.write(f"{kind}\t{text.strip()}\n")

    def anonymizer(self) -> Anonymizer:
        if self._detectors is None:
            self._detectors = _build_detectors()
        return Anonymizer([*self._detectors, DictionaryDetector(self._dictionary())], self._secret(), SETTINGS)

    def _load_state(self) -> dict:
        if self._state_file.exists():
            return json.loads(self._state_file.read_text())
        return {"docs": {}, "mapping": {}}

    def _save_state(self, state: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(json.dumps(state, ensure_ascii=False, indent=1))
        self._state_file.chmod(0o600)

    # --- pseudonimizacja ---

    def anonymize_inbox(self) -> list[dict]:
        """Nowe pliki z 1_wejscie -> 2_bezpieczne/DOK_nnn. Nazwy oryginałów nie wychodzą poza dysk."""
        if self.inbox.resolve() in (self.safe.resolve(), self.out.resolve()):
            # Inaczej kolejne uruchomienia brałyby własne wyniki za nowe umowy.
            raise ValueError("Folder z umowami musi być inny niż folder zanonimizowanych plików i folder wyników.")
        self.init()
        state = self._load_state()
        done = set(state["docs"].values())
        anonymizer = self.anonymizer()
        report = []
        for source in sorted(self.inbox.iterdir()):
            suffix = source.suffix.lower()
            if source.name in done or suffix not in SUPPORTED or source.name.startswith((".", "~$")):
                continue
            target_suffix = suffix if suffix in {".docx", ".xlsx"} else ".txt"
            name = f"DOK_{len(state['docs']) + 1:03d}{target_suffix}"
            mapping: dict[str, str] = {}
            try:
                if suffix == ".docx":
                    _anonymize_docx(source, self.safe / name, anonymizer, self._secret(), mapping)
                elif suffix == ".xlsx":
                    _anonymize_xlsx(source, self.safe / name, anonymizer, mapping)
                else:
                    result = anonymizer.anonymize(_read_plain(source))
                    mapping.update(result.mapping)
                    (self.safe / name).write_text(result.text)
            except LeakDetected as e:
                report.append({"dokument": name, "blad": str(e)})
                continue
            state["docs"][name] = source.name
            for token, value in mapping.items():
                state["mapping"].setdefault(token, value)
            self._save_state(state)
            counts = Counter(TOKEN_RE.fullmatch(t)["kind"] for t in mapping)
            report.append({"dokument": name, "ukryte": dict(sorted(counts.items()))})
        return report

    def check(self, path: Path) -> list[Span]:
        """Co wykrywacz znalazłby w pliku — bez zapisywania czegokolwiek."""
        if path.suffix.lower() == ".docx":
            text = "\n".join(_segment_text(seg) for seg in _docx_segments(docx.Document(str(path))))
        elif path.suffix.lower() == ".xlsx":
            text = "\n".join(_xlsx_text(openpyxl.load_workbook(path)))
        else:
            text = _read_plain(path)
        return self.anonymizer().detect(text)

    def review(self) -> dict[str, str]:
        return dict(self._load_state()["mapping"])

    # --- dokumenty po stronie bezpiecznej (to widzi model) ---

    def _safe_path(self, name: str) -> Path:
        path = self.safe / name
        if Path(name).name != name or not path.is_file():
            raise FileNotFoundError(f"Nie ma dokumentu {name!r} w 2_bezpieczne. Użyj list_documents.")
        return path

    def list_documents(self) -> list[str]:
        self.init()
        return sorted(p.name for p in self.safe.iterdir() if p.suffix.lower() in SUPPORTED and not p.name.startswith("."))

    def read_document(self, name: str) -> str:
        path = self._safe_path(name)
        if path.suffix.lower() == ".docx":
            document = docx.Document(str(path))
            lines = [_segment_text(seg) for seg in _docx_segments(document, body_only=True)]
            comments = [
                f"- [{c.comment_id}] {c.author}: {c.text}" for c in document.comments
            ]
            if comments:
                lines += ["", "KOMENTARZE:", *comments]
            return "\n".join(lines)
        if path.suffix.lower() == ".xlsx":
            return "\n".join(_xlsx_text(openpyxl.load_workbook(path)))
        return path.read_text()

    def add_comment(self, name: str, quote: str, comment: str, author: str = "AnonAgent") -> str:
        path = self._safe_path(name)
        if path.suffix.lower() != ".docx":
            raise ValueError("Komentarze można dodawać tylko do plików .docx.")
        document = docx.Document(str(path))
        for paragraph in _all_paragraphs(document):
            if quote.strip() and quote.strip() in paragraph.text and paragraph.runs:
                document.add_comment(paragraph.runs, text=comment, author=author, initials="AA")
                document.save(str(path))
                return f"Dodano komentarz w {name} przy akapicie: {paragraph.text[:80]!r}"
        raise ValueError(f"Nie znaleziono w {name} akapitu zawierającego: {quote!r}")

    def create_document(self, name: str, text: str) -> str:
        """Nowy .docx z treści modelu (na znacznikach). Linie '# ' i '## ' to nagłówki."""
        if Path(name).name != name:
            raise ValueError("Podaj samą nazwę pliku, bez folderów.")
        if not name.lower().endswith(".docx"):
            name += ".docx"
        self.init()
        document = docx.Document()
        for line in text.splitlines():
            if line.startswith("## "):
                document.add_heading(line[3:], level=2)
            elif line.startswith("# "):
                document.add_heading(line[2:], level=1)
            elif line.startswith(("- ", "* ")):
                document.add_paragraph(line[2:], style="List Bullet")
            else:
                document.add_paragraph(line)
        document.save(str(self.safe / name))
        return f"Zapisano {name} w 2_bezpieczne."

    def restore_document(self, name: str) -> str:
        """Podstawia prawdziwe dane i zapisuje do 3_wyjscie. Zwraca tylko nazwę pliku, bez treści."""
        path = self._safe_path(name)
        state = self._load_state()
        mapping = state["mapping"]
        source = state["docs"].get(name)
        target_name = f"{Path(source).stem} (wynik){path.suffix}" if source else name
        target = self.out / target_name
        self.out.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".docx":
            document = docx.Document(str(path))
            for segment in _docx_segments(document):
                text = _segment_text(segment)
                spans = [(m.start(), m.end(), mapping[m.group()]) for m in TOKEN_RE.finditer(text) if m.group() in mapping]
                _replace_spans(segment, spans)
            document.save(str(target))
        elif path.suffix.lower() == ".xlsx":
            workbook = openpyxl.load_workbook(path)
            _map_xlsx_strings(workbook, lambda value: restore(value, mapping))
            workbook.save(target)
        else:
            target.write_text(restore(path.read_text(), mapping))
        # Nazwa oryginału bywa danymi osobowymi ("umowa Kowalski.docx"), więc modelowi jej nie podajemy.
        return f"Przywrócono dane w {name}. Wynik jest w folderze wyników."


# --- DOCX: podmiana na poziomie w:t, żeby pogrubienia, tabele i style zostały na miejscu ---


def _all_paragraphs(document) -> Iterator:
    yield from document.paragraphs
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs


def _docx_segments(document, body_only: bool = False) -> Iterator[list]:
    """Akapity jako listy elementów w:t — ze wszystkich części (treść, nagłówki, stopki, komentarze)."""
    parts = [document.part] if body_only else [
        part for part in document.part.package.iter_parts() if hasattr(part, "element") and part.content_type.endswith("+xml")
        and "wordprocessingml" in part.content_type
    ]
    for part in parts:
        for p in part.element.iter(W_P):
            texts = [t for t in p.iter(W_T) if next(t.iterancestors(W_P)) is p]
            if texts:
                yield texts


def _segment_text(segment: list) -> str:
    return "".join(t.text or "" for t in segment)


def _replace_spans(segment: list, spans: list[tuple[int, int, str]]) -> None:
    """Zamienia zakresy tekstu akapitu; zakres rozcięty między runy trafia do pierwszego z nich."""
    starts, pos = [], 0
    for t in segment:
        starts.append(pos)
        pos += len(t.text or "")
    for start, end, new in sorted(spans, reverse=True):
        first = True
        for t, s in zip(segment, starts):
            text = t.text or ""
            e = s + len(text)
            if e <= start or s >= end:
                continue
            a, b = max(start, s) - s, min(end, e) - s
            t.text = text[:a] + (new if first else "") + text[b:]
            t.set(qn("xml:space"), "preserve")
            first = False


def _anonymize_docx(source: Path, target: Path, anonymizer: Anonymizer, secret: bytes, mapping: dict[str, str]) -> None:
    document = docx.Document(str(source))
    for _ in range(MAX_PASSES):
        changed = False
        for segment in _docx_segments(document):
            leaks = anonymizer.find_leaks(_segment_text(segment))
            if not leaks:
                continue
            spans = []
            for span in leaks:
                token = make_token(secret, span.kind, span.text)
                mapping.setdefault(token, span.text)
                spans.append((span.start, span.end, token))
            _replace_spans(segment, spans)
            changed = True
        if not changed:
            break
    leaks = [span for segment in _docx_segments(document) for span in anonymizer.find_leaks(_segment_text(segment))]
    if leaks:
        raise LeakDetected(leaks)
    # Metadane pliku też potrafią zdradzić autora.
    props = document.core_properties
    props.author = props.last_modified_by = ""
    document.save(str(target))


# --- XLSX i tekst ---


def _map_xlsx_strings(workbook, fn: Callable[[str], str]) -> None:
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and not cell.value.startswith("="):
                    cell.value = fn(cell.value)


def _anonymize_xlsx(source: Path, target: Path, anonymizer: Anonymizer, mapping: dict[str, str]) -> None:
    workbook = openpyxl.load_workbook(source)

    def mask(value: str) -> str:
        result = anonymizer.anonymize(value)
        mapping.update({k: v for k, v in result.mapping.items() if k not in mapping})
        return result.text

    _map_xlsx_strings(workbook, mask)
    workbook.properties.creator = workbook.properties.lastModifiedBy = ""
    workbook.save(target)


def _xlsx_text(workbook) -> list[str]:
    lines = []
    for sheet in workbook.worksheets:
        lines.append(f"## Arkusz: {sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            if any(v is not None for v in row):
                lines.append("\t".join("" if v is None else str(v) for v in row))
    return lines


def _read_plain(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return path.read_text(errors="replace")
