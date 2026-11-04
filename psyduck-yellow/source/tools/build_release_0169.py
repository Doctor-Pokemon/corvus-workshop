"""Build the public prototype-0169 (BETA 0.1.6.9) release inside the Psyduck-Yellow-Releases repo (patches and documentation only; never a ROM, save or source).

Same layout as build_release_0168.py: a self-contained prototype-0169 folder (the four older patch stages, the new final stage 0039 art -> 0169, the page, manifest and read-me),
the repository README and the development log. The page is derived from prototype-0168d's. The shipped ROM is build 0185 (0173 = BETA 0.1.6.8 plus Fuchsia's Gold Teeth/Warden chain, Sabrina's Strength, Janine's Surf,
the Fuchsia gatehouse guards, the Route 12 Snorlax and Poke Flute, the slot-machine message and the Running Shoes / Silph Scope icons).
The finished ROM the page hands out is named "Pokemon Psyduck Yellow 0-1-6-9.nds".

Usage: build_release_0169.py <releases-repo clone> <0039-art-to-0169.xdelta> <0039 art ROM> <0169 ROM>
"""
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

DATE = 'November 4, 2026'
VERSION = '0169-BETA'
LABEL = 'BETA 0.1.6.9'
FOLDER, PREVIOUS = 'prototype-0169', 'prototype-0168d'      # a new folder because the page host caches by path
OWNER = os.environ.get('RELEASE_OWNER', 'Doctor-Pokemon')       # the account whose Psyduck-Yellow-Releases repo hosts the page
PAGE = f'https://raw.githack.com/{OWNER}/Psyduck-Yellow-Releases/main/{FOLDER}/index.html'
OUT_NAME = 'Pokemon Psyduck Yellow 0-1-6-9.nds'
OLD_OUT_NAME = 'Pokemon Psyduck Yellow 0-1-6-8.nds'
PATCH_NAME = '0039-art-to-0169.xdelta'
SOURCE_URL = os.environ.get('SOURCE_URL', 'https://github.com/Doctor-Pokemon/corvus-workshop/tree/publish-0169/psyduck-yellow/source')

NEW_IN_0169 = [
    '**Replaces BETA 0.1.6.8.** Use 0.1.6.9: it has everything 0.1.6.8 had and finishes the road to Fuchsia: Strength and Surf can now be obtained in the game.',
    '**Strength and Surf (new):** Sabrina gives you HM04 Strength after the Marsh Badge, and Janine (Fuchsia Gym) gives you HM03 Surf after your first win there, each once and with a new line from the leader. Strength now works with the Plain Badge or the Marsh Badge (it used to accept the Rainbow Badge). The Safari Zone is no longer on the route (HeartGold already has one in Johto).',
    '**Fuchsia City (new):** Officer Jenny now stands in the Route 15 and Route 18 gatehouses and turns you back, with a rockslide line, until you hold the Marsh Badge (the Route 19 gatehouse was already closed). The Warden\'s granddaughter gives you his GOLD TEETH; the Warden thanks you with a NUGGET and a pun, then gives a NUGGET once a day, and after that he is only at home in the day and evening. Fixed: a full bag at his first NUGGET no longer leaves him mumbling forever.',
    '**Route 12 Snorlax (new):** a sleeping Snorlax now sits on the Route 12 side pier from the start of the game (HeartGold hid it until the postgame). Talk to it with the Poke Flute from Mr. Fuji: you play the flute (jingle and message), it wakes and you battle it. The Poke Flute is now a real key item: it sits in the Key Items pocket, cannot be thrown away, and has the Yellow Flute\'s icon.',
    '**Celadon Game Corner:** pressing A on a slot machine now shows "This machine is out of order." instead of hanging the game.',
    '**Bag icons:** the Running Shoes and the Silph Scope have real icons instead of the "?" placeholder.',
]

BLURB = ('<p><strong>BETA 0.1.6.9 (prototype 0169) — for testing.</strong> The Kanto campaign from Pallet Town to the first Hall of Fame, plus the <strong>first parts of the Johto postgame</strong>. New since 0.1.6.8: '
         'Strength (from Sabrina) and Surf (from Janine) can be obtained, Officer Jenny closes the Fuchsia gatehouses until the Marsh Badge, the Warden\'s Gold Teeth and Nugget routine, a sleeping Snorlax on Route 12 that the Poke Flute wakes, '
         'an out-of-order message on the Game Corner slot machines, and real icons for the Running Shoes and Silph Scope. Details are in the notes below.</p>'
         '<p><strong>How much has been played:</strong> the developer has played New Game through Lavender Town on earlier builds. Everything after that, and all of Johto, has only been checked in small emulator tests on prepared saves, not played through. '
         'Expect bugs, including possible softlocks. <strong>Johto is unfinished:</strong> the postgame steps listed in the notes exist, but the rest of Johto has not been checked.</p>'
         '<p>Start a <strong>New Game</strong>; saves from older prototypes are not supported. Keep this build and its saves separate.</p>')

