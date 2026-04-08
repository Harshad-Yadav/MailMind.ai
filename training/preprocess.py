from __future__ import annotations

import re


def normalize_email_text(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\s+", " ", value)
    return value
