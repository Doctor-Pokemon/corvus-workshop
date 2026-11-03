"""Prototype 0167: the Lavender Radio Tower door leads straight to Pokemon Tower 1F and its sign reads like Yellow's Pokemon Tower sign (owner order 2026-11-03, from a video: the door first showed the Radio Tower reception lobby and only then dropped the player into the Tower).
Before: the door (Lavender map 53, warp 6) led into the lobby (map 439) whose frame script (pokemon_tower.entrance_script) faded out and warped to Tower 1F until the Hall of Fame (flag 0x964).
Now: a trigger on the tile in front of the door runs the same fade + warp at once (so the lobby is never shown) and ends without doing anything once the flag is set, so after the Hall of Fame the door leads into the native Radio Tower lobby as before. The lobby's own frame script stays (harmless backup).
The sign (script 6 at tile 1430,236) shows Yellow's _LavenderTownPokemonTowerSignText ("May the Souls of / POKEMON Rest Easy / POKEMON TOWER"; the project writes Yellow's #MON as POKEMON, yellow_text.py) until the Hall of Fame, and the original "Kanto Radio Station" text after it, like the door: a wrapper script checks the flag and runs one of two copies of the sign's 21-byte TrainerTipsEx sequence (message 5 = the original text, untouched; the Tower text is a new message at the end of the bank); the sign's map event points to the wrapper.
Data files only (scripts a/0/1/2, events a/0/3/2, text a/0/2/7), changed in place: no ARM9 or overlay change.
Usage (from yellow-heartgold, PYTHONPATH=tools): lavender_tower_door.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import Script, events_decode, events_encode, trigger
from parcel_quest import append_bank
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE

LAVENDER, LOBBY = 53, 439
DOOR = (1429, 234)                      # Lavender warp 6 -> map 439
FRONT = (1429, 235)                     # the tile the player steps on before the door
GAME_CLEAR = 0x964
SIGN_MESSAGE, SIGN_SCRIPT, SIGN_TILE = 5, 6, (1430, 236)
SIGN_BODY = 21                           # SetSignpostMap 2,0 ; SetSignpostAction 3 ; WaitSignpostAction ; TrainerTips msg,0x800C ; CallStd ; End
SIGN_MSG_AT = 12                         # the message byte of TrainerTips inside that sequence
NEWLINE, SCROLL = 57344, 9661


def text(s):
    out = []
    for ch in s:
        if 'A' <= ch <= 'Z':
            out.append(299 + ord(ch) - 65)
        elif 'a' <= ch <= 'z':
            out.append(325 + ord(ch) - 97)
        elif ch == ' ':
            out.append(478)
        else:
            raise ValueError(ch)
    return out


def sign_codes():
    return text('May the Souls of') + [NEWLINE] + text('POKEMON Rest Easy') + [SCROLL] + text('POKEMON TOWER') + [65535]


def tower_arrival(rom, d):
    """(map, x, z, facing) of the Warp the lobby's frame script makes: Warp(map, 0, x, z, facing) with a Pokemon Tower map id."""
    sid = struct.unpack_from('<H', d, TABLE + LOBBY * 24 + 6)[0]
    raw = bytes(ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')]).files[sid])
    found = [struct.unpack_from('<5H', raw, p + 2) for p in range(len(raw) - 12) if raw[p:p + 2] == b'\xb0\x00' and 540 <= struct.unpack_from('<H', raw, p + 2)[0] <= 546]
    assert len(found) == 1, found
    return found[0]


def door_script(arrival):
    map_id, zero, x, z, facing = arrival
    s = Script().emit(32, GAME_CLEAR).jump('native', 1)
    s.emit(96).emit(174, 6, 6, 0, 0).emit(175).emit(176, map_id, zero, x, z, facing)
    s.emit(174, 6, 6, 1, 0).emit(175).emit(97).emit(2)
    s.label('native').emit(2)
    return s.finish()


def patch(rom):
    main = rom.loadArm9()
    d = bytes(main.sections[0].data)
    rec = TABLE + LAVENDER * 24
    sid, _, tid = struct.unpack_from('<3H', d, rec + 6)
    eid = struct.unpack_from('<H', d, rec + 16)[0]
    arrival = tower_arrival(rom, d)
    # the sign: the original message 5 stays, the Tower text is a new message, a wrapper script picks one
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    key, messages = decode_messages(bytes(texts.files[tid]))
    assert messages[SIGN_MESSAGE][:8] == text('Kanto Ra')[:8], 'message 5 is not the Radio Tower sign'
    tower_message = len(messages)
    assert tower_message <= 255, 'TrainerTips takes a byte message number'
    messages.append(sign_codes())
    texts.files[tid] = encode_messages(key, messages)
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    raw = bytes(scripts.files[sid])
    ptrs, i = [], 0
    while struct.unpack_from('<I', raw, i)[0] & 0xFFFF != 0xFD13:
        ptrs.append(i + 4 + struct.unpack_from('<I', raw, i)[0])
        i += 4
    old_body = raw[ptrs[SIGN_SCRIPT - 1]:ptrs[SIGN_SCRIPT - 1] + SIGN_BODY]
    assert old_body[:3] == b'\x38\x00\x02' and old_body[SIGN_MSG_AT - 1:SIGN_MSG_AT + 1] == b'\x00' + bytes([SIGN_MESSAGE]) and old_body[-2:] == b'\x02\x00', old_body.hex(' ')
    new_body = old_body[:SIGN_MSG_AT] + bytes([tower_message]) + old_body[SIGN_MSG_AT + 1:]
    sign = Script().emit(32, GAME_CLEAR).jump('radio', 1)
    sign.data.extend(new_body)
    sign.label('radio')
    sign.data.extend(old_body)
    # the door trigger
    bank, count = append_bank(scripts.files[sid], [door_script(arrival), sign.finish()])
    scripts.files[sid] = bytes(bank)
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    groups = events_decode(events.files[eid])
    assert not groups[3], 'Lavender already has triggers'
    assert any(struct.unpack_from('<4H', r, 0)[:2] == DOOR and struct.unpack_from('<4H', r, 0)[2] == LOBBY for r in groups[2]), 'the door warp is not where expected'
    groups[3] = [trigger(count + 1, FRONT[0], FRONT[1], 1, 0, 0)]
    rows = [k for k, r in enumerate(groups[0]) if struct.unpack_from('<I2i', r, 0) == (SIGN_SCRIPT,) + SIGN_TILE]
    assert len(rows) == 1, rows
    row = bytearray(groups[0][rows[0]])
    struct.pack_into('<I', row, 0, count + 2)
    groups[0][rows[0]] = bytes(row)
    events.files[eid] = events_encode(groups)
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    rom.files[rom.filenames.idOf('a/0/3/2')] = events.save()
    return dict(map=LAVENDER, trigger_script=count + 1, trigger_tile=FRONT, arrival=arrival, sign_script=count + 2, tower_message=tower_message)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
