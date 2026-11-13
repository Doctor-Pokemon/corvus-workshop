"""ROM 0277: the Route 47 Hiker gives the ENIGMA STONE (owner order 2026-11-13: "have the Hiker outside the Embedded Tower entrance give it to the player ... If you REALLY wanna investigate a MYSTERY though, have I got a GIFT for you! Here. I found this while I was wandering around in there.").
The Enigma Stone (item 536) is a Mystery Gift item in HeartGold and nothing in this game gave it, so the Steven Stone / Latios / Latias event of the Pewter Museum could not start (JOHTO-POSTGAME-PLAN.md items 91, 92).
The Hiker is actor 4 of Route 47 (map 151, script bank 1377, script 2): he tells the story of the tower that joins the sky, the land and the sea (HeartGold's own text 0 first time, text 1 afterwards).
After either text a helper runs: it gives the stone once: no stone in the bag AND the Pewter Museum variable 0x4083 still 0 (the scene sets it to 2 when it takes the stone), so no new flag is needed; key items cannot be tossed, so a player who holds it never gets a second one.
The gift line is the owner's own words. The receipt and the bag-full case are HeartGold's own standard script (std_obtain_item_verbose).
Usage (from yellow-heartgold, PYTHONPATH=tools): enigma_hiker.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from johto_step3d import install
from johto_step3d import starts as bank_starts
from johto_step3e import A
from map_edit import MapEdit

ROUTE_47, HIKER_SCRIPT = 151, 2
ENIGMA_STONE, PEWTER_VAR = 536, 0x4083
STD_OBTAIN_ITEM = 2008
LINE = "If you REALLY wanna investigate a\nMYSTERY though, have I got a GIFT\nfor you! Here. I found this while I\nwas wandering around in there."
WAIT, CLOSE, RELEASE, END, SETFLAG, GOTO = 50, 53, 97, 2, 30, 22


def helper(base, message):
    a = A()
    a.raw(struct.pack('<2H', WAIT, CLOSE))
    a.op(128, ENIGMA_STONE, 1, 0x800C).compare(0x800C, 0).jump('nostone', 1)    # HasItem: 0 = no stone yet
    a.jump('done')
    a.label('nostone').compare(PEWTER_VAR, 0).jump('give', 1)                    # the museum scene has not been through yet
    a.jump('done')
    a.label('give').msg(message)
    a.set_var(0x8004, ENIGMA_STONE).set_var(0x8005, 1).op(20, STD_OBTAIN_ITEM)
    a.label('done').op(RELEASE).op(END)
    return a.build(base)


def patch(rom):
    e = MapEdit(rom, ROUTE_47)
    message = e.message(LINE)
    size = len(helper(0, message))
    ids, addrs, _ = install(e, [size])                                           # the header may grow: find everything AFTER installing
    bank = bytearray(e.bank)
    st = bank_starts(bytes(bank))
    sid = struct.unpack_from('<H', e.groups[1][4], 10)[0]                         # actor 4 = the Hiker
    begin = st[sid - 1]
    end = min([s for s in st if s > begin] + [len(bank)])
    body = bytes(bank[begin:end])
    first = struct.pack('<2H', WAIT, CLOSE) + struct.pack('<2H', SETFLAG, 337) + struct.pack('<2H', RELEASE, END)     # text 0 path (sets the "told" flag)
    again = struct.pack('<HB', 45, 1) + struct.pack('<2H', WAIT, CLOSE) + struct.pack('<2H', RELEASE, END)           # text 1 path
    i1 = body.find(first)
    i2 = body.find(again)
    assert i1 >= 0 and i2 >= 0 and body.count(first) == 1 and body.count(again) == 1, (i1, i2)
    code = helper(addrs[0], message)
    assert len(code) == size
    bank[addrs[0]:addrs[0] + size] = code
    p1 = begin + i1                                                              # SetFlag 337, GoTo helper, pad
    bank[p1:p1 + 4] = struct.pack('<2H', SETFLAG, 337)
    bank[p1 + 4:p1 + 10] = struct.pack('<Hi', GOTO, addrs[0] - (p1 + 10))
    bank[p1 + 10:p1 + 12] = b'\0\0'
    p2 = begin + i2 + 3                                                          # after the NPCMsg 1: GoTo helper, pad
    bank[p2:p2 + 6] = struct.pack('<Hi', GOTO, addrs[0] - (p2 + 6))
    bank[p2 + 6:p2 + 8] = b'\0\0'
    e.bank = bytes(bank)
    e.save()
    return dict(map=ROUTE_47, script=sid, helper=ids[0], message=message, first_tail=p1, again_tail=p2)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
