import sys
sys.argv=[sys.argv[0],sys.argv[1],sys.argv[2]]
exec(open(sys.argv[0].replace('orph.py','reach.py')).read().split("if __name__")[0])
start=(506,)+tuple(maps[506]['warps'][0][:2])
r=reach(maps,start,surf=True,block_actors=False); rm={m for m,_,_ in r}
inc=collections.defaultdict(list)
for m,v in maps.items():
    for w in v['warps']: inc[w[2]].append((m,w[0],w[1],w[3]))
for m in sorted(set(maps)-rm):
    srcs=[(s,'REACHED' if s in rm else 'unreached') for s,_,_,_ in inc[m]]
    print(m,'mapsec',maps[m]['mapsec'],'warps',len(maps[m]['warps']),'incoming from',srcs[:5],'actors',len(maps[m]['actors']))
