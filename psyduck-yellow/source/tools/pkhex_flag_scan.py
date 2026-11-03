"""Scan the ROM scripts for flags (SetFlag/ClearFlag/CheckFlag u16) and variables (CompareVarValue/SetVar 0x4000-0x41FF) and list those NOT seen in the original HeartGold (byte-pattern scan: expect a few false positives among small ids). Usage (from yellow-heartgold): pkhex_flag_scan.py   (paths are hard-coded: ../Pokemon - HeartGold Version (USA).nds and build/0172-hideout-arrows/s.nds). Written 2026-11-03 for the PKHeX flag-label work."""
import struct, sys, collections
import ndspy.rom, ndspy.narc
FLAGOPS = {0x1E: 'set', 0x1F: 'clear', 0x20: 'check'}
def scan(path):
    rom = ndspy.rom.NintendoDSRom.fromFile(path)
    sc = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    flags, vars_ = collections.defaultdict(set), collections.defaultdict(set)
    for i, f in enumerate(sc.files):
        b = bytes(f)
        for p in range(0, len(b) - 5):
            op = struct.unpack_from('<H', b, p)[0]
            if op in FLAGOPS:
                v = struct.unpack_from('<H', b, p + 2)[0]
                if v < 0x1000: flags[v].add(i)
            elif op in (0x11, 0x29, 0x1B + 0):       # CompareVarValue var,value ; SetVar var,value
                v = struct.unpack_from('<H', b, p + 2)[0]
                if 0x4000 <= v < 0x4200: vars_[v].add(i)
    return flags, vars_, len(sc.files)
fn, vn, nn = scan('../Pokemon - HeartGold Version (USA).nds')
f2, v2, n2 = scan('build/0172-hideout-arrows/s.nds')
print('script banks: vanilla', nn, 'ROM', n2)
newf = sorted(set(f2) - set(fn)); newv = sorted(set(v2) - set(vn))
print('flags used (ROM)', len(f2), '| not seen in vanilla', len(newf))
print('vars used (ROM)', len(v2), '| not seen in vanilla', len(newv))
print('new flags:', ' '.join('%X' % x for x in newf[:120]))
print('new vars :', ' '.join('%X' % x for x in newv[:80]))
