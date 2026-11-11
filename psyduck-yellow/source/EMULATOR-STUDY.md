# Emulator / launcher study (2026-11-11) — read-only investigation, nothing built

Source studied: melonDS (GPLv3), shallow clone in build/melonds-study/src (ignored), commit 497aa6c (2026-11-04).

Findings (all from reading the code):
- Main RAM: src/NDS.cpp Reset(): MainRAMMask = 0x3FFFFF (4 MB) in DS mode, 0xFFFFFF (16 MB) in DSi mode. The 0x02000000 window mirrors the 4 MB.
  Our ROM: highest ARM9 overlay (129) ends at 0x023DFFF0, nothing above is statically used. Arena/heap limits are NOT found yet (no literal 0x02400000/0x023FE000 in ARM9 text).
- Cart save: size comes from melonDS' ROM database by game code (CartRetail.cpp, SaveMemType, up to 64 MB). The game only uses its own 512 KB layout, so a bigger chip alone gives nothing.
- Free hooks for a fork: no$gba debug register block at ARM9 IO 0x04FFFA00 already returns "melonDS <version>" (NDS.cpp ~2889). A new device in that area = runtime detection (read ID; 0 on hardware).
- Built-in FreeBIOS (src/FreeBIOS.*, used by frontend EmuInstance.cpp): no Nintendo BIOS/firmware needed in principle; HGSS compatibility with it is untested.
- Frontend: Qt + SDL (src/frontend/qt_sdl), command-line ROM argument exists (CLI::ManageArgs). Core and frontend are separate CMake targets.

Not done / unknown: JIT mirror handling for a 16 MB DS-mode window (ARMJIT_Memory.cpp lines ~1048/1182 use MainRAMMask), CP15/MPU region setup in our ROM, heap/arena constants, Windows build.
