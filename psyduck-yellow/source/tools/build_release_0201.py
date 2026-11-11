"""Build the public prototype-0201 (BETA 0.2.0.1) release inside the Psyduck-Yellow-Releases repo (patches and documentation only; never a ROM, save or source).
Same layout as build_release_0200.py: a self-contained prototype-0201 folder (the four older patch stages, the new final stage 0039 art -> 0201, the page, manifest and read-me), the README, the CHANGELOG and the development log.
The page is derived from prototype-0200's. The shipped ROM is build 0234 = the published ROM 0230 + tools/form_trader_hisui.py ONLY (owner 2026-11-11: the only listed change is "Added Hisuian Forms to Form Trader NPC.").
The finished ROM the page hands out is named "Pokemon Psyduck Yellow 0-2-0-1.nds". All NEW public text is free of any mention of the Mega Evolution content (owner rule 2026-11-04); the builder asserts that no file it writes (or line it adds) contains the word.
Disclaimer (owner 2026-11-11), on every page and note: "All features may not be in final version."
Usage: build_release_0201.py <releases-repo clone> <0039-art-to-0201.xdelta> <0039 art ROM> <0234 ROM>
"""
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

DATE = 'November 11, 2026'
VERSION = '0201-BETA'
LABEL = 'BETA 0.2.0.1'
TITLE = 'Pokémon Psyduck Yellow (BETA 0.2.0.1)'
DISCLAIMER = 'All features may not be in final version.'
FOLDER, PREVIOUS = 'prototype-0201', 'prototype-0200'      # a new folder because the page host caches by path
OWNER = os.environ.get('RELEASE_OWNER', 'Doctor-Pokemon')
PAGE = f'https://raw.githack.com/{OWNER}/Psyduck-Yellow-Releases/main/{FOLDER}/index.html'
OUT_NAME = 'Pokemon Psyduck Yellow 0-2-0-1.nds'
OLD_OUT_NAME = 'Pokemon Psyduck Yellow 0-2-0-0.nds'
PATCH_NAME = '0039-art-to-0201.xdelta'
SOURCE_URL = os.environ.get('SOURCE_URL', 'https://github.com/Doctor-Pokemon/corvus-workshop/tree/publish-0201/psyduck-yellow/source')
SECRET_WORD = re.compile('mega', re.I)

NEW_IN_0201 = [
    f'**Replaces BETA 0.2.0.0.** Everything from 0.2.0.0 is still here. **{DISCLAIMER}**',
    'Added Hisuian Forms to Form Trader NPC.',
]
KNOWN_ISSUES = [
    'The top screen can turn black in the overworld (a save and reload fixes it).',
    "Some move descriptions on the summary screen's Moves page are cut off at the right edge.",
    'Two red-screen crashes were each reported once on a real 3DS and could not be reproduced: falling off the path on the way out of the Ecruteak Gym, and opening the Pokémon menu.',
    'The new wild Pokémon, the League shop, the evolution changes and the Form Trader have only had small emulator tests on prepared saves; most of the forms the Form Trader offers were never tried. Wild Pokémon levels in Johto are not scaled by badges yet.',
    'Many of the added Gen 5-9 items still show a "?" icon in the bag.',
    'The Lavender Town building with the Pokémon Tower door still looks like the Radio Tower from outside.',
    'Johto is unfinished.',
]
TESTED = ("The developer has played New Game through Lavender Town on earlier builds, partly on a real 3DS. On a real 3DS the Johto Gym Leaders' presence and level scaling and Morty's battle have been confirmed, and one Form Trader swap (Typhlosion to Hisuian Typhlosion). "
          "Everything else has only had small emulator checks on prepared test saves and is not confirmed on hardware. Everything after Lavender and most of Johto has never been played through in one go.")

BLURB = (f'<p><strong>{LABEL} (prototype 0201) — for testing.</strong> The Kanto campaign from Pallet Town to the first Hall of Fame, plus <strong>more of the Johto postgame</strong>. New since 0.2.0.0: '
         f'Hisuian forms at the Form Trader NPC. Details are in the notes below. <strong>{DISCLAIMER}</strong></p>'
         '<p><strong>How much has been played:</strong> the developer has played New Game through Lavender Town on earlier builds. Most of the newer parts have only been checked in small emulator tests on prepared saves, not played through. '
         'Expect bugs, including possible softlocks. <strong>Johto is unfinished.</strong></p>'
         '<p>Start a <strong>New Game</strong>; saves from older prototypes are not supported. Keep this build and its saves separate.</p>')

