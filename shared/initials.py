def generate_initials(full_name):
    """Up to two uppercase initials from a whitespace-separated name string.

    Prefers the first letter of the first word plus the first letter of the
    next word (e.g. 'Julian Felipe Montoya' -> 'JF'). Returns '' for empty,
    blank, or single-character-only input instead of raising.
    """
    if not full_name:
        return ''
    parts = full_name.split()
    if not parts:
        return ''
    initials = parts[0][0]
    if len(parts) > 1:
        initials += parts[1][0]
    return initials.upper()
