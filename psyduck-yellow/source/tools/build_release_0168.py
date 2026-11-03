"""Build the public prototype-0168 (BETA 0.1.6.8) release inside the Psyduck-Yellow-Releases repo (patches and documentation only; never a ROM, save or source).

Same layout as build_release_0161.py: a self-contained prototype-0168 folder (the four older patch stages, the new final stage 0039 art -> 0168, the page, manifest and read-me),
the repository README and the development log. The page is derived from prototype-0161's. The shipped ROM is build 0170 (0168 plus the Route 7/8 tunnel fix; the owner calls it 0168).
The finished ROM the page hands out is named "Pokemon Psyduck Yellow 0-1-6-8.nds": the name the owner's 3DS forwarder CIA expects.

Usage: build_release_0168.py <releases-repo clone> <0039-art-to-0168.xdelta> <0039 art ROM> <0168 ROM>
"""
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

DATE = 'November 3, 2026'
VERSION = '0168-BETA'
LABEL = 'BETA 0.1.6.8'
FOLDER, PREVIOUS = 'prototype-0168', 'prototype-0161'
OWNER = os.environ.get('RELEASE_OWNER', 'Doctor-Pokemon')       # the account whose Psyduck-Yellow-Releases repo hosts the page
PAGE = f'https://raw.githack.com/{OWNER}/Psyduck-Yellow-Releases/main/{FOLDER}/index.html'
OUT_NAME = 'Pokemon Psyduck Yellow 0-1-6-8.nds'
OLD_OUT_NAME = 'Pokemon Psyduck Yellow BETA 0.1.61.nds'
PATCH_NAME = '0039-art-to-0168.xdelta'
SOURCE_URL = os.environ.get('SOURCE_URL', 'https://github.com/Doctor-Pokemon/corvus-workshop/tree/publish-0168/psyduck-yellow/source')

NEW_IN_0168 = [
    '**Replaces BETA 0.1.61.** Use 0.1.6.8: it also opens the way from Lavender Town to Celadon, which 0.1.61 left closed.',
    '**Route 7 / Route 8 tunnel (new):** the sealed Underground Path doors on Route 8 (east of the Saffron gatehouse) and Route 7 now lead to each other, so you can get from Lavender Town to Celadon City before Saffron opens. This is a plain door-to-door shortcut with no tunnel interior yet. The old notice on Route 7 still says the path is sealed.',
    '**Lavender Town:** the Radio Tower door leads straight to Pokémon Tower 1F and its sign reads like Yellow\'s Pokémon Tower sign; both go back to the Radio Tower after your first Hall of Fame.',
    '**Pewter City:** Brock\'s escort walks at double speed on the straights and normal speed around corners; you cannot move until he has left the screen, and he stays at his post until you hold the Boulder Badge.',
    '**Kanto Marts:** both clerks sell in every Kanto Mart: the lower clerk the supplies and the upper clerk the Poké Balls.',
    '**Bag:** the custom reusable TMs (Bide, Water Gun, Mega Punch, Whirlwind, Bubble Beam, Thunder Wave, Seismic Toss) show as TM with their number instead of "HM 00".',
    '**Vermilion Gym:** the sign now reads "The Lightning Unovan".',
]

BLURB = ('<p><strong>BETA 0.1.6.8 (prototype 0168) — for testing.</strong> The Kanto campaign from Pallet Town to the first Hall of Fame, plus the <strong>first parts of the Johto postgame</strong>. New since 0.1.61: '
         'a Route 7 / Route 8 shortcut that opens the way from Lavender Town to Celadon, a Lavender Town Pokémon Tower door and sign like Yellow\'s, a faster Pewter escort, both Mart clerks selling, TM labels in the bag and the Vermilion Gym sign.</p>'
         '<p><strong>How much has been played:</strong> the developer has played New Game through Lavender Town on earlier builds. Everything after that, and all of Johto, has only been checked in small emulator tests on prepared saves, not played through. '
         'Expect bugs, including possible softlocks. <strong>Johto is unfinished:</strong> the postgame steps listed in the notes exist, but the rest of Johto has not been checked.</p>'
         '<p>Start a <strong>New Game</strong>; saves from older prototypes are not supported. Keep this build and its saves separate.</p>')

