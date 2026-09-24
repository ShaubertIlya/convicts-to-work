def is_valid_kz_iik(value: str) -> bool:
    """Validate a Kazakhstan IBAN using its format and ISO 13616 checksum."""
    normalized = value.replace(" ", "").upper()
    if len(normalized) != 20 or not normalized.startswith("KZ"):
        return False
    if not normalized[2:4].isdigit():
        return False
    if any(character in "IOQ" or not character.isalnum() for character in normalized[4:]):
        return False

    rearranged = normalized[4:] + normalized[:4]
    numeric = "".join(
        str(ord(character) - 55) if character.isalpha() else character for character in rearranged
    )
    return int(numeric) % 97 == 1
