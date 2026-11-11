"""Trailer SAMPLE (owner 2026-11-10): a ~20 second teaser made only from captures of the ROM itself (libretro DeSmuME through live_core.Emulator, true colours, real game audio) plus title cards and captions.
Scenes (fixture saves, i.e. prepared saves, not a playthrough): title card, Form Trader swap (Johto Safari Zone Gate), the swapped Pokemon's summary, the Pokemon League lobby shop after the Hall of Fame, end card.
Layout: both DS screens side by side at 3x on 1920x1080, a caption bar below, 30 fps. NO AUDIO (owner: the trailer gets its own music; the recorder can still capture the game's PCM, see the 'bed' scene). Nothing is published; the output stays in build/trailer/.
Usage (from yellow-heartgold, PYTHONPATH=tools): trailer_sample.py <rom 0230 .nds> <work dir> <out.mp4>"""
import os
import subprocess
import sys
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageStat
from live_core import Emulator, BUTTONS

CORE = Path(__file__).resolve().parents[1] / '.tools/emulator/desmume_libretro.so'
PROBE = Path(__file__).resolve().parents[1] / 'build/tools-dotnet/probe/copy.dsv'
W, H, FPS = 1920, 1080, 30
BG = (14, 18, 28)


def font(size, bold=True):
    for name in ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf', 'DejaVuSansMono-Bold.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def fixture(rom, work, name, species, level, warp, flags='', form=''):
    d = Path(work) / name
    d.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).parent), FIXTURE_FLAGS=flags, FIXTURE_FORM=form)
    subprocess.run([sys.executable, '-s', str(Path(__file__).parent / 'fixture_party.py'), str(rom), str(d / 'fx.nds'), str(species), '0', str(level), '--dex', '--warp', warp], env=env, check=True, capture_output=True)
    (d / 'fx.dsv').write_bytes(PROBE.read_bytes())
    return d


class Cam:
    """Runs the emulator through steps; frames inside 'cap' windows are kept (every second frame = 30 fps)."""
    def __init__(self, directory):
        self.emu = Emulator(CORE, directory / 'fx.nds', directory, capture_audio=True)
        self.frames, self.audio, self.tick, self.title = [], [], 0, []

    def run(self, n, cap=False, touch=None, keys=()):
        self.emu.buttons = {BUTTONS[k] for k in keys}
        self.emu.touch = touch
        for _ in range(n):
            self.emu.run()
            pcm = self.emu.drain_audio()
            if cap:
                self.audio.append(pcm)
                if self.tick % 2 == 0:
                    self.frames.append(self.emu.image().copy())
                self.tick += 1

    def press(self, key, hold=8, after=40, cap=False):
        self.run(hold, cap, keys=(key,))
        self.run(after, cap)

    def tap(self, x, y, after=50, cap=False):
        self.run(8, cap, touch=(x, y))
        self.run(after, cap)

    def close(self):
        self.emu.close()


def screens(img, scale=3):
    top, bottom = img.crop((0, 0, 256, 192)), img.crop((0, 192, 256, 384))
    canvas = Image.new('RGB', (W, H), BG)
    w, h = 256 * scale, 192 * scale
    x0 = (W - 2 * w - 24) // 2
    y0 = 120
    canvas.paste(top.resize((w, h), Image.Resampling.NEAREST), (x0, y0))
    canvas.paste(bottom.resize((w, h), Image.Resampling.NEAREST), (x0 + w + 24, y0))
    return canvas


def caption(canvas, text):
    d = ImageDraw.Draw(canvas)
    f = font(46)
    tw = d.textlength(text, font=f)
    d.text(((W - tw) / 2, 800), text, fill=(240, 240, 250), font=f)
    return canvas


def card(lines, sizes, seconds):
    out = []
    for i in range(round(seconds * FPS)):
        c = Image.new('RGB', (W, H), BG)
        d = ImageDraw.Draw(c)
        y = H / 2 - sum(sizes) * 0.7
        for text, s in zip(lines, sizes):
            f = font(s)
            d.text(((W - d.textlength(text, font=f)) / 2, y), text, fill=(250, 220, 90) if s > 90 else (225, 230, 245), font=f)
            y += s * 1.5
        a = min(1, i / 8, (round(seconds * FPS) - 1 - i) / 8)
        out.append(Image.blend(Image.new('RGB', (W, H), BG), c, max(0, a)))
    return out


def scene(frames, text):
    return [caption(screens(f), text) for f in frames]


def boot(cam):
    """The harness' own boot (ds_session.boot): title screen, Continue, close the menu."""
    cam.run(900)
    cam.run(30, keys=('a',)); cam.run(60); cam.run(30, keys=('a',)); cam.run(60); cam.run(30, keys=('a',)); cam.run(120); cam.run(30, keys=('a',)); cam.run(700); cam.run(20); cam.run(60)


def show(cam, key, wait, seen, hold=8):
    """Press a button, let `wait` frames pass, keep only the last `seen` frames."""
    cam.run(hold, keys=(key,))
    cam.run(wait - seen)
    cam.run(seen, cap=True)