READ_ME = f'''Pokemon Psyduck Yellow - {LABEL} (prototype 0201) BETA - {DATE}

*** {DISCLAIMER.upper()} ***
*** BETA, FOR TESTING ONLY. NOT A COMPLETE GAME. ***
The Kanto campaign (Pallet Town to your first Hall of Fame) is built, and more of the Johto postgame is built too, but Johto as a whole is UNFINISHED and has not been played through.

HOW TO PLAY
1. Open the patching page: {PAGE}
2. Choose your OWN, original, unmodified USA HeartGold .nds file (not another prototype).
3. Click "Create my playable NDS", wait for the checks to finish, then download the result ("{OUT_NAME}") and load it in your DS emulator.
4. Start a NEW GAME. Saves from older prototypes do not work. Keep this build and its saves separate, and never reuse emulator save states between versions.
Nothing is uploaded; the patching happens in your browser and every step is hash-checked. Expected final SHA256: {{sha}}

WHAT IS NEW SINCE 0.2.0.0
''' + '\n'.join('- ' + x.replace('**', '') for x in NEW_IN_0201) + f'''
- The save layout is unchanged.

WHAT HAS BEEN TESTED
{TESTED}

KNOWN ISSUES
''' + '\n'.join('- ' + x for x in KNOWN_ISSUES) + f'''

Public files are patches and documentation only. No ROM, save or game file is distributed; you must supply your own legally obtained game. The source needed to rebuild this version (tools, data, notes, BUILDING.md, development documents) is at {SOURCE_URL}. Credits: BluRosie/hg-engine, the pret projects, RomPatcher.js (see HG-ENGINE-CREDITS.md and LICENSE.txt in this folder).
'''

LOG_ENTRY = f'''

## {DATE} — {LABEL} (prototype 0201, BETA)

**{DISCLAIMER} BETA, FOR TESTING ONLY. Not a complete game. The Kanto campaign is built; more of the Johto postgame is built but Johto is unfinished and has not been played through.**

[Create {LABEL}]({PAGE}). It builds from your original USA HeartGold file in your browser; nothing is uploaded. The finished game is named "{OUT_NAME}".

What changed since 0.2.0.0:
''' + '\n'.join('- ' + x for x in NEW_IN_0201[1:]) + '''
- Not changed: the save layout.

Known issues: ''' + ' '.join(KNOWN_ISSUES) + '\n'

CHANGELOG_ENTRY = f'''## {LABEL} (prototype 0201) — {DATE}
**{DISCLAIMER}**
''' + '\n'.join('- ' + x for x in NEW_IN_0201[1:]) + '''

'''

RELEASE_BODY = f'''# ⚠️ BETA — FOR TESTING ONLY

**{DISCLAIMER}**

**This is a beta for testing. It is NOT a complete version of the game.**

The **Kanto campaign (Pallet Town to your first Hall of Fame)** is built, and **more of the Johto postgame** is in, but **Johto is unfinished and has not been played through**. Expect bugs, including possible softlocks.

## How to play
1. Open the **[patching page]({PAGE})**.
2. Pick your **own, original, unmodified USA HeartGold `.nds`** file.
3. Click *Create my playable NDS*, wait for the checks, then download it (**{OUT_NAME}**) and load it in your DS emulator.
4. Start a **New Game** (older saves do not work).

Nothing is uploaded; the patching runs in your browser. This release ships **no ROM or save files**; you must supply your own legally obtained game. The source needed to rebuild this version (tools, data, notes, `BUILDING.md`, development documents) is published at **[{SOURCE_URL}]({SOURCE_URL})**.

## What's new since 0.2.0.0
''' + '\n'.join('- ' + x for x in NEW_IN_0201) + f'''

## How much has been tested
{TESTED}

## Known issues
''' + '\n'.join('- ' + x for x in KNOWN_ISSUES) + '''

Files below: the patch stage for this version, the manifest (hashes) and a plain-text read-me. Expected final SHA256: `{sha}`
'''


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def scrub(value):
    """Drop every key and every sentence that mentions the withheld content from the page's inherited stage manifests."""
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items() if not SECRET_WORD.search(k)}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, str) and SECRET_WORD.search(value):
        return ' '.join(s for s in re.split(r'(?<=[.!?])\s+', value) if not SECRET_WORD.search(s))
    return value