READ_ME = f'''Pokemon Psyduck Yellow - {LABEL} (prototype 0169) BETA - {DATE}

*** BETA, FOR TESTING ONLY. NOT A COMPLETE GAME. ***
The Kanto campaign (Pallet Town to your first Hall of Fame) is built. The first parts of the Johto postgame are built too, but Johto as a whole is UNFINISHED and has not been played through.

HOW TO PLAY
1. Open the patching page: {PAGE}
2. Choose your OWN, original, unmodified USA HeartGold .nds file (not another prototype).
3. Click "Create my playable NDS", wait for the checks to finish, then download the result ("{OUT_NAME}") and load it in your DS emulator.
4. Start a NEW GAME. Saves from older prototypes do not work (a renamed old save may behave strangely). Keep this build and its saves separate, and never reuse emulator save states between versions.
Nothing is uploaded; the patching happens in your browser and every step is hash-checked. Expected final SHA256: {{sha}}

WHAT IS NEW SINCE 0.1.6.8 (internal builds 0174-0185)
''' + '\n'.join('- ' + x.replace('**', '') for x in NEW_IN_0169) + '''
- Everything from 0.1.6.8 is still here. The save layout is unchanged.

WHAT HAS BEEN TESTED
- The developer has played New Game through Lavender Town on earlier builds, partly on a real 3DS.
- Everything in the list above has only had small emulator checks on prepared test saves (the leader talked to and the HM received, the gatehouse blocked and walked through, the Warden present and absent, the Snorlax woken with and without the flute, a slot machine pressed, the bag opened). None of it has been confirmed on a real 3DS yet, and the bag-full cases for the HM gifts were not tested.
- Everything after Lavender, and every Johto step, has only had small emulator checks on prepared test saves and has never been played through in one go.

NOT BUILT YET
Elevator floor-selection menus in Silph Co. and Rocket Hideout (stairs instead); the Rocket Hideout Lift Key and item balls; some stand-in wall and floor textures; the Game Corner slot games and Department Store extras; a USE button for the Poke Flute in the bag (it is played when you talk to the Snorlax); Yellow\'s second Snorlax on Route 16; the Stellar type icon on the Pokedex info page and the PC storage preview (a placeholder shows); an interior for the Route 7 / Route 8 shortcut; door art for the new door in Mr. Game\'s north wall (it shows a picture; you walk up into it); most of Johto beyond the steps in earlier notes has not been checked.

KNOWN ISSUES
Reported by the developer: the top screen can turn black in the overworld; saving and reloading fixes it (not investigated).
Some move descriptions on the summary screen's Moves page are cut off at the right edge.
The Lavender Town building with the Pokemon Tower door still looks like the Radio Tower from outside.
The new door in the north wall of Mr. Game's room (Celadon) is drawn as a picture, with no door art yet.
The Route 12 Snorlax sleeps at the west end of the side pier where Route 12 meets Route 11, not on the main pier, so it does not block the road to Fuchsia; the Fuchsia gatehouses are what keep you out until the Marsh Badge.
Mega Punch and Focus Punch both show as TM 001 in the bag's TM list.
The Union Room (Pokemon Center 2nd floor) reads a missing structure and is left alone until online play exists.
One freeze was reported when arriving in Cerulean after fighting a Route 25 trainer who blocked the path (not reproduced).
In the emulator used for testing (DeSmuME), item balls, rocks and boulders are not drawn while you stand directly south of them (they stay solid and come back when you step away).
Fuchsia Gym's leader is still HeartGold's Janine (with Koga's Yellow team and her own lines), and Sabrina gives HeartGold's TM48 instead of Yellow's TM46.
The Gen 5-9 items that were added for the Johto postgame still show a "?" icon in the bag (the Kanto campaign does not hand any out).
Oak's complete-Pokedex check may still expect 256 species. The Forms page of a few Pokemon shows the species name twice.

Public files are patches and documentation only. No ROM, save or game file is distributed; you must supply your own legally obtained game. The source needed to rebuild this version (tools, data, notes, BUILDING.md) is at {SOURCE_URL}. Credits: BluRosie/hg-engine and contributors; the patch decoder is RomPatcher.js by Marc Robledo (MIT); Pokemon Yellow data from pret/pokeyellow.
'''

