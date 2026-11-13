"""ROM 0276: restore Steven Stone's Pewter Museum step of the Steven chain (owner order 2026-11-13: "Restore the Steven chain inside Yellow's rebuilt Pewter").
Finding (JOHTO-POSTGAME-PLAN.md items 89c/91): the Yellow Pewter rebuild replaced the museum's script bank (vanilla 755, 2756 bytes -> 1048, 856 bytes) and event file (424 -> 565): the Steven actors, the variable 0x4130 = 5 step
and the Enigma Stone scene are gone, so Steven Stone's story variable 0x4130 stops at 4 (Hoenn starter given in Saffron) and Saffron's Silph Co. Steven (stages 6/7, the Beldum trade) never appears.
This tool restores the STANDARD chain step only: the vanilla actor 7 of the museum (sprite 421, "Steven after the Latis" with hide flag 0x317, at the vanilla spot (16, 4)) and its script 19 = HeartGold's own text 13 of the museum text bank and SetVar 0x4130 = 5.
 - The museum interior is HeartGold's native one (the Yellow museum events use the same coordinates), so the vanilla spot is valid.
 - Visibility needs no new logic: flag 0x317 is set by the new-game flag list and cleared by Saffron's stage 4 script (copies of the vanilla scripts are in the ROM); Saffron's stage 5 step hides the house Steven again. No new flag or variable is used.
 - NOT restored (needs the Enigma Stone, a Mystery Gift item that nothing in this game gives): the museum's Steven + Enigma Stone scene (actor 6, flag 0x308, variable 0x4083 stages 1-2) and Pewter City's Steven / Latios / Latias scenes (stages 3-5, vanilla bank 750); Latias and Latios stay obtainable through the Vermilion roamer scene and the Hall-of-Fame hub.
Usage (from yellow-heartgold, PYTHONPATH=tools): steven_museum.py <in.nds> <out.nds> <vanilla HeartGold.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from johto_step3e import A
from map_edit import MapEdit
from prototype import decode_messages

MUSEUM, STEVEN_SPRITE, AFTER_LATIS_FLAG, STEVEN_VAR = 471, 421, 0x317, 0x4130
VANILLA_TEXT_BANK, VANILLA_MESSAGE, VANILLA_EVENT, VANILLA_ACTOR = 464, 13, 424, 7
PLAY_SE, SE_SELECT, LOCK_ALL, RELEASE_ALL, END = 73, 1500, 96, 97, 2


def talk_script(message_index):
    """PlaySE(select); LockAll; text; WaitButton; CloseMsg; SetVar 0x4130 = 5; ReleaseAll; End (vanilla T03R0101_019)."""
    a = A()
    a.op(PLAY_SE, SE_SELECT).op(LOCK_ALL).msg(message_index)
    a.set_var(STEVEN_VAR, 5)
    a.op(RELEASE_ALL).op(END)
    return a.build(0)


def patch(rom, vanilla_path):
    vanilla = ndspy.rom.NintendoDSRom.fromFile(vanilla_path)
    vtext = ndspy.narc.NARC(vanilla.getFileByName('a/0/2/7'))
    _, vrows = decode_messages(vtext.files[VANILLA_TEXT_BANK])
    vevents = ndspy.narc.NARC(vanilla.getFileByName('a/0/3/2'))
    from opening import events_decode
    vactor = bytes(events_decode(bytes(vevents.files[VANILLA_EVENT]))[1][VANILLA_ACTOR])
    vw = struct.unpack('<16H', vactor)
    assert vw[1] == STEVEN_SPRITE and vw[4] == AFTER_LATIS_FLAG, vw          # the vanilla "Steven after the Latis" actor

    e = MapEdit(rom, MUSEUM)
    assert not any(struct.unpack_from('<H', bytes(r), 8)[0] == AFTER_LATIS_FLAG for r in e.groups[1]), 'the museum already has the actor'
    e.rows.append(list(vrows[VANILLA_MESSAGE]))                               # HeartGold's own text, copied word for word
    index = len(e.rows) - 1
    assert index < 255
    sid = e.script(lambda add: talk_script(index))
    ids = [struct.unpack_from('<H', bytes(r), 0)[0] for r in e.groups[1]]
    new_id = max(ids) + 1
    record = bytearray(vactor)
    struct.pack_into('<H', record, 0, new_id)                                 # actor id
    struct.pack_into('<H', record, 10, sid)                                   # its script (the new one)
    e.groups[1].append(bytes(record))
    e.save()
    return dict(message=index, script=sid, actor=new_id, spot=(vw[12], vw[13]))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
