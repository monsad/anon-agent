import docx
import openpyxl
import pytest

from docagent.anonagent import Workspace
from docagent.anonymizer import Kind, PatternDetector

PESEL = "44051401458"
NIP = "526-104-08-28"


@pytest.fixture
def ws(tmp_path):
    workspace = Workspace(tmp_path / "AnonAgent")
    workspace.init()
    workspace._detectors = [PatternDetector()]  # bez NER — szybko i deterministycznie
    workspace.add_to_dictionary("Jan Kowalski", Kind.PERSON)
    return workspace


def _umowa(path):
    document = docx.Document()
    p = document.add_paragraph("Wykonawca: ")
    p.add_run("Jan").bold = True
    p.add_run(" Kowalski, PESEL " + PESEL)
    document.add_paragraph("Kara umowna wynosi 50% wynagrodzenia.")
    document.add_paragraph("Wynagrodzenie: 125 000,00 zł netto.")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "NIP"
    table.cell(0, 1).text = NIP
    document.core_properties.author = "Jan Kowalski"
    document.save(str(path))


def _all_text(path) -> str:
    return path.read_bytes().decode("latin-1") if path.suffix != ".docx" else "\n".join(
        t.text or "" for part in docx.Document(str(path)).part.package.iter_parts()
        if hasattr(part, "element") for t in part.element.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
    )


def test_docx_round_trip_keeps_formatting_and_hides_data(ws):
    _umowa(ws.inbox / "umowa Kowalski.docx")

    report = ws.anonymize_inbox()

    assert report == [{"dokument": "DOK_001.docx", "ukryte": {"AMOUNT": 1, "NIP": 1, "PERSON": 1, "PESEL": 1}}]
    safe = ws.safe / "DOK_001.docx"
    text = ws.read_document("DOK_001.docx")
    for secret in ("Kowalski", PESEL, NIP, "125 000"):
        assert secret not in text
        assert secret not in _all_text(safe)
    assert docx.Document(str(safe)).core_properties.author == ""
    assert docx.Document(str(safe)).paragraphs[0].runs[1].bold  # znacznik osoby w pogrubionym runie

    ws.add_comment("DOK_001.docx", "Kara umowna", "Ryzyko: wysoka kara dla [PERSON] — negocjować.")
    result = ws.restore_document("DOK_001.docx")

    out = ws.out / "umowa Kowalski (wynik).docx"
    assert out.exists() and "Kowalski" not in result
    restored = docx.Document(str(out))
    assert restored.paragraphs[0].text == f"Wykonawca: Jan Kowalski, PESEL {PESEL}"
    assert restored.tables[0].cell(0, 1).text == NIP
    assert restored.paragraphs[2].text == "Wynagrodzenie: 125 000,00 zł netto."
    assert [c.text for c in restored.comments] == ["Ryzyko: wysoka kara dla [PERSON] — negocjować."]


def test_comment_tokens_are_restored(ws):
    _umowa(ws.inbox / "u.docx")
    ws.anonymize_inbox()
    token = next(t for t, v in ws.review().items() if v == "Jan Kowalski")

    ws.add_comment("DOK_001.docx", "Kara", f"Uwaga na {token}")
    ws.restore_document("DOK_001.docx")

    assert [c.text for c in docx.Document(str(ws.out / "u (wynik).docx")).comments] == ["Uwaga na Jan Kowalski"]


def test_xlsx_and_txt_and_skip_already_done(ws):
    workbook = openpyxl.Workbook()
    workbook.active.append(["Kontrahent", "NIP", "Kwota"])
    workbook.active.append(["Jan Kowalski", NIP, 100])
    workbook.save(ws.inbox / "koszty.xlsx")
    (ws.inbox / "notatka.txt").write_text(f"PESEL {PESEL}")

    assert [r["dokument"] for r in ws.anonymize_inbox()] == ["DOK_001.xlsx", "DOK_002.txt"]
    second = ws.anonymize_inbox()
    assert len(second) == 1 and "Wcześniej przetworzone: 2" in second[0]["info"]
    assert NIP not in ws.read_document("DOK_001.xlsx") and "100" in ws.read_document("DOK_001.xlsx")
    assert PESEL not in ws.read_document("DOK_002.txt")

    ws.restore_document("DOK_001.xlsx")
    sheet = openpyxl.load_workbook(ws.out / "koszty (wynik).xlsx").active
    assert [c.value for c in sheet[2]] == ["Jan Kowalski", NIP, 100]


