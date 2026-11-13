"""ROM 0268: the Magnet Train gets its power (flag 0x118) with the first Kanto Hall of Fame, so the Pass quest can be played (owner "Agreed", 2026-11-12).
FINDING (ROM 0264 test): no script gives the Pass (item 480) by itself; HeartGold's chain is: Machine Part (item 481) -> the Power Plant manager (maps 489 / 673, bank 196) takes it and sets the flag 0x118 ("the Magnet Train has power";
the Saffron station attendant tests it) -> the Saffron Copycat (map 405, bank 841) tells of her lost Clefairy doll and sets 0x119 -> the Vermilion Pokemon Fan Club (map 362, bank 1137, script 3) hands over the Lost Item (479) ->
back to the Copycat: she takes it and gives the Pass. The Machine Part's giver (script bank 760: Cerulean City in HeartGold) is no longer referenced by any map header in this ROM (our Cerulean is Yellow's), so 0x118 is never set and the whole chain is dead.
FIX: the first Kanto Hall of Fame sets 0x118 too. The league-ending script (map 306, bank 1309 script 1) already calls tools/embedded_tower.py's helper at one site (it replaced `SetVar 0x413E 1`); that Call is re-pointed to a new helper
that sets 0x118 and then calls the old helper. Nothing else changes: the Copycat, the Fan Club and the attendant are HeartGold's own scripts, so the Pass appears after the Kanto League win (the train itself still needs the Pass and the
Johto arrival, johto_step1c / 1d). No new flag is allocated (0x118 is HeartGold's own).
Usage (from yellow-heartgold, PYTHONPATH=tools): magnet_power.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from johto_step1b import script_ranges
from opening import Script
from parcel_quest import append_bank

BANK = 1309
POWER = 0x118
SET_FLAG, CALL, RETURN = 30, 26, 27


def patch(rom):
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    old = bytes(scripts.files[BANK])
    starts, ends = script_ranges(old)
    pat = struct.pack('<3H', 41, 0x413E, 1)
    # the old helper = the (appended) script that holds `SetVar HOFN 1` outside the league script itself
    homes = [i for i, (a, z) in enumerate(zip(starts, ends)) if old.find(pat, a, z) >= 0]
    assert len(homes) == 1, homes
    helper_start = starts[homes[0]]
    calls = [p for p in range(len(old) - 6) if struct.unpack_from('<H', old, p)[0] == CALL and p + 6 + struct.unpack_from('<i', old, p + 2)[0] == helper_start]
    assert len(calls) == 1, calls
    # new helper B: SetFlag POWER, Call old helper, Return  (its Call offset is computed once its own address is known: it is the last script, appended)
    probe, count = append_bank(old, [Script().emit(SET_FLAG, POWER).emit(CALL, 0, 0).emit(RETURN).finish()])
    probe = bytearray(probe)
    shift = 4
    new_start = count * 4 + 4 + struct.unpack_from('<I', probe, count * 4)[0]
    # locate the Call inside the new script (SetFlag = 4 bytes, then Call = 2 + 4 bytes)
    call_at = new_start + 4
    assert struct.unpack_from('<H', probe, call_at)[0] == CALL, probe[call_at:call_at + 6].hex()
    old_helper_new = helper_start + shift
    struct.pack_into('<i', probe, call_at + 2, old_helper_new - (call_at + 6))
    site = calls[0] + shift
    assert struct.unpack_from('<H', probe, site)[0] == CALL
    struct.pack_into('<i', probe, site + 2, new_start - (site + 6))
    scripts.files[BANK] = bytes(probe)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    return dict(bank=BANK, call_site=site, old_helper=old_helper_new, new_helper=new_start, script=count + 1)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
