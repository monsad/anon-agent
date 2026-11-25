import hashlib
import hmac
import re

from docagent.anonymizer.kinds import Kind
from docagent.anonymizer.normalize import normalize

TOKEN_RE = re.compile(r"\[(?P<kind>[A-Z]+(?:_[A-Z]+)*)_(?P<digest>[0-9a-f]{8})\]")


def make_token(secret: bytes, kind: Kind, value: str) -> str:
    """Stały w obrębie firmy (ten sam sekret), różny między firmami."""
    message = f"{kind}:{normalize(kind, value)}".encode()
    digest = hmac.new(secret, message, hashlib.sha256).hexdigest()[:8]
    return f"[{kind}_{digest}]"
