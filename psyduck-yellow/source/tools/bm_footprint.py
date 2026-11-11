"""TEST ONLY: bounding box (box test: position and size in tiles) of building models in a/0/4/0. Usage: bm_footprint.py <rom> <model id> [...]
The NSBMD model block carries: u32 size, 4 offsets, 8 bytes of counts/flags, fx32 posScale, fx32 invPosScale, 4 u16 counts, s16 x/y/z, u16 w/h/d (fx 4.12), fx32 boxPosScale, fx32 boxInvPosScale; 1.0 unit = 4 tiles here."""
import re
import struct
import sys
import ndspy.narc
import ndspy.rom


def box(b):
    k = b.find(b'MDL0')
    base = k + 8
    for p in range(base, base + 80, 4):
        off = struct.unpack_from('<I', b, p)[0]
        at = base + off if off < len(b) else 0
        if 0 < off < len(b) - 64:
            for rel in (0, k):
                a = rel + off
                size, sbc, mat, shp, evp = struct.unpack_from('<5I', b, a)
                if 0x40 < size < len(b) and 0 < sbc < size and 0 < mat < size and 0 < shp < size and sbc < mat < shp:
                    pos_scale = struct.unpack_from('<i', b, a + 0x1C)[0] / 4096
                    bx, by, bz = struct.unpack_from('<3h', b, a + 0x2C - 0)
                    return a, pos_scale, (bx, by, bz), struct.unpack_from('<3H', b, a + 0x32), struct.unpack_from('<2i', b, a + 0x38)
    return None


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    bm = ndspy.narc.NARC(rom.getFileByName('a/0/4/0'))
    for i in map(int, sys.argv[2:]):
        b = bytes(bm.files[i])
        r = box(b)
        if not r:
            print(i, 'no box'); continue
        a, ps, (x, y, z), (w, h, d), (bs, ibs) = r
        s = bs / 4096
        print(i, 'at', a, 'box pos', [round(v / 4096 * s * 4, 2) for v in (x, y, z)], 'size tiles', [round(v / 4096 * s * 4, 2) for v in (w, h, d)], 'raw', (x, y, z), (w, h, d), bs)