READ_ME = f'''Pokemon Psyduck Yellow - {LABEL} (prototype 0168) BETA - {DATE}

*** BETA, FOR TESTING ONLY. NOT A COMPLETE GAME. ***
The Kanto campaign (Pallet Town to your first Hall of Fame) is built. The first parts of the Johto postgame are built too, but Johto as a whole is UNFINISHED and has not been played through.

HOW TO PLAY
1. Open the patching page: {PAGE}
2. Choose your OWN, original, unmodified USA HeartGold .nds file (not another prototype).
3. Click "Create my playable NDS", wait for the checks to finish, then download the result ("{OUT_NAME}") and load it in your DS emulator.
4. Start a NEW GAME. Saves from older prototypes do not work (a renamed old save may behave strangely). Keep this build and its saves separate, and never reuse emulator save states between versions.
Nothing is uploaded; the patching happens in your browser and every step is hash-checked. Expected final SHA256: {{sha}}

WHAT IS NEW SINCE 0.1.61 (internal builds 0162-0170)
''' + '\n'.join('- ' + x.replace('**', '') for x in NEW_IN_0168) + '''
- Everything from 0.1.61 is still here. The save layout is unchanged.

WHAT HAS BEEN TESTED
- The developer has played New Game through Lavender Town on earlier builds, partly on a real 3DS.
- Everything in the list above has only had small emulator checks on prepared test saves (the door, sign, shop or escort used once and the exit taken). The Route 7 / Route 8 shortcut was walked in both directions in the emulator and has not yet been used on a real 3DS.
- Everything after Lavender, and every Johto step, has only had small emulator checks on prepared test saves and has never been played through in one go.

NOT BUILT YET
Elevator floor-selection menus in Silph Co. and Rocket Hideout (stairs instead); the Rocket Hideout Lift Key and item balls; some stand-in wall and floor textures; Game Corner and Department Store extras; the Stellar type icon on the Pokedex info page and the PC storage preview (a placeholder shows); an interior for the Route 7 / Route 8 shortcut; most of Johto beyond the steps in earlier notes has not been checked.

KNOWN ISSUES
Reported by the developer: the top screen can turn black in the overworld; saving and reloading fixes it (not investigated).
Some move descriptions on the summary screen's Moves page are cut off at the right edge.
The Lavender Town building with the Pokemon Tower door still looks like the Radio Tower from outside.
Mega Punch and Focus Punch both show as TM 001 in the bag's TM list.
The Union Room (Pokemon Center 2nd floor) reads a missing structure and is left alone until online play exists.
One freeze was reported when arriving in Cerulean after fighting a Route 25 trainer who blocked the path (not reproduced).
In the emulator used for testing (DeSmuME), item balls, rocks and boulders are not drawn while you stand directly south of them (they stay solid and come back when you step away).
Fuchsia Gym's leader is still HeartGold's Janine (with Koga's Yellow team and her own lines), and Sabrina gives HeartGold's TM48 instead of Yellow's TM46.
Oak's complete-Pokedex check may still expect 256 species. The Forms page of a few Pokemon shows the species name twice.

Public files are patches and documentation only. No ROM, save or game file is distributed; you must supply your own legally obtained game. The source needed to rebuild this version (tools, data, notes, BUILDING.md) is at {SOURCE_URL}. Credits: BluRosie/hg-engine and contributors; the patch decoder is RomPatcher.js by Marc Robledo (MIT); Pokemon Yellow data from pret/pokeyellow.
'''

LOG_ENTRY = f'''

## {DATE} — {LABEL} (prototype 0168, BETA)

**BETA, FOR TESTING ONLY. Not a complete game. The Kanto campaign is built; the first parts of the Johto postgame are built but Johto is unfinished and has not been played through.**

[Create {LABEL}]({PAGE}). It builds from your original USA HeartGold file in your browser; nothing is uploaded. The finished game is named "{OUT_NAME}".

What changed since 0.1.61 (internal builds 0162–0170):
''' + '\n'.join('- ' + x for x in NEW_IN_0168) + '''
- Not changed: the save layout.

Reported, not fixed: the top screen sometimes turns black in the overworld (a save and reload fixes it); cut-off move descriptions on the summary Moves page; the Lavender building's outside picture; a freeze when arriving in Cerulean after Route 25 (not reproduced); the Union Room. Checked: small emulator tests on prepared saves (see the read-me). Source to rebuild this version: [{SOURCE_URL}]({SOURCE_URL}).
'''

