import struct,sys,collections,pickle,ndspy.rom,ndspy.narc
import map_dump as gd
from prototype import decode_messages
rom=ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
maps=pickle.load(open(sys.argv[2],'rb'))
sys.argv=[sys.argv[0],sys.argv[1],'/dev/null']
exec(open(sys.argv[0].replace('reach.py','load.py')).read().split("maps={}")[0].split("rom=ndspy")[0]) if False else None
import map_header_extension as ext
mats=ndspy.narc.NARC(rom.getFileByName('a/0/4/1')); lands=ndspy.narc.NARC(rom.getFileByName('a/0/6/5'))
names=decode_messages(ndspy.narc.NARC(rom.getFileByName('a/0/0/2')).files[279])[1] if False else None
mc={}
mh_={}
def mapat(mx,t,default):
    w,hd=mh_[mx]
    return hd[(t[1]//32)*w+t[0]//32] if hd else default
def grid(mx):
    if mx in mc: return mc[mx]
    mat=bytes(mats.files[mx]); w,h,hd,ht,n=mat[:5]
    ids=struct.unpack_from('<%dH'%(w*h),mat,5+n+w*h*(2*hd+ht)); free={}
    hdrs=struct.unpack_from('<%dH'%(w*h),mat,5+n) if hd else None
    mh_[mx]=(w,hdrs)
    for cz in range(h):
        for cx in range(w):
            if ids[cz*w+cx]>=len(lands.files): continue
            land=bytes(lands.files[ids[cz*w+cx]])
            bgs=4+struct.unpack_from('<H',land,18)[0] if land[16:18]==b'\x34\x12' else 0
            perm=land[16+bgs:16+bgs+2048]
            for lz in range(32):
                for lx in range(32):
                    o=(lz*32+lx)*2
                    if not perm[o+1]&0x80: free[(cx*32+lx,cz*32+lz)]=perm[o]
    mc[mx]=free; return free
WATER={0x10,0x15}
def reach(maps,start,surf=True,block_actors=True,unblock=(),hidden=lambda f:False,extra_free=()):
    seen=set(); q=collections.deque([start]); seen.add(start)
    blocked={}
    for m,v in maps.items():
        s=set(tuple(b) for b in v['bgs'])
        if block_actors:
            for a,(x,z) in v['actors']:
                if (m,a[0]) in unblock or hidden(a[4]): continue
                s.add((x,z))
        blocked[m]=s
    while q:
        m,x,z=q.popleft()
        if m not in maps: continue
        v=maps[m]; fr=grid(v['matrix'])
        for w in v['warps']:
            if (w[0],w[1])==(x,z) and w[2] in maps:
                d=maps[w[2]]
                if w[3]<len(d['warps']):
                    n=(w[2],d['warps'][w[3]][0],d['warps'][w[3]][1])
                    if n not in seen: seen.add(n); q.append(n)
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            t=(x+dx,z+dz)
            if t not in fr or t in blocked[m]:
                # warp tiles may be blocked yet enterable
                if not any((w[0],w[1])==t for w in v['warps']): continue
            if fr.get(t,0) in WATER and not surf: continue
            n=(mapat(v['matrix'],t,m),)+t
            if n not in seen: seen.add(n); q.append(n)
    return seen
if __name__=='__main__':
    start=(506,)+tuple(maps[506]['warps'][0][:2])
    for surf in (False,True):
        r=reach(maps,start,surf=surf,block_actors=False)
        print('surf',surf,'tiles',len(r),'maps',len({m for m,_,_ in r}))
        pickle.dump(r,open(sys.argv[0]+'.%d.pkl'%surf,'wb')) if False else None
    r=reach(maps,start,surf=True,block_actors=False)
    print(sorted({m for m,_,_ in r}))
    for m in sorted({m for m,_,_ in r}):
        print(m,maps[m]['matrix'],len([1 for a in r if a[0]==m]),[w for w in maps[m]['warps']][:8])