LOG_ENTRY = f'''

## {DATE} — {LABEL} (prototype 0169, BETA)

**BETA, FOR TESTING ONLY. Not a complete game. The Kanto campaign is built; the first parts of the Johto postgame are built but Johto is unfinished and has not been played through.**

[Create {LABEL}]({PAGE}). It builds from your original USA HeartGold file in your browser; nothing is uploaded. The finished game is named "{OUT_NAME}".

What changed since 0.1.6.8 (internal builds 0174–0185):
''' + '\n'.join('- ' + x for x in NEW_IN_0169) + '''
- Not changed: the save layout.

Reported, not fixed: the top screen sometimes turns black in the overworld (a save and reload fixes it); cut-off move descriptions on the summary Moves page; the Lavender building's outside picture; a freeze when arriving in Cerulean after Route 25 (not reproduced); the Union Room; no USE button for the Poke Flute in the bag; the Gen 5-9 items still show a "?" icon. Checked: small emulator tests on prepared saves (see the read-me), nothing confirmed on a real 3DS yet. Source to rebuild this version: [{SOURCE_URL}]({SOURCE_URL}).
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

## What's new since 0.1.6.8
''' + '\n'.join('- ' + x for x in NEW_IN_0169) + '''

## How much has been tested
The developer has played New Game through **Lavender Town** on earlier builds. The changes above have only had small emulator checks on prepared test saves and are not confirmed on a real 3DS. Everything after Lavender, and every Johto step, has not been played through.

## Known issues
The top screen can turn black in the overworld (a save and reload fixes it). Some move descriptions on the summary Moves page are cut off. The Lavender Pokémon Tower building still looks like the Radio Tower from outside. The Poke Flute has no USE button in the bag (it is played when you talk to the Snorlax). The Route 12 Snorlax sleeps beside the main pier and does not block it. A freeze was reported when arriving in Cerulean after a blocked Route 25 (not reproduced). The Union Room is left alone until online play exists. The Gen 5-9 items added for Johto still show a "?" icon. In the test emulator (DeSmuME), item balls, rocks and boulders are not drawn while you stand directly south of them. Fuchsia Gym's leader is still HeartGold's Janine, and Sabrina gives TM48 instead of Yellow's TM46.

Files below: the patch stage for this version, the manifest (hashes) and a plain-text read-me. Expected final SHA256: `{{sha}}`
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
    assert html.count('0168-BETA') >= 2 and html.count(OLD_OUT_NAME) >= 1, 'page labels changed'
    html = html.replace('0168-BETA', VERSION).replace(OLD_OUT_NAME, OUT_NAME)
    lines = html.split('\n')
    i = next(k for k, l in enumerate(lines) if l.startswith('<p><strong>BETA 0.1.6.8'))
    lines[i] = BLURB
    html = '\n'.join(lines)
    visible = re.sub(r'<script id="package".*?</script>', '', html, flags=re.S)
    assert '0168' not in visible.replace('since 0.1.6.8', '').replace('0.1.6.8', ''), 'stale 0168 label left in the page'
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
    for old_text, new_text in (('**BETA 0.1.6.8, prototype 0168**', f'**{LABEL}, prototype 0169**'), ('(BETA 0.1.6.8, prototype 0168)', f'({LABEL}, prototype 0169)')):
        assert readme.count(old_text) == 1, old_text
        readme = readme.replace(old_text, new_text)
    readme = re.sub(r'\[hosted BETA 0\.1\.6\.8 patching page\]\([^)]*\)', f'[hosted {LABEL} patching page]({PAGE})', readme)
    new_line = "- **New in 0169:** Strength (from Sabrina, with the Marsh Badge) and Surf (from Janine) can be obtained; Officer Jenny closes the Route 15 and Route 18 gatehouses to Fuchsia until the Marsh Badge; the Warden's granddaughter gives his Gold Teeth and he rewards you with Nuggets; a sleeping Snorlax on Route 12 wakes to the Poké Flute (now a real key item); the Game Corner slot machines say they are out of order; the Running Shoes and Silph Scope have real icons.\\n"
    marker_line = '- **New in 0168:**'
    assert readme.count(marker_line) == 1
    readme = readme.replace(marker_line, new_line + marker_line)
    entry = (f'- **{LABEL} (prototype 0169) — {DATE} (beta, testing only).** Strength from Sabrina and Surf from Janine, Officer Jenny closing the Fuchsia gatehouses until the Marsh Badge, the Warden\'s Gold Teeth and Nugget routine, a sleeping Route 12 Snorlax woken with the Poké Flute (now a real key item), an out-of-order message on the Game Corner slot machines, and real Running Shoes and Silph Scope icons. [Patching page]({PAGE}).\\n')
    marker = '## Release history (newest first)\n'
    assert marker in readme
    readme = readme.replace(marker, marker + entry)
    (rel / 'README.md').write_text(readme, encoding='utf-8')
    (rel.parent / 'RELEASE_BODY.md').write_text(RELEASE_BODY.replace('{sha}', new_sha), encoding='utf-8')
    print(json.dumps({'output_sha256': new_sha, 'patch_sha256': patch_sha, 'patch_bytes': size_patch, 'out_name': OUT_NAME}))


if __name__ == '__main__':
    main(*sys.argv[1:5])
