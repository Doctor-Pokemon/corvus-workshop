"""Prototype 0242: the Kanto Elite Four speak Yellow's own lines (owner 2026-11-12: "Aren't the Kanto Elite Four's dialogue in Pokemon Yellow in our project?" - yes: pret/pokeyellow, the reference the project already uses).
Built from ROM 0241. League rooms 301-304 hold two actors (tools/elite_four_overworld.py): the Johto person (hidden in Kanto mode) and the Kanto person (hidden in Johto mode), both with talk script 2 = HeartGold's lines, so in the Kanto league
Lorelei said "I am Will". Now the KANTO actor gets its OWN copy of script 2 with Yellow's text, and the Johto actor keeps the original script (HeartGold's lines for Will, Koga, Bruno, Karen).
 - The Kanto script is the same sequence as the original (door sound, LockAll, FacePlayer, "already beaten" flag test, intro, TrainerBattle with the Kanto record, white-out on loss, flag, victory text, sound, HidePerson 2-4, release) written
   with the script builder (so the player's and rival's names are buffered: Yellow's "<PLAYER>" and "<RIVAL>" work). Per room: flag 228 / 229 / 230 / 231, trainer 245 / 247 / 418 / 246 (Lorelei, Bruno, Agatha, Lance).
 - The lines come from pret/pokeyellow text/{Loreleis,Brunos,Agathas,Lances}Room.asm at the revision the project pins (e89ead154b9968aa50eed9328ff2b38b6c194382): before-battle text, then after the fight "<end-battle text>" and the after-battle
   text on the next page, and the after-battle text again when you talk to the beaten trainer. "#MON" -> "POKéMON", "#DEX" -> "POKéDEX", "<PLAYER>" / "<RIVAL>" -> the names, line breaks are re-flowed to HeartGold's 30-character box, pages keep Yellow's paragraphs.
 Not changed: Johto mode, Champion Blue's lines, the "Don't run away!" text (Yellow's door-lock scene is not in this build).
Usage (from yellow-heartgold, PYTHONPATH=tools): elite_four_dialogue.py <in 0241.nds> <out.nds> <pokeyellow checkout>"""
import re
import struct
import sys
from pathlib import Path
import ndspy.rom
from map_edit import MapEdit
from opening import Script

ROOMS = {301: ('Loreleis', 'Lorelei', 228, 245), 302: ('Brunos', 'Bruno', 229, 247), 303: ('Agathas', 'Agatha', 230, 418), 304: ('Lances', 'Lance', 231, 246)}
JOHTO_FLAG = 0x9FC


def yellow_blocks(path):
    """Parse an asm text file -> {label: reflowed text with \\r page breaks}."""
    blocks, name, pages = {}, None, None
    for raw in Path(path).read_text().splitlines():
        s = raw.strip()
        m = re.match(r'_(\w+)::', s)
        if m:
            name, pages = m.group(1), []
            blocks[name] = pages
            continue
        m = re.match(r'(text|line|cont|para)\s+"(.*)"', s)
        if m and pages is not None:
            kind, body = m.groups()
            if kind in ('text', 'para') or not pages:
                pages.append([body])
            else:
                pages[-1].append(body)
    out = {}
    for label, pgs in blocks.items():
        pages_txt = []
        for p in pgs:
            t = ' '.join(p).replace('@', '')
            t = t.replace('#MON', 'POKéMON').replace('#DEX', 'POKéDEX').replace('<PLAYER>', '{PLAYER}').replace('<RIVAL>', '{RIVAL}')
            pages_txt.append(re.sub(r'\s+', ' ', t).strip())
        out[label] = '\r'.join(pages_txt)
    return out


def lines_for(root, room_file, trainer):
    blocks = yellow_blocks(Path(root) / 'text' / f'{room_file}Room.asm')
    pick = lambda suffix: next(v for k, v in blocks.items() if k.endswith(suffix) and 'DontRunAway' not in k)
    before, end, after = pick('BeforeBattleText'), pick('EndBattleText'), pick('AfterBattleText')
    return before, end + '\r' + after, after


def kanto_script(add, flag, trainer, before, victory, after):
    m0, m1, m2 = add(before), add(victory), add(after)
    s = Script().emit(73, 0x5DC).emit(96).emit(104)                                         # PlaySE, LockAll, FacePlayer
    s.emit(32, flag).jump('beaten', 1)                                                       # CheckFlag: already beaten?
    s.msg(m0)
    s.emit(213, trainer, 0, 0)                                                               # TrainerBattle with the Kanto record
    s.emit(220, 0x800C).compare(0x800C, 0).jump('lost', 1)                                   # CheckBattleWon, lost -> white-out
    s.emit(30, flag)                                                                         # SetFlag
    s.msg(m1)
    s.emit(73, 0x619)
    for person in (2, 3, 4):
        s.emit(101, person)                                                                  # HidePerson
    s.emit(97).emit(2)
    s.label('beaten')
    s.msg(m2).emit(97).emit(2)
    s.label('lost')
    s.emit(219).emit(97).emit(2)
    return s.finish()


def patch(rom, root):
    report = {}
    for room, (room_file, name, flag, trainer) in ROOMS.items():
        before, victory, after = lines_for(root, room_file, trainer)
        e = MapEdit(rom, room)
        actors = e.groups[1]
        kanto = bytearray(actors[-1])
        assert struct.unpack_from('<H', kanto, 8)[0] == JOHTO_FLAG and struct.unpack_from('<H', kanto, 10)[0] == 2, room        # the Kanto twin of elite_four_overworld.py
        sid = e.script(lambda add: kanto_script(add, flag, trainer, before, victory, after))
        struct.pack_into('<H', kanto, 10, sid)
        actors[-1] = bytes(kanto)
        e.save()
        report[name] = dict(room=room, script=sid, pages=(before.count('\r') + 1, victory.count('\r') + 1, after.count('\r') + 1))
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
