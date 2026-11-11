"""Prototype 0208: Fly to New Bark Town lands in New Bark Town (owner report 2026-11-09, real 3DS: Fly from Olivine, picking New Bark Town, landed in PALLET TOWN; Fly to Indigo Plateau from Johto also ended in Pallet with a "NEW BARK TOWN" banner).
Cause (static, compared with the original HeartGold ROM): the engine's fly-point table (ARM9 0x020F9E80, 30 entries of 0x12 bytes) entry 0 is New Bark Town's (Fly point 11). Fields: +0 fly point/flags, +2 the Pokemon Center / home map used for the respawn point, +4 (unknown), +6 the town map that triggers the entry, +8/+10 trigger tile, +12/+14/+16 the Fly LANDING (map, x, z). The 0037 engine build had made entry 0 a Pallet Town entry: home map 503 (Red's house 1F), tiles 1033/364 and landing map 49 (Pallet). fly_point_table_fix.py (0158) put only the trigger map (+6) back to 60, so entering New Bark sets the flag, but picking New Bark on the Fly map still warped to Pallet (map 49 at Pallet's tile). The Fly code also falls back to entry 0 for a pick it cannot resolve, which explains Indigo -> Pallet and the New Bark banner.
Fix: entry 0 returns completely to HeartGold's original row: home map 63 (the player's house 1F in New Bark Town), trigger tile (695, 397), landing map 60 at (695, 397). Pallet keeps its own entry (12): Fly point 0, map 49, tile (1033, 364), which is unchanged.
Known side effect (intended, original behaviour): entering New Bark Town now sets the respawn/home point to the New Bark house like in HeartGold.
Usage (from yellow-heartgold, PYTHONPATH=tools): fly_point_dest_fix.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom

TABLE = 0x020F9E80
STRIDE = 0x12
BAD = (779, 503, 2054, 60, 1033, 364, 49, 1033, 364)
ORIGINAL = (779, 63, 2054, 60, 695, 397, 60, 695, 397)


def patch(rom):
    main = rom.loadArm9()
    d = main.sections[0].data = bytearray(main.sections[0].data)
    at = TABLE - main.sections[0].ramAddress
    now = struct.unpack_from('<9H', d, at)
    assert now == BAD, ('entry 0 is not the known-bad row', now)
    pallet = struct.unpack_from('<9H', d, at + 12 * STRIDE)
    assert pallet == (512, 49, 3336, 49, 1033, 364, 49, 1033, 364), pallet
    struct.pack_into('<9H', d, at, *ORIGINAL)
    rom.arm9 = main.save(compress=True)
    return dict(entry0=ORIGINAL)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
