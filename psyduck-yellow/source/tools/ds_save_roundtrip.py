import os, sys, json
sys.path.insert(0, '/home/thatanarchydude/code/corvus-workshop/yellow-heartgold/tools')
import ds_session as d
import ctypes as C
X, Z = 0x1da6f6, 0x1da6fe
import struct
def pos():
    r = d.ram(); return struct.unpack_from('<H', r, X)[0], struct.unpack_from('<H', r, Z)[0]
d.boot(); d.run(500)
print('start', pos(), flush=True)
KEYS = {'x': 9, 'start': 3, 'a': 8, 'b': 0, 'up': 4, 'down': 5, 'left': 6, 'right': 7}
for step in sys.argv[1:]:
    w = step.split()
    if w[0] in KEYS: d.run(8, KEYS[w[0]]); d.run(40)
    elif w[0] == 'wait': d.run(int(w[1]))
    elif w[0] == 'tshot': d.shot_true(w[1] + '.png')
    elif w[0] == 'tap': d.touch = (int(w[1]), int(w[2])); d.run(8); d.touch = None; d.run(50)
    elif w[0] == 'pos': print('pos', pos(), flush=True)
    elif w[0] == 'dump':
        d.core.retro_get_memory_data.restype = C.c_void_p; d.core.retro_get_memory_size.restype = C.c_size_t
        p = d.core.retro_get_memory_data(0); n = d.core.retro_get_memory_size(0)
        open(w[1], 'wb').write(C.string_at(p, n)); print('dumped', n, flush=True)
print('done', flush=True)
