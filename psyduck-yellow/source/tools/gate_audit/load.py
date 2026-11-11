import struct,sys,collections,pickle,ndspy.rom,ndspy.narc
import map_dump as gd, map_header_extension as ext
from opening import events_decode
rom=ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
total=ext.NATIVE_COUNT+len(ext.records(rom)); print('maps',total,'native',ext.NATIVE_COUNT)
mats=ndspy.narc.NARC(rom.getFileByName('a/0/4/1')); lands=ndspy.narc.NARC(rom.getFileByName('a/0/6/5'))
ev=ndspy.narc.NARC(rom.getFileByName('a/0/3/2'))
mcache={}
def grid(mid_):
    if mid_ in mcache: return mcache[mid_]
    mat=bytes(mats.files[mid_]); w,h,hd,ht,n=mat[:5]
    ids=struct.unpack_from('<%dH'%(w*h),mat,5+n+w*h*(2*hd+ht))
    free,attr={},{}
    for cz in range(h):
        for cx in range(w):
            if ids[cz*w+cx]>=len(lands.files): continue
            land=bytes(lands.files[ids[cz*w+cx]])
            bgs=4+struct.unpack_from('<H',land,18)[0] if land[16:18]==b'\x34\x12' else 0
            perm=land[16+bgs:16+bgs+2048]
            for lz in range(32):
                for lx in range(32):
                    o=(lz*32+lx)*2; t=(cx*32+lx,cz*32+lz); attr[t]=perm[o]
                    if not perm[o+1]&0x80: free[t]=perm[o]
    mcache[mid_]=free; return free
maps={}
for m in range(total):
    rec=gd.record(rom,m)
    if not rec[20]&1: continue
    matrix=struct.unpack_from('<H',rec,4)[0]; eid=struct.unpack_from('<H',rec,16)[0]
    try: g=events_decode(bytes(ev.files[eid]))
    except Exception: continue
    maps[m]=dict(matrix=matrix,actors=[(struct.unpack_from('<7H',a,0),struct.unpack_from('<2H',a,24)) for a in g[1]],
      warps=[struct.unpack_from('<4H',w,0) for w in g[2]],bgs=[struct.unpack_from('<2i',b,4) for b in g[0]],
      trig=[struct.unpack_from('<HhhHHHHH',t,0) for t in g[3]],mapsec=rec[18],sid=struct.unpack_from('<H',rec,6)[0])
print(len(maps),'kanto maps; matrices',collections.Counter(v['matrix'] for v in maps.values()).most_common(5))
pickle.dump(maps,open(sys.argv[2],'wb'))
