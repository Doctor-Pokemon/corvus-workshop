"""Prototype 0221: the five new HM givers say the HM's move and what it does in the field with the right badge (owner rule 2026-11-10: "they just need to say the HM move's name, and what it does in the field with the right badge").
Replaces the placeholder line "Take this HM, too." that hm_gym_gifts.py (0215) put in each leader's map text bank. Badges follow the owner's table: Rock Smash = Boulder, Waterfall = Rainbow, Fly = Thunder, Rock Climb = Earth, Whirlpool = Volcano.
Janine (Surf) and Sabrina (Strength) keep their own lines. Only a text row changes in each of five maps.
Usage (from yellow-heartgold, PYTHONPATH=tools): hm_gift_lines.py <in.nds> <out.nds>"""
import sys
import ndspy.rom
from ext_edit import ExtEdit
from map_edit import MapEdit
from opening import encode_text
from parcel_quest import PH
from prototype import decode_messages

OLD = 'Take this HM, too.'
LINES = [
    ('Brock', 473, "This is HM06, ROCK SMASH.\nWith the BOULDER BADGE, it shatters\nrocks that block your way."),
    ('Misty', 427, "This is HM07, WATERFALL.\nWith the RAINBOW BADGE, your Pokémon\ncan climb up waterfalls."),
    ('Surge', 365, "This is HM02, FLY.\nWith the THUNDER BADGE, you can fly\nto any town you have visited."),
    ('Blaine', 457, "This is HM08, ROCK CLIMB.\nWith the EARTH BADGE, your Pokémon\ncan scale rocky walls."),
    ('Giovanni', 579, "This is HM05, WHIRLPOOL.\nWith the VOLCANO BADGE, your Pokémon\ncan cross whirlpools."),
]


def row(text):
    return decode_messages(encode_text([text], PH))[1][0]


def patch(rom):
    old = row(OLD)
    report = {}
    for name, map_id, text in LINES:
        e = ExtEdit(rom, map_id) if map_id >= 540 else MapEdit(rom, map_id)
        hits = [i for i, r in enumerate(e.rows) if r == old]
        assert len(hits) == 1, (name, hits)
        e.rows[hits[0]] = row(text)
        e.save()
        report[name] = hits[0]
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