def test_created_report_is_restored(ws):
    (ws.inbox / "n.txt").write_text(f"PESEL {PESEL}")
    ws.anonymize_inbox()
    token = next(iter(ws.review()))

    ws.create_document("raport", f"# Raport\n- osoba z PESEL {token}")
    ws.restore_document("raport.docx")

    assert docx.Document(str(ws.out / "raport.docx")).paragraphs[1].text == f"osoba z PESEL {PESEL}"


def test_names_outside_safe_folder_are_rejected(ws):
    with pytest.raises(FileNotFoundError):
        ws.read_document("../.mapa.json")


def test_claude_desktop_registration_keeps_other_settings(tmp_path):
    import json

    from docagent.anonagent.cli import register_in_claude_desktop

    config = tmp_path / "claude_desktop_config.json"
    config.write_text(json.dumps({"preferences": {"x": 1}, "mcpServers": {"inny": {"command": "a"}}}))

    register_in_claude_desktop(config)

    data = json.loads(config.read_text())
    assert data["preferences"] == {"x": 1}
    assert set(data["mcpServers"]) == {"inny", "anon-agent"}
    assert data["mcpServers"]["anon-agent"]["args"] == ["-m", "docagent.anonagent.server"]
    assert (tmp_path / "claude_desktop_config.json.bak").exists()


def test_folders_can_be_chosen_separately(tmp_path, monkeypatch):
    monkeypatch.setenv("ANONAGENT_HOME", str(tmp_path / "nowy" / "klucz"))  # jeszcze nie istnieje
    monkeypatch.setenv("ANONAGENT_INBOX", str(tmp_path / "Umowy"))
    monkeypatch.setenv("ANONAGENT_SAFE", str(tmp_path / "Zanonimizowane"))
    monkeypatch.setenv("ANONAGENT_OUT", "${user_config.folder_wynikow}")  # nierozwinięte = domyślny
    workspace = Workspace()
    workspace._detectors = [PatternDetector()]
    workspace.init()  # tak startuje serwer
    (tmp_path / "Umowy" / "n.txt").write_text(f"PESEL {PESEL}")

    assert [r["dokument"] for r in workspace.anonymize_inbox()] == ["DOK_001.txt"]
    assert (tmp_path / "Zanonimizowane" / "DOK_001.txt").exists()
    workspace.restore_document("DOK_001.txt")
    assert (tmp_path / "nowy" / "klucz" / "3_wyjscie" / "n (wynik).txt").read_text() == f"PESEL {PESEL}"
    assert (tmp_path / "nowy" / "klucz" / ".mapa.json").exists()


def test_inbox_must_differ_from_output_folders(tmp_path):
    same = tmp_path / "Umowy"
    workspace = Workspace(tmp_path / "AnonAgent", inbox=same, out=same)
    with pytest.raises(ValueError, match="musi być inny"):
        workspace.anonymize_inbox()


def test_unsupported_and_broken_files_are_reported_without_names(ws):
    (ws.inbox / "umowa Kowalski.doc").write_bytes(b"stary format")
    (ws.inbox / "zepsuta.docx").write_bytes(b"to nie jest zip")
    (ws.inbox / "~$umowa.docx").write_bytes(b"plik blokady Worda")

    report = ws.anonymize_inbox()

    assert [r["pominiety_plik"] for r in report] == [".doc", ".docx"]
    assert "Zapisz jako" in report[0]["powod"] and "Kowalski" not in str(report)


def test_empty_inbox_says_where_it_looked(ws):
    assert "AnonAgent" in ws.anonymize_inbox()[0]["info"]


def test_import_file_from_anywhere(ws, tmp_path):
    elsewhere = tmp_path / "Pulpit" / "umowa.txt"
    elsewhere.parent.mkdir()
    elsewhere.write_text(f"PESEL {PESEL}")

    report = ws.import_file(f'"{elsewhere}"')  # tak wkleja "Kopiuj jako ścieżkę"

    assert report[0]["dokument"] == "DOK_001.txt"
    assert elsewhere.exists() and (ws.inbox / "umowa.txt").exists()
    with pytest.raises(FileNotFoundError, match="Kopiuj jako ścieżkę"):
        ws.import_file(str(tmp_path / "nie-ma.pdf"))


def test_open_folder_opens_the_real_path(ws, monkeypatch):
    opened = []
    monkeypatch.setattr("docagent.anonagent.workspace.subprocess.Popen", lambda args: opened.append(args))
    monkeypatch.setattr("docagent.anonagent.workspace.sys.platform", "darwin")

    message = ws.open_folder("wyniki")

    assert opened == [["open", str(ws.out)]] and str(ws.out) in message
    with pytest.raises(ValueError):
        ws.open_folder("pulpit")
