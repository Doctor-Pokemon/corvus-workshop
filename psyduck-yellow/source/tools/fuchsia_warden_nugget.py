"""Fuchsia: the Warden's Nugget routine (owner order 2026-11-04, option D). Strength now comes from Sabrina, so he cannot reward the Gold Teeth with HM04.
 - First time you give him the GOLD TEETH: Yellow's lines (gave the teeth, popped them in, thanks), then the first pun ("Ha! I meant to reward you with STRENGTH, but I see you have that already! So take this NUGGET instead. ..."), a NUGGET, and the 'helped' flag 0xA6C.
 - Afterwards, once per day: the owner's text ("I'd love to give you some NUGGET of wisdom, but I can't even remember to grab my GOLD TEETH when I leave the house! We'll just have to settle for this.") and another NUGGET. The once-a-day state is a DAILY flag (0xAAC, in the range the game clears every day, unused in every script bank and actor list); the first Nugget sets it too. A second visit the same day gets the short follow-up line.
 - NOT done: the owner's "every day after 12pm": the script command table has no hour-of-day check (found 2026-11-04), so it is once per day at any time for now.
Usage (from yellow-heartgold, PYTHONPATH=tools): fuchsia_warden_nugget.py <in.nds> <out.nds> <pokeyellow source>"""
import struct
import sys
import ndspy.rom
import yellow_text
from map_edit import MapEdit
from opening import Script, end

WARDEN_MAP, GOLD_TEETH, WARDEN_GIVEN, DAILY, NUGGET = 481, 877, 0xA6C, 0xAAC, 92
FIRST = ("Ha! I meant to reward you with STRENGTH, but I see you have that already! So take this NUGGET instead. "
         "Consider it a NUGGET of wisdom: never leave your teeth lying around!")
DAILY_TEXT = ("I'd love to give you some NUGGET of wisdom, but I can't even remember to grab my GOLD TEETH when I leave the house! "
              "We'll just have to settle for this.")                  # the owner's text; "when I leave" corrects "when leave"
TODAY = 'Consider it a NUGGET of wisdom: never leave your teeth lying around!'
GOT = '{PLAYER} received a NUGGET!'


def patch(rom, source):
    m = lambda l: yellow_text.message(source, 'WardensHouse', l).rstrip('@')
    edit = MapEdit(rom, WARDEN_MAP)

    def build(msg):
        gib = msg(m('_WardensHouseWardenGibberish1Text') + '\r' + m('_WardensHouseWardenGibberish2Text'))
        gave = msg(m('_WardensHouseWardenGaveTheGoldTeethText'))
        popped = msg(m('_WardensHouseWardenTeethPoppedInHisTeethText'))
        thanks = msg(m('_WardensHouseWardenThanksText'))
        first = msg(FIRST)
        daily = msg(DAILY_TEXT)
        today = msg(TODAY)
        got = msg(GOT)
        full = msg(m('_WardensHouseWardenHM04NoRoomText'))
        s = Script().emit(96).emit(104).emit(32, WARDEN_GIVEN).jump('helped', 1)
        s.emit(126, GOLD_TEETH, 1, 0x800C).compare(0x800C, 0).jump('noteeth', 1)
        s.msg(gave).msg(popped).msg(thanks).msg(first)
        s.emit(125, NUGGET, 1, 0x800C).compare(0x800C, 0).jump('full', 1)
        s.emit(30, WARDEN_GIVEN).emit(30, DAILY).emit(78, 1185).msg(got).emit(79)
        end(s)
        s.label('noteeth').msg(gib)
        end(s)
        s.label('full').msg(full)
        end(s)
        s.label('helped').emit(32, DAILY).jump('today', 1)
        s.msg(daily)
        s.emit(125, NUGGET, 1, 0x800C).compare(0x800C, 0).jump('full', 1)
        s.emit(30, DAILY).emit(78, 1185).msg(got).emit(79)
        end(s)
        s.label('today').msg(today)
        end(s)
        return s.finish()

    entry = edit.script(build)
    i = max(range(len(edit.groups[1])), key=lambda k: struct.unpack_from('<H', edit.groups[1][k], 10)[0])
    edit.groups[1][i] = bytearray(edit.groups[1][i])
    struct.pack_into('<H', edit.groups[1][i], 10, entry)
    edit.save()
    return dict(map=WARDEN_MAP, script=entry, actor=i, daily_flag=hex(DAILY))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
