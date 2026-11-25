# Punkt startowy rozszerzenia: `uv run src/server.py` dodaje src/ do sys.path, więc pakiet docagent jest obok.
from docagent.anonagent.server import main

main()