def form_trader(cam):
    boot(cam)
    show(cam, 'right', 40, 16)               # turn to the NPC
    for _ in range(4):                       # greeting, then the party menu
        show(cam, 'a', 90, 30)
    cam.run(150)
    cam.run(40, cap=True)                    # party menu
    cam.run(8, keys=('right',)); cam.run(12, cap=True)
    cam.run(8, keys=('a',)); cam.run(40)
    show(cam, 'a', 130, 50)                  # offer text
    cam.run(40, cap=True)                    # yes / no box
    show(cam, 'a', 110, 30)                  # yes
    show(cam, 'a', 150, 44)                  # done
    show(cam, 'a', 100, 20)


def summary(cam):
    cam.run(8, keys=('a',)); cam.run(90)     # close the last line of dialogue (a second press would start a new talk)
    cam.tap(42, 268, 70)
    cam.tap(190, 225, 40)
    cam.tap(170, 234, 70, cap=True)
    cam.run(80, cap=True)
    cam.tap(85, 368, 60, cap=True)
    cam.run(90, cap=True)


def shop(cam):
    boot(cam)
    show(cam, 'up', 30, 16)
    show(cam, 'a', 110, 30)
    show(cam, 'a', 90, 40)
    for _ in range(5):
        cam.tap(60, 367, 14, cap=True)


def capture(kind, directory, outdir):
    """One scene in its own process (the libretro core cannot be started twice in one process): frames go to outdir as PNGs, the BGM to outdir/pcm.raw."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cam = Cam(Path(directory).resolve())
    if kind == 'trader':
        form_trader(cam)
        parts = [('trader', cam.frames)]
        cam.frames = []
        summary(cam)
        parts.append(('summary', cam.frames))
    elif kind == 'shop':
        shop(cam)
        parts = [('shop', cam.frames)]
    else:                                         # 'bed': the Safari Zone Gate BGM
        boot(cam)
        cam.run(60 * 24, cap=True)
        (outdir / 'pcm.raw').write_bytes(b''.join(cam.audio))
        (outdir / 'rate.txt').write_text(str(round(cam.emu.sample_rate)))
        parts = []
    for name, frames in parts:
        for n, f in enumerate(frames):
            f.save(outdir / f'{name}_{n:04d}.png')
    cam.close()


def load(outdir, name):
    frames = [Image.open(f).convert('RGB') for f in sorted(Path(outdir).glob(name + '_*.png'))]
    return [f for f in frames if sum(ImageStat.Stat(f).mean) / 3 > 14]        # drop the black frames of screen transitions


def main(rom, work, out):
    work = Path(work).resolve()
    rom = Path(rom).resolve()
    a = fixture(rom, work, 'trader', 52, 30, '173,12,10')
    b = fixture(rom, work, 'shop', 66, 29, '300,16,20', flags='0x964')
    me = [sys.executable, '-s', str(Path(__file__))]
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).parent))
    for kind, d in (('trader', a), ('shop', b)):
        subprocess.run(me + ['capture', kind, str(d), str(work / ('out_' + kind))], env=env, check=True)
    trader_frames, sum_frames = load(work / 'out_trader', 'trader'), load(work / 'out_trader', 'summary')
    shop_frames = load(work / 'out_shop', 'shop')
    start_card = card(['PSYDUCK YELLOW', "Yellow's Kanto and a Johto postgame, in HeartGold's engine"], [120, 44], 3.0)
    segments = [('trader', trader_frames, 'Johto Safari Zone: swap a Pokemon for its Alolan or Galarian form'),
                ('summary', sum_frames, 'Its stats, ability and moves follow the new form'),
                ('shop', shop_frames, 'After the Hall of Fame: evolution items at the Pokemon League shop')]
    end_card = card(['WORK IN PROGRESS', 'sample cut from the game itself'], [100, 44], 3.0)
    total = sum(len(f) for _, f, _ in segments) + len(end_card) + len(start_card)
    print('seconds', round(total / FPS, 1), {n: len(f) for n, f, _ in segments})
    seconds = total / FPS

    def video():
        yield from start_card
        for _, frames, text in segments:
            for k, f in enumerate(frames):
                c = caption(screens(f), text)
                a = min(1, (k + 1) / 6, (len(frames) - k) / 6)
                yield Image.blend(Image.new('RGB', (W, H), BG), c, a)
        yield from end_card
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', 'pipe:0',
                            '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', str(out)], stdin=subprocess.PIPE)
    marks = {int(total * q) for q in (0.05, 0.2, 0.35, 0.55, 0.7, 0.85)}
    for n, f in enumerate(video()):
        enc.stdin.write(f.tobytes())
        if n in marks:
            f.resize((640, 360)).save(work / f'contact{n:05d}.png')
    enc.stdin.close()
    assert enc.wait() == 0


if __name__ == '__main__':
    if sys.argv[1] == 'capture':
        capture(*sys.argv[2:5])
    else:
        main(*sys.argv[1:4])
