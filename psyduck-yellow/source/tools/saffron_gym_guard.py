"""A Rocket guard blocks Saffron's gym door until the Silph Co. takeover is done (owner order 2026-11-08: the Silph takeover should also gate the Saffron Gym).
Saffron City (map 59): the gym's door tile (1328,204) can only be entered from (1328,205) (walls on both sides). A Rocket guard (sprite 334, facing south) stands on (1328,205) and says Yellow's own Saffron Rocket line
(_SaffronCityRocket1Text: "What do you want? Get lost!"). His hide flag is the Silph Co. takeover flag 0xA68 (silph.GIOVANNI_DONE, set when Giovanni is beaten there), so he leaves for good after the takeover: no new flag, no variable, no script test.
Usage (from yellow-heartgold, PYTHONPATH=tools): saffron_gym_guard.py <in.nds> <out.nds> <pokeyellow source>"""
import struct
import sys
import ndspy.rom
import yellow_text
from map_edit import MapEdit
from opening import Script, actor, end

MAP, GUARD_SPRITE, HIDE, SPOT = 59, 334, 0xA68, (1328, 205)


def patch(rom, source):
    edit = MapEdit(rom, MAP)
    msg = edit.message(yellow_text.message(source, 'SaffronCity', '_SaffronCityRocket1Text'))
    entry = edit.script(lambda add: end(Script().emit(96).emit(104).msg(msg)).finish())
    taken = {struct.unpack_from('<H', a, 0)[0] for a in edit.groups[1]}
    assert not any(struct.unpack_from('<2H', a, 24) == SPOT for a in edit.groups[1]), 'tile already occupied'
    aid = max(taken) + 1
    edit.groups[1].append(actor(aid, GUARD_SPRITE, entry, SPOT[0], SPOT[1], HIDE, 1))
    edit.save()
    return dict(map=MAP, script=entry, message=msg, actor=aid, hide_flag=hex(HIDE))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