RELEASE_BODY = f'''# ⚠️ BETA — FOR TESTING ONLY

**This is a beta for testing. It is NOT a complete version of the game.**

The **Kanto campaign (Pallet Town to your first Hall of Fame)** is built, and the **first parts of the Johto postgame** are in, but **Johto is unfinished and has not been played through**. Expect bugs, including possible softlocks.

## How to play
1. Open the **[patching page]({PAGE})**.
2. Pick your **own, original, unmodified USA HeartGold `.nds`** file.
3. Click *Create my playable NDS*, wait for the checks, then download it (**{OUT_NAME}**) and load it in your DS emulator.
4. Start a **New Game** (older saves do not work).

Nothing is uploaded; the patching runs in your browser. This release ships **no ROM or save files**; you must supply your own legally obtained game. The source needed to rebuild this version (tools, data, notes, `BUILDING.md`) is published at **[{SOURCE_URL}]({SOURCE_URL})**.

## What's new since 0.1.61
''' + '\n'.join('- ' + x for x in NEW_IN_0168) + '''

## How much has been tested
The developer has played New Game through **Lavender Town** on earlier builds. The new Route 7 / Route 8 shortcut and the other changes above have only had small emulator checks on prepared test saves. Everything after Lavender, and every Johto step, has not been played through.

## Known issues
The top screen can turn black in the overworld (a save and reload fixes it). Some move descriptions on the summary Moves page are cut off. The Lavender Pokémon Tower building still looks like the Radio Tower from outside. A freeze was reported when arriving in Cerulean after a blocked Route 25 (not reproduced). The Union Room is left alone until online play exists. In the test emulator (DeSmuME), item balls, rocks and boulders are not drawn while you stand directly south of them. Fuchsia Gym's leader is still HeartGold's Janine, and Sabrina gives TM48 instead of TM46.

Files below: the patch stage for this version, the manifest (hashes) and a plain-text read-me. Expected final SHA256: `{sha}`
'''


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main(releases, delta, art_rom, new_rom):
    rel = Path(releases)
    old, out = rel / PREVIOUS, rel / FOLDER
    out.mkdir(exist_ok=True)
    shutil.copyfile(delta, out / PATCH_NAME)
    for name in ('HG-ENGINE-CREDITS.md', 'LICENSE.txt'):
        shutil.copyfile(old / name, out / name)
    html = (old / 'index.html').read_text(encoding='utf-8')
    m = re.search(r'(<script id="package" type="application/json">)(.*?)(</script>)', html, re.S)
    package = json.loads(m.group(2))
    stages = package['stages']
    art_sha, new_sha, patch_sha = sha(art_rom), sha(new_rom), sha(delta)
    assert len(stages) == 5 and stages[3]['manifest']['output_sha256'] == art_sha
    for st in stages[:4]:                                  # mirror the older stages so this release is self-contained
        src = old / st['url']
        shutil.copyfile(src, out / src.name)
        assert sha(out / src.name) == st['manifest']['patch_sha256']
    size_art, size_new, size_patch = Path(art_rom).stat().st_size, Path(new_rom).stat().st_size, Path(delta).stat().st_size
    stages[4] = {'url': PATCH_NAME, 'bytes': size_patch,
                 'manifest': {'source_sha256': art_sha, 'source_bytes': size_art, 'output_sha256': new_sha,
                              'output_bytes': size_new, 'patch_sha256': patch_sha, 'patch_bytes': size_patch}}
    source_sha = package['manifest']['source_sha256']
    package['manifest'] = dict(version=VERSION, source_sha256=source_sha,
                               source_bytes=package['manifest']['source_bytes'], output_sha256=new_sha, output_bytes=size_new,
                               output_name=OUT_NAME, cumulative=True, roundtrip_verified=True,
                               status='BETA for testing only: Kanto through the first Hall of Fame plus the first parts of the Johto postgame; Johto unfinished; owner-played to Lavender Town only',
                               browser_patch_stages=[{'url': s['url'], 'bytes': s['bytes'], 'sha256': s['manifest']['patch_sha256']} for s in stages])
    package['patchURL'], package['patchBytes'] = PATCH_NAME, size_patch
    html = html[:m.start(2)] + json.dumps(package, ensure_ascii=False) + html[m.end(2):]
    assert html.count('0161-BETA') >= 2 and html.count(OLD_OUT_NAME) >= 1, 'page labels changed'
    html = html.replace('0161-BETA', VERSION).replace(OLD_OUT_NAME, OUT_NAME)
    lines = html.split('\n')
    i = next(k for k, l in enumerate(lines) if l.startswith('<p><strong>BETA 0.1.61'))
    lines[i] = BLURB
    html = '\n'.join(lines)
    visible = re.sub(r'<script id="package".*?</script>', '', html, flags=re.S)
    assert '0161' not in visible.replace('since 0.1.61', ''), 'stale 0161 label left in the page'
    assert html.count(OUT_NAME) >= 2, 'download name not normalised'
    assert source_sha in html, 'HeartGold source hash lost'
    (out / 'index.html').write_text(html, encoding='utf-8')
    (out / 'manifest.json').write_text(json.dumps(package['manifest'], indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (out / 'READ-ME-FIRST.txt').write_text(READ_ME.replace('{sha}', new_sha), encoding='utf-8')
    log = rel / 'DEVELOPMENT-LOG.md'                       # the releases copy only
    text = log.read_text(encoding='utf-8')
    text = re.sub(r'\*\*Last updated: [^*]*\.\*\*', f'**Last updated: {DATE}.**', text, count=1)
    log.write_text(text + LOG_ENTRY, encoding='utf-8')
    readme = (rel / 'README.md').read_text(encoding='utf-8')
    for old_text, new_text in (('**BETA 0.1.61, prototype 0161**', f'**{LABEL}, prototype 0168**'), ('(BETA 0.1.61, prototype 0161)', f'({LABEL}, prototype 0168)')):
        assert readme.count(old_text) == 1, old_text
        readme = readme.replace(old_text, new_text)
    readme = re.sub(r'\[hosted BETA 0\.1\.61 patching page\]\([^)]*\)', f'[hosted {LABEL} patching page]({PAGE})', readme)
    new_line = "- **New in 0168:** a Route 7 / Route 8 shortcut opens the way from Lavender Town to Celadon; the Lavender Pokémon Tower door and sign follow Yellow; Brock's escort in Pewter is faster; both Mart clerks sell; the custom TMs show their TM numbers; the Vermilion Gym sign reads \"The Lightning Unovan\".\n"
    marker_line = '- **New in 0161:**'
    assert readme.count(marker_line) == 1
    readme = readme.replace(marker_line, new_line + marker_line)
    entry = (f'- **{LABEL} (prototype 0168) — {DATE} (beta, testing only).** Opens the way from Lavender Town to Celadon (Route 7 / Route 8 shortcut), plus the Lavender Pokémon Tower door and sign, a faster Pewter escort, both Mart clerks selling, TM labels and the Vermilion Gym sign. Everything else as in 0.1.61. Kanto complete to the first Hall of Fame; Johto unfinished.\n')
    marker = '## Release history (newest first)\n'
    assert marker in readme
    readme = readme.replace(marker, marker + entry)
    (rel / 'README.md').write_text(readme, encoding='utf-8')
    (rel.parent / 'RELEASE_BODY.md').write_text(RELEASE_BODY.replace('{sha}', new_sha), encoding='utf-8')
    print(json.dumps({'output_sha256': new_sha, 'patch_sha256': patch_sha, 'patch_bytes': size_patch, 'out_name': OUT_NAME}))


if __name__ == '__main__':
    main(*sys.argv[1:5])
