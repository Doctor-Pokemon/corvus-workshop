"""TEST ONLY: ds_save_fixture.py <rom> <workdir> <base.dsv> <map> <x> <z> writes workdir/t.nds (fixture warp) + t.dsv; ds_save_roundtrip.py (env DS_ROM, DS_OUT) runs steps given as arguments (menu: x, SAVE = tap 126 270, a, a, wait 600): the emulator core writes the in-game save into DS_OUT/t.dsv. To COLD-LOAD it: copy the plain ROM to a new folder as t.nds, the saved dsv as t.dsv, run again with no fixture (2026-11-09, Viridian Gym crash hunt)."""
import sys, os, shutil, ndspy.rom
sys.path.insert(0, 'tools')
import fixture_party
rom0, work, dsv, m, x, z = sys.argv[1:7]
os.makedirs(work, exist_ok=True)
rom = ndspy.rom.NintendoDSRom.fromFile(rom0)
fixture_party.install(rom, 68, 0, 50, [], None, False, (int(m), int(x), int(z)), False, None)
rom.saveToFile(os.path.join(work, 't.nds')); shutil.copy(dsv, os.path.join(work, 't.dsv'))
