"""ОКВЭД 2 (ОК 029-2014, КДЕС Ред. 2): раздел по классу кода."""

_SECTIONS = (
    ("A", 1, 3), ("B", 5, 9), ("C", 10, 33), ("D", 35, 35), ("E", 36, 39), ("F", 41, 43), ("G", 45, 47),
    ("H", 49, 53), ("I", 55, 56), ("J", 58, 63), ("K", 64, 66), ("L", 68, 68), ("M", 69, 75), ("N", 77, 82),
    ("O", 84, 84), ("P", 85, 85), ("Q", 86, 88), ("R", 90, 93), ("S", 94, 96), ("T", 97, 98), ("U", 99, 99),
)


def okved_class(code: str | None) -> str | None:
    """'56.30' → '56'."""
    head = (code or "").split(".")[0]
    return head if head.isdigit() else None


def section_of(code: str | None) -> str | None:
    cls = okved_class(code)
    if cls is None:
        return None
    n = int(cls)
    return next((s for s, lo, hi in _SECTIONS if lo <= n <= hi), None)
