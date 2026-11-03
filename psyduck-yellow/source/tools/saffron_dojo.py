"""Prototype 0173: Yellow's Fighting Dojo master battle and the Hitmonlee / Hitmonchan prize in Saffron's Fighting Dojo (owner order 2026-11-03).
The Dojo (map 398) has HeartGold's own NPC (actor 0, sprite 344) who says the Karate King is away. Owner rules: no Karate King is added; THIS NPC battles the player ("...but I can still teach you a lesson."), as a Black Belt trainer with Yellow's Karate Master team (Hitmonlee L37 + Hitmonchan L37, moves as Yellow's level-up rule gives them); the four optional Dojo students are not added.
After the win two Poke Ball objects behind him (tiles 6,3 and 8,3) unlock: choosing one gives that Pokemon (level 30 like Yellow, HOLDING A BLACK BELT: owner's addition) and the other ball disappears (the Mt. Moon fossil pattern). Before the win the balls do nothing.
The old script (message 0 / message 1, chosen by flag 269) stays as the fall-back: once flag 269 is set (the postgame state the original text refers to) the NPC behaves as before.
Flags (persistent flags are nearly exhausted, so only two): the trainer-defeat flag (0x550 + the new trainer id, the lowest free one) which also means "won", and ONE hide flag shared by both ball objects (taking either hides both). Both are checked free in every script bank and actor list (flag_alloc / trainer_alloc). No variable is used.
Usage (from yellow-heartgold, PYTHONPATH=tools): saffron_dojo.py <in.nds> <out.nds> <pokeyellow source>"""
import re
import struct
import sys
from pathlib import Path
import ndspy.narc
import ndspy.rom
import flag_alloc
import trainer_alloc
from opening import Script, actor, end, events_decode, events_encode, script_bank, encode_text
from parcel_quest import PH, split_bank
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE

MAP, NPC = 398, 0
NATIVE_FLAG = 269                     # the original script's own test (message 1 once set)
BLACK_BELT_CLASS_TEMPLATE = 17        # a native Black Belt trainer record (class 14)
BLACK_BELT_ITEM = 241
GIFT_LEVEL = 30                       # Yellow: ld c, 30 ; call GivePokemon
HITMONLEE, HITMONCHAN = 106, 107
BALLS = {'HITMONLEE': (6, 3, HITMONLEE), 'HITMONCHAN': (8, 3, HITMONCHAN)}

LESSON = '...but I can still teach you a lesson.'
BEATEN = 'Hwa! Arrgh! Beaten!'
STAY = 'Ho! Stay and train at Karate with us!'
PRIZE = ("Indeed, I have lost! But, I beseech you, do not take our emblem as your trophy! "
         "In return, I will give you a prized fighting POKEMON! Choose whichever one you like!")
ASK = {'HITMONLEE': 'You want the hard-kicking HITMONLEE?', 'HITMONCHAN': 'You want the piston-punching HITMONCHAN?'}
GOT = {'HITMONLEE': '{PLAYER} received HITMONLEE!', 'HITMONCHAN': '{PLAYER} received HITMONCHAN!'}
FULL = 'You have no room for more POKEMON!'


def yellow_moves(source, name, level):
    """Yellow's rule for a trainer's Pokemon: the level-1 moves, then each level-up move up to the level, keeping the last four."""
    src = Path(source)
    move_ids = {n: i for i, n in enumerate(re.findall(r'^\s*const\s+(\w+)', (src / 'constants/move_constants.asm').read_text(), re.M))}
    base = (src / ('data/pokemon/base_stats/' + name.lower().replace('_', '') + '.asm')).read_text()
    learned = [m.strip() for m in re.search(r'db\s+([^;\n]+); level 1 learnset', base).group(1).split(',') if m.strip() != 'NO_MOVE']
    evos = (src / 'data/pokemon/evos_moves.asm').read_text()
    label = name.title().replace('_', '') + 'EvosMoves'
    learnset = re.search(r'^' + label + r':\s*\n(.*?)(?=^\w+EvosMoves:|\Z)', evos, re.M | re.S).group(1).split('; Learnset')[1]
    for lv, move in re.findall(r'^\s*db\s+(\d+),\s*(\w+)', learnset, re.M):
        if int(lv) <= level and move not in learned:
            learned = (learned + [move])[-4:]
    return [move_ids[m] for m in learned] + [0] * (4 - len(learned))


def npc_script(trainer, msg, orig_body, won, hide_a):
    """msg: first index of this script's new messages: lesson, beaten, prize, stay."""
    s = Script().emit(96).emit(32, NATIVE_FLAG).jump('native', 1)
    s.emit(104).emit(32, won).jump('after', 1)
    s.msg(0).msg(msg)                                     # the original line (message 0), then the owner's line
    s.emit(213, trainer, 0)
    s.data.extend(bytes(2))
    s.emit(220, 0x800C).compare(0x800C, 1).jump('lost', 5)
    s.emit(36, trainer).msg(msg + 1).msg(msg + 2)
    end(s)
    s.label('after').emit(32, hide_a).jump('stay', 1).msg(msg + 2)
    end(s)
    s.label('stay').msg(msg + 3)
    end(s)
    s.label('lost').emit(219)
    end(s)
    s.label('native')
    s.data.extend(orig_body)                              # the original script, whole (its jumps are relative)
    return s.finish()


