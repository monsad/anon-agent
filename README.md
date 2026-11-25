# AnonAgent

Serwer MCP dla Claude Desktop. Claude czyta i komentuje umowy, faktury i arkusze, ale nie widzi w nich PESEL-i, nazwisk, firm, adresów ani kwot. Dane zamieniane są na znaczniki na Twoim komputerze, a na końcu wracają do gotowego dokumentu.

```
1_wejscie      Wykonawca: Jan Kowalski, PESEL 44051401458, wynagrodzenie 125 000,00 zł
2_bezpieczne   Wykonawca: [PERSON_bd1079f1], PESEL [PESEL_7e6fd4d5], wynagrodzenie [AMOUNT_c3277461]   ← tylko to widzi Claude
3_wyjscie      Wykonawca: Jan Kowalski, PESEL 44051401458, wynagrodzenie 125 000,00 zł  + komentarze Claude
```

Mapa „znacznik → prawdziwa wartość” zostaje na dysku (`~/AnonAgent/.mapa.json`). Formatowanie Worda, tabele i style zostają na miejscu.

## Instalacja

**[⬇ Pobierz anon-agent.zip](https://github.com/monsad/anon-agent/releases/latest/download/anon-agent.zip)** i rozpakuj go (prawy przycisk → Wyodrębnij wszystko).

**Sposób A, rozszerzenie (polecany):** w Claude Desktop otwórz Ustawienia → Rozszerzenia → Ustawienia zaawansowane → Zainstaluj rozszerzenie i wybierz `anon-agent.mcpb`. Pierwsze uruchomienie trwa kilka minut, bo pobiera polski model językowy.

**Sposób B, Windows:** kliknij dwukrotnie `zainstaluj-anonagent.bat`. Jeśli Windows pokaże „System Windows ochronił komputer”, wybierz Więcej informacji → Uruchom mimo to. Potem zamknij Claude Desktop całkowicie (także ikonę przy zegarze) i uruchom go ponownie.

## Użycie

1. Wrzuć dokument (.docx, .xlsx, .pdf, .txt) do `AnonAgent/1_wejscie` w katalogu domowym.
2. Napisz w Claude Desktop, np.: *„Zpseudonimizuj nowe dokumenty, przeanalizuj umowę pod kątem ryzyk dla Zamawiającego, dodaj komentarze do klauzul i przywróć dane.”*
3. Wynik znajdziesz w `AnonAgent/3_wyjscie`.

> **Nie dołączaj dokumentu spinaczem do czatu.** Wtedy trafia do Claude bez pseudonimizacji.

## Co jest ukrywane

PESEL, NIP, REGON i IBAN (z kontrolą sumy), KRS, dowód osobisty, imiona i nazwiska (model spaCy `pl_core_news_md`), nazwy firm z formą prawną, adresy, kody pocztowe, telefony, e-maile i kwoty (także „słownie”). Procenty i terminy zostają widoczne. W Excelu ukrywany jest tylko tekst, liczby w komórkach zostają.

Nazwy, których wykrywacz nie złapał, dopisz do słownika: `anonagent dodaj PERSON "Jan Kowalski"`.

## Narzędzia MCP

| Narzędzie | Co robi |
|---|---|
| `anonymize_inbox` | pseudonimizuje nowe pliki z `1_wejscie` do `2_bezpieczne/DOK_nnn` |
| `list_documents` | lista dokumentów na znacznikach |
| `read_document` | treść dokumentu (z komentarzami Worda) |
| `docx_add_comment` | komentarz Worda przy akapicie z podanym fragmentem |
| `create_document` | nowy .docx, np. raport z analizy |
| `restore_document` | przywraca dane do `3_wyjscie`; modelowi zwraca tylko potwierdzenie |

## Dla programistów

```bash
uv sync --extra ner --extra mcp
uv pip install https://github.com/explosion/spacy-models/releases/download/pl_core_news_md-3.8.0/pl_core_news_md-3.8.0-py3-none-any.whl
uv run pytest
uv run anonagent check umowa.docx        # co zostanie wykryte, nic nie zapisuje
sh scripts/build.sh                       # buduje dist/anon-agent.zip, .mcpb i .bat
```

Wykrywanie jest automatyczne i może coś przeoczyć. Przy ważnych dokumentach przejrzyj wersję z `2_bezpieczne`, zanim poprosisz Claude o analizę.

Licencja: MIT.
