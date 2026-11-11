"""TEST/READ ONLY: HeartGold script disassembler built from pret/pokeheartgold asm/macros/script.inc (download it first: curl -sL https://raw.githubusercontent.com/pret/pokeheartgold/master/asm/macros/script.inc -o script.inc).
Usage (from yellow-heartgold, PYTHONPATH=tools): hg_dis.py <rom> <script.inc> <script bank file> <script number> [more script numbers]
Prints every command reachable from the script (follows GoTo/GoToIf/Call). Commands whose macro has a conditional layout are printed as '?'."""
import re
import struct
import sys
import ndspy.narc
import ndspy.rom

SIZES = {'.byte': 1, '.short': 2, '.word': 4}


def load_table(path):
    table, name, ops, depth = {}, None, None, 0
    for line in open(path):
        s = line.strip()
        m = re.match(r'\.macro (\w+)\s*(.*)', s)
        if m:
            name, ops, depth, args = m.group(1), [], 0, m.group(2)
            continue
        if name is None:
            continue
        if s.startswith('.endm'):
            if ops and ops[0][0] == '.short':
                try:
                    code = int(ops[0][1].split('//')[0].strip(), 0)
                    table.setdefault(code, (name, [SIZES[d] for d, _ in ops[1:]], depth))
                except ValueError:
                    pass
            name = None
            continue
        if s.startswith('.if') or s.startswith('.else'):
            depth += 1
        mm = re.match(r'(\.byte|\.short|\.word)\s+(.*)', s)
        if mm:
            ops.append((mm.group(1), mm.group(2)))
    return table


def dis(bank, starts, table, n, seen=None):
    out, queue, done = [], [starts[n - 1]], set()
    while queue:
        i = queue.pop(0)
        while i < len(bank) and i not in done:
            done.add(i)
            op = struct.unpack_from('<H', bank, i)[0]
            if op not in table:
                out.append((i, '?op%d (0x%x)' % (op, op), []))
                break
            name, sizes, cond = table[op]
            args, j = [], i + 2
            for sz in sizes:
                args.append(int.from_bytes(bank[j:j + sz], 'little', signed=(sz == 4 and False)))
                j += sz
            out.append((i, name + ('*' if cond else ''), args))
            if name in ('End', 'EndScript'):
                break
            if name in ('GoTo', 'Call'):
                rel = struct.unpack_from('<i', bank, i + 2)[0]
                (queue if name == 'Call' else queue).append(i + 6 + rel)
                if name == 'GoTo':
                    break
            if name in ('GoToIf', 'CallIf'):
                rel = struct.unpack_from('<i', bank, i + 3)[0]
                queue.append(i + 7 + rel)
            i = j
    return sorted(out)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    table = load_table(sys.argv[2])
    bank = bytes(ndspy.narc.NARC(rom.getFileByName('a/0/1/2')).files[int(sys.argv[3])])
    cnt = next(i for i in range(400) if struct.unpack_from('<H', bank, 4 * i)[0] == 0xFD13)
    starts = [struct.unpack_from('<I', bank, 4 * i)[0] + 4 * i + 4 for i in range(cnt)]
    for n in map(int, sys.argv[4:]):
        print('--- script', n, 'at', starts[n - 1])
        for at, name, args in dis(bank, starts, table, n):
            print(' ', at, name, ' '.join(hex(a) if a > 255 else str(a) for a in args))