def ball_script(name, msg, won, hide_flags, actor_ids):
    x, z, species = BALLS[name]
    s = Script().emit(96).emit(32, won).jump('go', 1)
    end(s)                                                # locked until the battle is won: nothing happens
    s.label('go').msg(msg).emit(63, 0x800C).compare(0x800C, 0).jump('no', 5)
    s.emit(332, 0x800C).compare(0x800C, 6).jump('full', 1)
    s.emit(137, species, GIFT_LEVEL, BLACK_BELT_ITEM, 0, 0, 0x800C).compare(0x800C, 0).jump('full', 1)
    for f in hide_flags:
        s.emit(30, f)
    for a in actor_ids:
        s.emit(101, a)
    s.emit(78, 1185).msg(msg + 1).emit(79)
    end(s)
    s.label('no')
    end(s)
    s.label('full').msg(msg + 2)
    end(s)
    return s.finish()


def patch(rom, source):
    seen = flag_alloc.used_flags(rom)
    tflag = min(f for f in range(0x956, flag_alloc.HIGH) if f not in seen)          # lowest free trainer-defeat flag (ids below 1030 do not exist yet)
    trainer_alloc.assert_flags_free(rom, [tflag])
    won = tflag                                                                   # the trainer-defeat flag doubles as 'won' (emit(36, trainer) sets it)
    hide = flag_alloc.free_flags(rom, 1, reserved=[tflag])[0]
    trainer_alloc.assert_flags_free(rom, [hide])
    tid = tflag - 0x550
    team = [dict(level=37, species=HITMONLEE, moves=yellow_moves(source, 'HITMONLEE', 37)), dict(level=37, species=HITMONCHAN, moves=yellow_moves(source, 'HITMONCHAN', 37))]
    entry = dict(role='Blackbelt', team=team, messages=dict(BattleText=LESSON, EndBattleText=BEATEN, AfterBattleText=STAY))
    trainer_alloc.add(rom, [entry], [tid], {'Blackbelt': BLACK_BELT_CLASS_TEMPLATE})
    d = bytes(rom.loadArm9().sections[0].data)
    rec = TABLE + MAP * 24
    sid, _, tx = struct.unpack_from('<3H', d, rec + 6)
    eid = struct.unpack_from('<H', d, rec + 16)[0]
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    bank = split_bank(scripts.files[sid])
    key, lines = decode_messages(texts.files[tx])
    groups = events_decode(events.files[eid])
    old = struct.unpack_from('<7H', groups[1][NPC], 0)
    assert old[1] == 344 and old[4] == 0, old
    orig_index = old[5]
    orig_body = bank[orig_index - 1].rstrip(b'\0') + b'\0'        # the End opcode is 02 00: strip the padding, keep its high byte
    assert orig_body[-2:] == b'\x02\x00', orig_body.hex(' ')
    new_lines = [LESSON, BEATEN, PRIZE, STAY]
    npc_msg = len(lines)
    ball_msgs = {}
    for name in BALLS:
        ball_msgs[name] = npc_msg + len(new_lines)
        new_lines.extend([ASK[name], GOT[name], FULL])
    ids = [struct.unpack_from('<H', a, 0)[0] for a in groups[1]]
    aid = {'HITMONLEE': max(ids) + 1, 'HITMONCHAN': max(ids) + 2}
    npc_idx = len(bank) + 1
    bank.append(npc_script(tid, npc_msg, orig_body, won, hide))
    row = bytearray(groups[1][NPC])
    struct.pack_into('<H', row, 10, npc_idx)
    groups[1][NPC] = bytes(row)
    for name, (x, z, species) in BALLS.items():
        idx = len(bank) + 1
        bank.append(ball_script(name, ball_msgs[name], won, [hide], [aid['HITMONLEE'], aid['HITMONCHAN']]))
        groups[1].append(actor(aid[name], 87, idx, x, z, hide, 0))
    lines.extend(decode_messages(encode_text(new_lines, PH))[1])
    scripts.files.append(script_bank(bank))
    texts.files.append(encode_messages(key, lines))
    events.files.append(events_encode(groups))
    main = rom.loadArm9()
    dd = main.sections[0].data = bytearray(main.sections[0].data)
    struct.pack_into('<H', dd, rec + 6, len(scripts.files) - 1)
    struct.pack_into('<H', dd, rec + 10, len(texts.files) - 1)
    struct.pack_into('<H', dd, rec + 16, len(events.files) - 1)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    rom.files[rom.filenames.idOf('a/0/3/2')] = events.save()
    rom.arm9 = main.save(compress=True)
    return dict(trainer_id=tid, trainer_flag=hex(tflag), won_flag=hex(won), hide_flag=hex(hide), moves=[t['moves'] for t in team], npc_script=npc_idx, balls=aid)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
