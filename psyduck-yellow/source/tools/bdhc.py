"""BDHC (the per-chunk terrain height table of HeartGold land files): parse and write.
Layout (little endian): 'BDHC', then six u16 counts: points, slopes, constants, plates, strips, access.
 points: (s32 x, s32 z) 16.16 fixed, tile units from the chunk centre (-16..16); slopes: 3 x s32 normal (nx, ny, nz) 16.16; constants: s32 16.16;
 plates: 4 x u16 = point index of corner 1, point index of corner 2, slope index, constant index; strips: s32 z (16.16, the strip's far edge), u16 plate count, u16 first access index; access: u16 plate indices.
Height on a plate at (x, z): y = (c - nx*x - nz*z) / ny (flat plate: n = (0, 1, 0), y = c). Parsed from the stock Cinnabar chunk; see the plan entry 2026-11-08 CINNABAR RAISED LAND."""
import struct


def parse(b):
    assert b[:4] == b'BDHC'
    npt, nsl, nco, npl, nst, nac = struct.unpack_from('<6H', b, 4)
    at = 16
    pts = [struct.unpack_from('<2i', b, at + 8 * i) for i in range(npt)]
    at += 8 * npt
    slopes = [struct.unpack_from('<3i', b, at + 12 * i) for i in range(nsl)]
    at += 12 * nsl
    consts = [struct.unpack_from('<i', b, at + 4 * i)[0] for i in range(nco)]
    at += 4 * nco
    plates = [struct.unpack_from('<4H', b, at + 8 * i) for i in range(npl)]
    at += 8 * npl
    strips = [struct.unpack_from('<iHH', b, at + 8 * i) for i in range(nst)]
    at += 8 * nst
    access = [struct.unpack_from('<H', b, at + 2 * i)[0] for i in range(nac)]
    at += 2 * nac
    return dict(points=pts, slopes=slopes, consts=consts, plates=plates, strips=strips, access=access, size=at)


def build(points, slopes, consts, plates, strips, access):
    out = b'BDHC' + struct.pack('<6H', len(points), len(slopes), len(consts), len(plates), len(strips), len(access))
    out += b''.join(struct.pack('<2i', *p) for p in points)
    out += b''.join(struct.pack('<3i', *s) for s in slopes)
    out += b''.join(struct.pack('<i', c) for c in consts)
    out += b''.join(struct.pack('<4H', *p) for p in plates)
    out += b''.join(struct.pack('<iHH', *s) for s in strips)
    out += b''.join(struct.pack('<H', a) for a in access)
    return out


def fx(v):
    return v / 65536.0
