"""Species-name helper: pret's SPECIES_ constants from the ROM's name text (HG charmap: digits 0x121.., A 0x12B.., a 0x145..)."""
SPECIAL = {0x1AC: '', 0x1B1: '', 0x1BE: '', 0x1B3: '', 0x1AE: '', 0x1BF: ''}


def species_name(row):
    out = ''
    for c in row:
        if c == 65535:
            break
        if 0x121 <= c <= 0x12A:
            out += chr(48 + c - 0x121)
        elif 0x12B <= c <= 0x144:
            out += chr(65 + c - 0x12B)
        elif 0x145 <= c <= 0x15E:
            out += chr(65 + c - 0x145)
    return out
