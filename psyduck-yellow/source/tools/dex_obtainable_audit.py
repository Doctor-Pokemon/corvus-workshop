import struct, collections
import ndspy.rom, ndspy.narc
from prototype import decode_messages
rom = ndspy.rom.NintendoDSRom.fromFile('build/0222-field-kit/s.nds')
texts = ndspy.narc.NARC(rom.getFileByName('a/0/2/7'))
def ch(c):
    if 0x121<=c<=0x12A: return chr(48+c-0x121)
    if 0x12B<=c<=0x144: return chr(65+c-0x12B)
    if 0x145<=c<=0x15E: return chr(97+c-0x145)
    return {0x1AC:'?',0x1B1:'.',0x1BE:'-',0x1B3:"'",0x1AE:'-',0x1BF:'.',0xE2:'e'}.get(c,'')
_, rows = decode_messages(texts.files[237])
name = {i:''.join(ch(c) for c in r if c!=65535) for i,r in enumerate(rows)}
evo = [bytes(f) for f in ndspy.narc.NARC(rom.getFileByName('a/0/3/4')).files]
def evos(s):
    out=[]
    for k in range(9):
        m,p,t = struct.unpack_from('<3H', evo[s], 6*k)
        if m and t: out.append(t & 0x7FF)
    return out
enc = [bytes(f) for f in ndspy.narc.NARC(rom.getFileByName('a/0/3/7')).files]
wild=set()
for f in enc:
    r=f[:6]
    if r[0]:
        for i in range(36): wild.add(struct.unpack_from('<H',f,20+2*i)[0]&0x7FF)
    for rate,at,n in ((r[1],100,5),(r[2],120,2),(r[3],128,5),(r[4],148,5),(r[5],168,5)):
        if rate:
            for k in range(n): wild.add(struct.unpack_from('<BBH',f,at+4*k)[2]&0x7FF)
wild.discard(0)
def dexnum(s):
    if s<=493: return s
    if 544<=s<=1076: return s-50
    return None
reach=set(wild); st=list(wild)
while st:
    s=st.pop()
    for t in evos(s):
        if t not in reach: reach.add(t); st.append(t)
dex_ids=[s for s in range(1,1077) if dexnum(s)]
print('dex species ids', len(dex_ids), 'wild raw', len(wild), 'wild+evo', len(reach))
miss=[s for s in dex_ids if s not in reach]
print('missing by wild+evolution only:', len(miss))
# group by generation
gens=[(1,151),(152,251),(252,386),(387,493),(494,649),(650,721),(722,809),(810,905),(906,1025)]
for g,(a,b) in enumerate(gens,1):
    tot=[s for s in dex_ids if a<=dexnum(s)<=b]
    mi=[s for s in tot if s not in reach]
    print('gen',g,'total',len(tot),'missing',len(mi))
print('gen1-3 missing names:', [name[s] for s in miss if dexnum(s)<=386])
import json; json.dump({'wild':sorted(wild),'miss':miss}, open('/tmp/claude-1000/-home-thatanarchydude-code-corvus-workshop/3489ee22-26b5-4abc-99aa-c427002fe683/scratchpad/dex/out.json','w'))
