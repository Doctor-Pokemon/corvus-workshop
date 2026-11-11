"""Prototype 0249: the DAILY LEGENDARY HUB in the Embedded Tower (owner 2026-11-12: his first idea was the Embedded Tower; ROM 0248 had put it in the League lobby by mistake and is REPLACED by this build).
Built from ROM 0247 (spots with follower sprites). Chamber 524 (Groudon's; HeartGold hides Groudon there, its lower door on Route 47 (tile 389) still leads in, walked in the emulator for var 0x40F9 = 1 and 2).
 - THE ORB: a ball-sprite actor (sprite 87, "the Red Orb") at (17, 17) in front of the chamber's far end. Touching it activates the check (owner: "Have the Red Orb activate the check, and start the encounter automatically").
 - THE ENCOUNTER (owner's design): the day's visitor appears at the far end of the chamber as ITS OWN FOLLOWER SPRITE (HeartGold's follower model of the species: overworld sprite id 2500 + species id, rows of the overlay 131 table, no art needed), and WALKS toward the player at the normal walking speed
   (movement code 13 = step down; no Running Boots) while the player is locked (LockAll). As soon as it reaches the player the wild battle starts. Scripts cannot change an actor's sprite and the event file is capped at 0x800 bytes (108 hidden actors do not fit), so this build adds a script command,
   SetPersonSprite (opcode 337, tools/set_person_sprite.py), that rewrites the sprite of ONE hidden visitor actor's in-memory event record just before ShowPerson creates it. A map-entry script sets the visitor's hide flag on every entry. The player is first moved to the fixed tile (16, 17) (MovePersonFacing on object 255) so the approach always ends touching.
   MEW and ARCEUS (owner 2026-11-12) are the last two entries of the pool and are special: Mew is eligible only when at most TWO of the 1025 National Dex species are NOT registered as caught, Arceus only when at most ONE is missing (the count comes from script command 343 CountUncaught, tools/count_uncaught.py;
   the owner: "we don't need to verify every Pokedex entry... just the amount of unique species caught"). Since the other 108 are skipped once caught, they surface exactly when the dex is nearly complete; a caught one is skipped like any other.
 - BIG FOLLOWERS CRASH (found 2026-11-12 with Arceus: the emulator segfaulted the moment ShowPerson created it): 15 of the species have a 64 x 64 follower model (param 21000, 16 KB) and the scene dies; those get a 32 x 32 person-style model made from their party icon on a borrowed UNUSED person sprite id
   (tools/legend_spots.py borrowable / icon_frames), the other 95 + Mew use their own 32 x 32 follower model. A second dispatch table (after the pick is found) gives the sprite id.
 - THE ORBS: the Red Orb must be in the bag (the orb actor only answers a Champion who carries it); Mr. Pokemon now gives BOTH orbs (tools/both_orbs.py, owner request), so the Red Orb is there after his scene.
 - MUSIC: the Embedded Tower's own "ancient Pokemon" battle theme (SEQ_GS_VS_KODAI 1174, the Kyogre / Groudon / Rayquaza theme) is started with PlayBGM when the visitor appears, and SetBattleMusic (command 335, tools/battle_music_hook.py) makes the wild battle that follows play the same track (it starts from its beginning); ResetBGM restores the chamber music afterwards.
 - THE POOL, THE PICK (unchanged from 0248): every held-back legendary-class species (tools/postgame_spread.py EVENT = 134 dex numbers) that has NO other way to be obtained: minus the 17 with a script avenue, minus the themed spots (Celebi, Regirock, Regice, Registeel, Uxie, Mesprit, Azelf), minus Mew and Arceus = 108 species (Groudon included) + the two special ones, 110.
   Tiers by base-stat total (a/0/0/2): BST < 480 needs 2 Johto badges, < 580 needs 4, < 640 needs 6, else 8. Before the first Hall of Fame (HOFN var 0x413E < 1) the orb is dark. The day's pick lives in ONE persistent work variable 0x4031 = (GetWeekday + 1) * 256 + pick (0 = never used, pick 255 = "today's visitor was caught");
   a new weekday re-rolls Random(pool size = 110); from the pick the script walks forward (wrapping) to the first species that is eligible (Johto badges >= tier) and NOT caught (CheckMonCaught, command 336). A catch ends the day; a visitor that faints or is run from can be met again the same day. Battle level 60 + 5 x Johto badges.
Variable 0x4031 is free in ROM 0247 (instruction-level scan of every script bank + tools; 0x4034 0x4044 0x4049 are the album's, 0x4038-0x403B / 0x4172+ the state-variable work's). Script-local vars 0x8004-0x800A only; hide flag 0xAC7 (free; 0xAC0-0xAC6 are the themed spots').
Usage (from yellow-heartgold, PYTHONPATH=tools): legend_hub.py <in 0247.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import postgame_spread as p
from legend_spots import script_start
import battle_music_hook
import both_orbs
import count_uncaught
import os
import ndspy.texture
from PIL import Image
from elite_four_overworld import model_bytes
from legend_spots import borrowable, icon_frames, sheet_of
import set_person_sprite
from map_edit import MapEdit
from opening import Script

MAPS, ORB_TILE, ORB_SPRITE = (524, 525, 526), (17, 17), 87                    # the orb stands in ALL THREE chambers: which Route 47 door leads to which chamber changes with the Hoenn progress variable (see below)
PLAYER_TILE, VISITOR_TILE, STEPS = (15, 17), (15, 9), 7             # the player is moved to (15, 17); the visitor starts at (15, 9) and walks 7 steps down to (15, 16); column 15 avoids the chamber's own legendary at (16, 11)
HIDE_FLAG, BGM, FOLLOWER_BASE = 0xAC7, 1174, 2500
HOFN, HUB = 0x413E, 0x4031
HAVE = {144, 145, 146, 150, 243, 244, 245, 249, 250, 380, 381, 382, 384, 483, 484, 487, 719}        # dex numbers with another avenue
THEMED = {251, 377, 378, 379, 480, 481, 482}
HELD = {151, 493}
MEW, ARCEUS = 151, 493
SLACK = int(os.environ.get('LEGEND_TEST_SLACK', '0'))                                # test switch: loosens the Pokedex count (never set in a real build)                                                                                    # Mew, Arceus: later
LEVEL_BASE, LEVEL_PER_BADGE = 60, 5
T, LOW, K, PICK, COUNT, SPECIES, NEED = 0x8004, 0x8005, 0x8006, 0x8007, 0x8008, 0x8009, 0x800A       # script-local
IDX, HIGH, LEVEL = T, K, K                                                                           # reuse once free


def species_id(dex):
    return dex if dex <= 493 else dex + 50


def tier(bst):
    return 2 if bst < 480 else 4 if bst < 580 else 6 if bst < 640 else 8


def pool(rom):
    personal = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/0/2')])
    out = []
    for dex in sorted(p.EVENT - HAVE - THEMED - HELD):
        sid = species_id(dex)
        bst = sum(bytes(personal.files[sid])[:6])
        out.append((sid, tier(bst)))
    out += [(MEW, 8), (ARCEUS, 8)]                                                # special: gated by the Pokedex count
    if os.environ.get('LEGEND_TEST_POOL') == 'mew':                               # test switch: only Mew and Arceus
        out = out[-2:]
    elif os.environ.get('LEGEND_TEST_POOL') == 'arceus':                          # test switch: only Arceus
        out = out[-1:]
    return out


TEXT = dict(
    hof="The orb stays dark. It answers only a Champion who carries the Red Orb.",
    none="The Red Orb glows faintly, but nothing answers today. Come back tomorrow, or when you are stronger.",
    done="The Red Orb has gone quiet. Come back tomorrow.",
    glow="The Red Orb begins to glow with an ancient light...",
)


def talk_script(rows, msg, visitor_id, sprites):
    n = len(rows)
    s = Script()
    s.emit(96)                                                                    # LockAll
    s.emit(128, 534, 1, 0x800C).compare(0x800C, 0).jump('nohof', 1)               # HasItem: no Red Orb in the bag
    s.compare(HOFN, 1).jump('nohof', 0)
    s.emit(41, COUNT, 0)
    for badge in range(8):
        s.emit(294, badge, 0x800C).emit(39, COUNT, 0x800C)                        # Johto badge count
    s.emit(484, T).emit(39, T, 1)                                                 # T = weekday + 1
    s.emit(42, LOW, T)                                                            # LOW = T * 256 by eight doublings of a copy of T
    for _ in range(8):
        s.emit(39, LOW, LOW)
    s.emit(18, HUB, LOW).jump('newday', 0)                                        # CompareVarToVar: HUB < LOW (a smaller / unset stamp)
    s.emit(42, HIGH, LOW).emit(39, HIGH, 256)
    s.emit(18, HUB, HIGH).jump('newday', 4)                                       # HUB >= LOW + 256
    s.emit(42, PICK, HUB).emit(40, PICK, LOW).jump('havepick')                    # same day: pick = HUB - LOW
    s.label('newday')
    s.emit(380, PICK, n)                                                          # Random: pick in 0 .. n-1
    s.emit(42, HUB, LOW).emit(39, HUB, PICK)                                      # HUB = stamp * 256 + pick
    s.label('havepick')
    s.compare(PICK, 255).jump('donetoday', 1)
    s.emit(41, K, 0)
    s.label('loop')
    s.emit(42, IDX, PICK).emit(39, IDX, K)
    s.compare(IDX, n).jump('inrange', 0)
    s.emit(40, IDX, n)                                                            # wrap
    s.label('inrange')
    s.emit(26).relative('dispatch')                                               # Call: SPECIES / NEED for IDX
    s.emit(18, NEED, COUNT).jump('skip', 2)                                       # needs more badges than we have
    s.emit(336, SPECIES, 0x800C).compare(0x800C, 1).jump('skip', 1)               # already caught
    s.compare(SPECIES, MEW).jump('mew', 1)
    s.compare(SPECIES, ARCEUS).jump('arceus', 1)
    s.jump('found')
    s.label('mew')
    s.emit(343, NEED).compare(NEED, 3 + SLACK).jump('found', 0)                   # CountUncaught: at most two missing
    s.jump('skip')
    s.label('arceus')
    s.emit(343, NEED).compare(NEED, 2 + SLACK).jump('found', 0)                   # at most one missing
    s.label('skip')
    s.emit(39, K, 1)
    s.compare(K, n).jump('loop', 0)
    s.jump('none')
    s.label('found')
    s.emit(45)
    s.data.append(msg['glow'])
    s.emit(50).emit(53)                                                           # NPCMsg, WaitButton, CloseMsg: the Red Orb glows
    s.emit(339, 255, PLAYER_TILE[0], 0, PLAYER_TILE[1], 0)                        # MovePersonFacing (x, height, z, facing): the player to the fixed tile, facing up
    s.emit(80, BGM)                                                               # PlayBGM: the ancient-Pokemon battle theme
    s.emit(31, HIDE_FLAG)                                                         # ClearFlag
    s.emit(26).relative('spritetable')                                            # Call: NEED = the sprite id of the picked species (follower model, or an icon model for the big ones)
    s.emit(337, visitor_id, NEED)                                                 # SetPersonSprite
    s.emit(100, visitor_id)                                                       # ShowPerson: the visitor's follower sprite appears
    s.emit(76, SPECIES, 0).emit(77)                                               # PlayCry, WaitCry
    s.emit(94, visitor_id)
    s.relative('walk')                                                            # ApplyMovement: STEPS normal steps down
    s.emit(95)                                                                    # WaitMovement
    s.emit(41, LEVEL, LEVEL_BASE)
    for _ in range(LEVEL_PER_BADGE):
        s.emit(39, LEVEL, COUNT)
    s.emit(335, BGM)                                                              # SetBattleMusic: the next wild battle plays the same theme (tools/battle_music_hook.py)
    s.emit(589, SPECIES, LEVEL).data.append(0)                                    # WildBattle: the visitor touches the player
    s.emit(335, 0)                                                                # clear (the hook clears it itself; this covers a battle that never started)
    s.emit(220, 0x800C).compare(0x800C, 0).jump('lost', 1)
    s.emit(101, visitor_id)                                                       # HidePerson
    s.emit(82)                                                                    # ResetBGM
    s.emit(336, SPECIES, 0x800C).compare(0x800C, 1).jump('release', 5)            # caught?
    s.emit(42, HUB, LOW).emit(39, HUB, 255)                                       # one catch per day
    s.label('release')
    s.emit(97).emit(2)
    s.label('lost')
    s.emit(219).emit(97).emit(2)
    for name in ('nohof', 'none', 'donetoday'):
        s.label(name)
        s.emit(45)
        s.data.append(msg[{'nohof': 'hof', 'none': 'none', 'donetoday': 'done'}[name]])
        s.emit(50).emit(53).emit(97).emit(2)
    s.label('dispatch')
    for i in range(n):
        s.compare(IDX, i).jump(f'd{i}', 1)
    s.emit(27)
    for i, (sid, need) in enumerate(rows):
        s.label(f'd{i}')
        s.emit(41, SPECIES, sid).emit(41, NEED, need).emit(27)
    s.label('spritetable')
    for i in range(n):
        s.compare(IDX, i).jump(f't{i}', 1)
    s.emit(27)
    for i in range(n):
        s.label(f't{i}')
        s.emit(41, NEED, sprites[i]).emit(27)
    s.label('walk')
    s.data.extend(struct.pack('<4H', 13, STEPS, 254, 0))                          # movement data: step down x STEPS, end
    return s


def follower_info(rom, rows):
    """-> (sprite id per row, [rows that need an icon model]): the follower model (sprite id 2500 + species id) when it is a 32 x 32 model, else None."""
    overlay = rom.loadArm9Overlays()[131]
    at = 0x23CA660 - overlay.ramAddress
    ids = {}
    k = 0
    while True:
        r = struct.unpack_from('<3H', overlay.data, at + 6 * k)
        if r[0] == 0xFFFF:
            break
        ids[r[0]] = r[1]
        k += 1
    models = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/8/1')])
    sprites, big = [], []
    for i, (sid, _) in enumerate(rows):
        assert FOLLOWER_BASE + sid in ids, sid
        tex = ndspy.texture.NSBTX(bytes(models.files[ids[FOLLOWER_BASE + sid]]))
        if tex.textures[0][1].width == 32:
            sprites.append(FOLLOWER_BASE + sid)
        else:
            sprites.append(None)
            big.append(i)
    return sprites, big


def patch(rom):
    rows = pool(rom)
    assert len(rows) in (110, 2, 1), len(rows)
    sprites, big = follower_info(rom, rows)
    if big:                                                                       # icon models on borrowed person sprite ids for the 64 x 64 followers
        pool_ids = borrowable(rom, len(big))
        models_id = rom.filenames.idOf('a/0/8/1')
        models = ndspy.narc.NARC(rom.files[models_id])
        for (sprite, model), i in zip(pool_ids, big):
            data, _, _ = model_bytes(bytes(models.files[model]), sheet_of(icon_frames(rom, rows[i][0])))
            models.files[model] = data
            sprites[i] = sprite
        rom.files[models_id] = models.save()
    set_person_sprite.patch(rom)
    battle_music_hook.patch(rom)
    count_uncaught.patch(rom)
    both_orbs.patch(rom)
    return [install(rom, mp, rows, sprites) for mp in MAPS]


def install(rom, mp, rows, sprites):
    e = MapEdit(rom, mp)
    msg = {}
    for key, text in TEXT.items():
        msg[key] = e.message(text)
    actors = e.groups[1]
    first = max(struct.unpack_from('<H', a, 0)[0] for a in actors) + 1
    orb_id, visitor_id = first, first + 1
    code = talk_script(rows, msg, visitor_id, sprites).finish()
    talk = e.script(lambda add: code)
    orb = bytearray(32)
    struct.pack_into('<7H', orb, 0, orb_id, ORB_SPRITE, 0, 0, 0, talk, 1)
    struct.pack_into('<HH', orb, 24, *ORB_TILE)
    actors.append(bytes(orb))
    rec = bytearray(32)
    struct.pack_into('<7H', rec, 0, visitor_id, sprites[0], 0, 0, HIDE_FLAG, 0, 1)    # facing down, hidden, no script; its sprite is set per day
    struct.pack_into('<HH', rec, 24, *VISITOR_TILE)
    actors.append(bytes(rec))
    # map-entry script: SetFlag HIDE_FLAG (the visitors stay hidden), then the chamber's original entry script
    header_id = struct.unpack_from('<H', e.d, e.at + 8)[0]
    header = bytes(e.scripts.files[header_id])
    trows, at = [], 0
    while header[at] != 0:
        trows.append((header[at], struct.unpack_from('<I', header, at + 1)[0]))
        at += 5
    tail = header[at:]
    original = next((v for t, v in trows if t == 2), None)
    entry = Script().emit(30, HIDE_FLAG)
    if original is not None:
        entry.emit(22)
        entry.data.extend(bytes(4))
    else:
        entry.emit(2)
    ecode = entry.finish()
    entry_id = e.script(lambda add: ecode)
    if original is not None:
        new_start, old_start = script_start(e.bank, entry_id), script_start(e.bank, original)
        fix = new_start + len(ecode) - 4
        struct.pack_into('<i', e.bank, fix, old_start - (fix + 4))
        trows = [(2, entry_id) if t == 2 else (t, v) for t, v in trows]
    else:
        trows = sorted(trows + [(2, entry_id)])
    e.scripts.files.append(b''.join(struct.pack('<BI', t, v) for t, v in trows) + tail)
    struct.pack_into('<H', e.d, e.at + 8, len(e.scripts.files) - 1)
    e.save()
    return dict(map=mp, orb=orb_id, visitor=visitor_id, talk=talk, entry=entry_id, original_entry=original, species=len(rows), tiers={t: sum(1 for _, x in rows if x == t) for t in (2, 4, 6, 8)}, code_bytes=len(code))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
