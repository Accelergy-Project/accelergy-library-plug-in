import re
from typing import Dict, List, Optional


def cast_to_float(s: str) -> float:
    if isinstance(s, str):
        s = s.strip()
    return float(s)


def parse_float(s: str, context: str = "") -> float:
    """Parses a string into a float. Handles scientific notation."""
    # Remove leading and trailing non-numeric characters
    s = str(s)
    numeric_re_sub = f"[^0-9eE\-\+\.]"
    s_trimmed = re.sub(f"^{numeric_re_sub}+", "", s)
    s_trimmed = re.sub(f"{numeric_re_sub}+$", "", s_trimmed)
    try:
        return float(s_trimmed)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f'Could not parse "{s}" from "{context}" as a float.'
        ) from e


def get_value_from_entry(
    entry: Dict[str, str],
    target: str,
) -> Optional[float]:
    """Searches an entry for a value matching the target and quantifiers.
    Scales by any attached quantifiers and the base unit.

    Args:
        entry (Dict[str, str]): Entry to search
        target (str): Target to search for. "energy" or "area"
    Returns:
        Optional[float]: Scaled value, or None if not found
    """
    value = None
    for k in entry:
        if target in k.lower():
            value = cast_to_float(entry[k])
            break

    return value
