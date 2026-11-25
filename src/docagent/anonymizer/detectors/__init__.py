from typing import Protocol

from docagent.anonymizer.spans import Span


class Detector(Protocol):
    def detect(self, text: str) -> list[Span]: ...
