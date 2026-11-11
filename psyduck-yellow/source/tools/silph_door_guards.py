"""Two Rocket guards block Silph Co.'s door until the Rocket Hideout run is done (owner order 2026-11-08: "a Rocket Grunt blocks the way into Silph Co. until you defeat Giovanni at the Rocket Hideout ... ensure the story beats are hit in the intended order").
Saffron City (map 59): Silph Co.'s two door tiles (1308,229) and (1309,229) can only be entered from the tiles directly south of them, (1308,230) and (1309,230). A Rocket guard (sprite 334, the Game Corner guard's sprite) stands on each, facing south,
and says Yellow's own Saffron guard line (_SaffronCityRocket8Text: "I'm a security guard. Suspicious kids I don't allow in!"). Their hide flag is the Rocket Hideout's own "Giovanni done" flag 0xA6D (rocket_hideout.GIOVANNI_HIDE: set when Giovanni has given you the Silph Scope),
so they disappear for good once the Hideout is finished: no new flag, no variable, no script test. They are plain talkers (no battle). Story order enforced: Hideout (Silph Scope) -> Tower (Flute) -> Silph Co. takeover -> the rest of the badges -> Viridian Gym (viridian_guard.py).
Usage (from yellow-heartgold, PYTHONPATH=tools): silph_door_guards.py <in.nds> <out.nds> <pokeyellow source>"""
import struct
import sys
import ndspy.rom
import yellow_text
from map_edit import MapEdit
from opening import Script, actor, end

MAP, GUARD_SPRITE, HIDE = 59, 334, 0xA6D
SPOTS = ((1308, 230), (1309, 230))


def patch(rom, source):
    edit = MapEdit(rom, MAP)
    line = yellow_text.message(source, 'SaffronCity', '_SaffronCityRocket8Text')
    msg = edit.message(line)
    entry = edit.script(lambda add: end(Script().emit(96).emit(104).msg(msg)).finish())
    taken = {struct.unpack_from('<H', a, 0)[0] for a in edit.groups[1]}
    ids = [max(taken) + 1, max(taken) + 2]
    for aid, (x, z) in zip(ids, SPOTS):
        assert not any(struct.unpack_from('<2H', a, 24) == (x, z) for a in edit.groups[1]), 'tile already occupied'
        edit.groups[1].append(actor(aid, GUARD_SPRITE, entry, x, z, HIDE, 1))
    edit.save()
    return dict(map=MAP, script=entry, message=msg, actors=ids, hide_flag=hex(HIDE))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
