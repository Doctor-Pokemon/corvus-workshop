import sys,struct,collections,pickle,ndspy.narc
sys.argv=[sys.argv[0],sys.argv[1],sys.argv[2]]
exec(open(sys.argv[0].replace('layers.py','reach.py')).read().split("if __name__")[0])
names=decode_messages(ndspy.narc.NARC(rom.getFileByName('a/0/2/7')).files[279])[1]
def nm(m): return m
start=(506,)+tuple(maps[506]['warps'][0][:2])
surf=True
unb=set(); seenm=set()
for layer in range(25):
    blk=reach(maps,start,surf=surf,block_actors=True,unblock=unb); bm={m for m,_,_ in blk}
    new=bm-seenm; seenm|=bm
    print('LAYER',layer,'reached maps',len(bm),'new:',sorted(new))
    cand=[]
    for m,v in maps.items():
        if m not in bm: continue
        fr=grid(v['matrix'])
        for a,(x,z) in v['actors']:
            if (m,a[0]) in unb: continue
            nb=[(x+dx,z+dz) for dx,dz in ((1,0),(-1,0),(0,1),(0,-1))]
            if any((m,)+t in blk for t in nb) and any((t in fr or any((w[0],w[1])==t for w in v['warps'])) and (mapat(v['matrix'],t,m),)+t not in blk for t in nb): cand.append((m,a[0],a[1],x,z,a[4]))
    gates=[]
    for (m,aid,sp,x,z,fl) in cand:
        r=reach(maps,start,surf=surf,block_actors=True,unblock=unb|{(m,aid)}); nw={mm for mm,_,_ in r}-bm
        if nw: gates.append((m,aid,sp,x,z,fl,nw))
    if not gates: print('no more single-actor gates; unreached kanto maps:',sorted(set(maps)-bm)[:80]); break
    for g in gates: print('  GATE map',g[0],'actor',g[1],'sprite',g[2],'at',(g[3],g[4]),'hide',hex(g[5]),'-> opens',sorted(g[6])[:14])
    unb|={(g[0],g[1]) for g in gates}
