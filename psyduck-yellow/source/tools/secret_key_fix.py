"""Prototype 0197: the Secret Key works from the Key Items pocket and from PKHeX (owner report 2026-11-08: a Secret Key injected with PKHeX still left Cinnabar Gym's door locked).
Cause: item 872 (the Mansion's key, what the B1F ball gives and what the gym door tests with HaveItem) had an all-zero item record (and no icon), so the engine files it in the ordinary Items pocket; HaveItem looks in the pocket the item's record names,
so a copy sitting in the Key Items pocket (what PKHeX shows for a key item) is invisible to the door. The engine also has a native, proper key item called "Secret Key" (467) that PKHeX lists by that name.
Fix: item 872 gets the record and icon of 467 (a key item: Key Items pocket, no toss, no use), and the gym door accepts EITHER 872 or 467. The door's text and the step back are Yellow's, unchanged.
Not done on purpose: the Card Key (876, Silph Co.) has the same empty record (saves that already hold it in the Items pocket would lose it if changed): to decide with the owner.
Usage (from yellow-heartgold, PYTHONPATH=tools): secret_key_fix.py <in.nds> <out.nds> <pokeyellow source>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import yellow_text
from map_edit import MapEdit
from opening import Script, end

MANSION_KEY, NATIVE_KEY, MAP = 872, 467, 57


def patch(rom, source):
    items = ndspy.narc.NARC(rom.getFileByName('a/0/1/7'))
    assert bytes(items.files[MANSION_KEY]) == bytes(36), 'the Mansion key already has a record'
    assert bytes(items.files[NATIVE_KEY]) != bytes(36), 'the native Secret Key has no record'
    items.files[MANSION_KEY] = bytes(items.files[NATIVE_KEY])
    rom.setFileByName('a/0/1/7', items.save())
    gfx = ndspy.narc.NARC(rom.getFileByName('a/0/1/8'))
    for k in (2, 3):
        gfx.files[MANSION_KEY * 2 + k] = bytes(gfx.files[NATIVE_KEY * 2 + k])
    rom.setFileByName('a/0/1/8', gfx.save())
    edit = MapEdit(rom, MAP)
    msg = edit.message(yellow_text.message(source, 'CinnabarIsland', '_CinnabarIslandDoorIsLockedText'))

    def lock(add):
        s = Script().emit(96)
        for item in (MANSION_KEY, NATIVE_KEY):
            s.emit(128, item, 1, 0x800C).compare(0x800C, 1).jump('open', 1)
        s.msg(msg).movement(255, 'back').emit(95)
        end(s)
        s.label('open')
        end(s)
        s.moves('back', [(13, 1)])
        return s.finish()
    entry = edit.script(lock)
    rows = edit.groups[3]
    assert len(rows) == 1 and struct.unpack_from('<2h', rows[0], 2) == (1048, 493), [r.hex(' ') for r in rows]
    row = bytearray(rows[0])
    struct.pack_into('<H', row, 0, entry)
    edit.groups[3] = [bytes(row)]
    edit.save()
    return dict(map=MAP, script=entry, message=msg, items=(MANSION_KEY, NATIVE_KEY))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
