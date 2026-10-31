import re


class PIIAnalyzer:
    """Detects and masks PII in documents using regex patterns."""
    
    PII_PATTERNS = {
        "PHONE": r"\b(?:\+?91|0)?[6-9]\d{9}\b",
        "EMAIL": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        "PAN": r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
    }

    @classmethod
    def detect_pii(cls, text: str) -> dict[str, list[str]]:
        pii_found = {}
        for pii_type, pattern in cls.PII_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                pii_found[pii_type] = matches
        return pii_found

    @classmethod
    def mask_pii(cls, text: str, mask_char: str = "*") -> str:
        for pii_type, pattern in cls.PII_PATTERNS.items():
            text = re.sub(pattern, lambda m: mask_char * len(m.group()), text)
        return text