def clean(label, text):
    assert not SECRET_WORD.search(text), f'withheld word in new public text: {label}'
    return text


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
                               status='BETA for testing only. All features may not be in final version. Kanto through the first Hall of Fame plus more of the Johto postgame; Johto unfinished; owner-played to Lavender Town only',
                               browser_patch_stages=[{'url': s['url'], 'bytes': s['bytes'], 'sha256': s['manifest']['patch_sha256']} for s in stages])
    package['patchURL'], package['patchBytes'] = PATCH_NAME, size_patch
    package = scrub(package)
    html = html[:m.start(2)] + json.dumps(package, ensure_ascii=False) + html[m.end(2):]
    assert html.count('0200-BETA') >= 2 and html.count(OLD_OUT_NAME) >= 1, 'page labels changed'
    html = html.replace('0200-BETA', VERSION).replace(OLD_OUT_NAME, OUT_NAME)
    lines = html.split('\n')
    i = next(k for k, l in enumerate(lines) if l.startswith('<p><strong>BETA 0.2.0.0'))
    lines[i] = BLURB
    html = '\n'.join(lines)
    visible = re.sub(r'<script id="package".*?</script>', '', html, flags=re.S)
    assert '0200' not in visible, 'stale 0200 label left in the page'
    assert html.count(OUT_NAME) >= 2, 'download name not normalised'
    assert source_sha in html, 'HeartGold source hash lost'
    (out / 'index.html').write_text(clean('index.html', html), encoding='utf-8')
    (out / 'manifest.json').write_text(clean('manifest.json', json.dumps(package['manifest'], indent=2, ensure_ascii=False) + '\n'), encoding='utf-8')
    (out / 'READ-ME-FIRST.txt').write_text(clean('READ-ME-FIRST.txt', READ_ME.replace('{sha}', new_sha)), encoding='utf-8')
    log = rel / 'DEVELOPMENT-LOG.md'                       # the releases copy only
    text = log.read_text(encoding='utf-8')
    text = re.sub(r'\*\*Last updated: [^*]*\.\*\*', f'**Last updated: {DATE}.**', text, count=1)
    log.write_text(text + clean('DEVELOPMENT-LOG entry', LOG_ENTRY), encoding='utf-8')
    changelog = rel / 'CHANGELOG.md'
    text = changelog.read_text(encoding='utf-8')
    marker = '## BETA 0.2.0.0 (prototype 0200)'
    assert text.count(marker) == 1
    changelog.write_text(text.replace(marker, clean('CHANGELOG entry', CHANGELOG_ENTRY) + marker), encoding='utf-8')
    readme = (rel / 'README.md').read_text(encoding='utf-8')

    def swap(old_text, new_text, count=1):
        nonlocal readme
        assert readme.count(old_text) == count, (old_text, readme.count(old_text))
        readme = readme.replace(old_text, clean('README', new_text))
    swap('The newest release (**BETA 0.2.0.0, prototype 0200**) is for testing. **It is NOT a complete game.** *All features may not be in final version.*',
         f'The newest release (**{LABEL}, prototype 0201**) is for testing. **It is NOT a complete game.** *{DISCLAIMER}*')
    swap('## Where it stands right now (BETA 0.2.0.0, prototype 0200)', f'## Where it stands right now ({LABEL}, prototype 0201)')
    readme = re.sub(r'- \*\*Played by the developer:\*\*[^\n]*', clean('README', "- **Played by the developer:** New Game through Lavender Town on earlier builds. Most of what is new since 0.2.0.0 has only had small emulator tests on prepared saves; the Johto Gym Leaders' presence and level scaling, Morty's battle and one Form Trader swap (Typhlosion to Hisuian Typhlosion) are confirmed on a real 3DS. Expect bugs, including softlocks."), readme, count=1)
    new_line = '- **New in 0201:** ' + ' '.join(re.sub(r'\*\*', '', x) for x in NEW_IN_0201[1:]) + '\n'
    swap('- **New in 0200:**', new_line + '- **New in 0200:**')
    swap('[hosted BETA 0.2.0.0 patching page](https://raw.githack.com/Doctor-Pokemon/Psyduck-Yellow-Releases/main/prototype-0200/index.html)', f'[hosted {LABEL} patching page]({PAGE})')
    entry = f'- **{LABEL} (prototype 0201) — {DATE} (beta, testing only).** {DISCLAIMER} Added Hisuian Forms to Form Trader NPC. Kanto complete to the first Hall of Fame; Johto unfinished.\n'
    swap('## Release history (newest first)\n', '## Release history (newest first)\n' + entry)
    (rel / 'README.md').write_text(readme, encoding='utf-8')
    (rel.parent / 'RELEASE_BODY.md').write_text(clean('RELEASE_BODY', RELEASE_BODY.replace('{sha}', new_sha)), encoding='utf-8')
    (rel.parent / 'RELEASE_TITLE.txt').write_text(TITLE, encoding='utf-8')
    print(json.dumps({'output_sha256': new_sha, 'patch_sha256': patch_sha, 'patch_bytes': size_patch, 'out_name': OUT_NAME, 'title': TITLE}))


if __name__ == '__main__':
    main(*sys.argv[1:5])
