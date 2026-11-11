"""Build the public prototype-0200 (BETA 0.2.0.0) release inside the Psyduck-Yellow-Releases repo (patches and documentation only; never a ROM, save or source).
Same layout as build_release_0169.py: a self-contained prototype-0200 folder (the four older patch stages, the new final stage 0039 art -> 0200, the page, manifest and read-me), the README, the CHANGELOG and the development log.
The page is derived from prototype-0169's. The shipped ROM is build 0230 (form-trader). The finished ROM the page hands out is named "Pokemon Psyduck Yellow 0-2-0-0.nds". All NEW public text is free of any mention of the Mega Evolution content (owner rule 2026-11-04);
the stage manifests inherited from the old page are scrubbed of it too, and the builder asserts that no file it writes (or line it adds) contains the word.
Disclaimer (owner 2026-11-11), on every page and note: "All features may not be in final version."
Usage: build_release_0200.py <releases-repo clone> <0039-art-to-0200.xdelta> <0039 art ROM> <0230 ROM>
"""
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

DATE = 'November 11, 2026'
VERSION = '0200-BETA'
LABEL = 'BETA 0.2.0.0'
TITLE = 'Pokémon Psyduck Yellow (BETA 0.2.0.0)'
DISCLAIMER = 'All features may not be in final version.'
FOLDER, PREVIOUS = 'prototype-0200', 'prototype-0169'      # a new folder because the page host caches by path
OWNER = os.environ.get('RELEASE_OWNER', 'Doctor-Pokemon')
PAGE = f'https://raw.githack.com/{OWNER}/Psyduck-Yellow-Releases/main/{FOLDER}/index.html'
OUT_NAME = 'Pokemon Psyduck Yellow 0-2-0-0.nds'
OLD_OUT_NAME = 'Pokemon Psyduck Yellow 0-1-6-9.nds'
PATCH_NAME = '0039-art-to-0200.xdelta'
SOURCE_URL = os.environ.get('SOURCE_URL', 'https://github.com/Doctor-Pokemon/corvus-workshop/tree/publish-0200/psyduck-yellow/source')
SECRET_WORD = re.compile('mega', re.I)

NEW_IN_0200 = [
    f'**Replaces BETA 0.1.6.9.** Everything from 0.1.6.9 is still here. **{DISCLAIMER}**',
    "**Johto postgame, further along:** the first Johto scenes (Elm's lab, the New Bark Town and Route 29 gate scenes) were repaired; a Johto Gym Leader is always in the gym until you have beaten him, and the postgame weekday schedule applies afterwards; Johto Gym Leaders' teams scale with your Johto badges; the S.S. Aqua ferry and its lost-granddaughter quest follow HeartGold's own flow.",
    '**HMs from the Kanto gyms:** Brock gives Rock Smash, Misty Waterfall, Surge Fly, Blaine Rock Climb and Giovanni Whirlpool; the S.S. Anne captain gives Cut; Sabrina still gives Strength and Janine Surf. Each leader says what the HM does in the field and which Badge unlocks it.',
    '**Silph Co. Field Kit:** after the Master Ball the Silph Co. President also gives you a Field Kit. With the right Badge it lets you clear Cut trees, Rock Smash rocks and Strength boulders without a Pokémon that knows the move.',
    "**Bag descriptions:** items show real descriptions again (HeartGold's own text for the original items, new text for 52 of the added items).",
    '**National Dex after your first Hall of Fame:** Kanto and Johto then use a second set of wild Pokémon tables. Hundreds of species the game never handed out now turn up in the rarer slots of grass, caves and water (legendary-class Pokémon are held back for later events). Before the first Hall of Fame nothing changes.',
    '**Evolutions:** the Linking Cord now evolves every Pokémon that evolves by trade. Spritzee needs a held Sachet and Swirlix a held Whipped Dream, as in the games, and Kubfu can use its Scrolls.',
    '**Pokémon League shop:** after your first Hall of Fame the clerk in the Pokémon League lobby also sells the evolution items nothing else gives out (the stones, Linking Cord, Whipped Dream, Sachet, Apples, Pots, Galarica items, Black Augurite, Peat Block, Scrolls, Armors and Metal Alloy).',
    '**Form Trader:** a new NPC in the Johto Safari Zone Gate swaps a Pokémon for its Alolan or Galarian form (34 forms). Its stats, ability and moves follow the new form. The swap is one way.',
    '**3DS:** a red-screen crash right before Morty\'s battle was worked around (confirmed on a real 3DS).',
]
KNOWN_ISSUES = [
    'The top screen can turn black in the overworld (a save and reload fixes it).',
    "Some move descriptions on the summary screen's Moves page are cut off at the right edge.",
    'Two red-screen crashes were each reported once on a real 3DS and could not be reproduced: falling off the path on the way out of the Ecruteak Gym, and opening the Pokémon menu.',
    'The new wild Pokémon, the League shop, the evolution changes and the Form Trader have only had small emulator tests on prepared saves; most of the 34 forms were never tried. Wild Pokémon levels in Johto are not scaled by badges yet.',
    'Many of the added Gen 5-9 items still show a "?" icon in the bag.',
    'The Lavender Town building with the Pokémon Tower door still looks like the Radio Tower from outside.',
    'Johto is unfinished.',
]
TESTED = ("The developer has played New Game through Lavender Town on earlier builds, partly on a real 3DS. On a real 3DS the Johto Gym Leaders' presence and level scaling and Morty's battle have been confirmed. "
          "Everything else in the list above has only had small emulator checks on prepared test saves and is not confirmed on hardware. Everything after Lavender and most of Johto has never been played through in one go.")

BLURB = (f'<p><strong>{LABEL} (prototype 0200) — for testing.</strong> The Kanto campaign from Pallet Town to the first Hall of Fame, plus <strong>more of the Johto postgame</strong>. New since 0.1.6.9: '
         'HMs handed out by the Kanto Gym Leaders, the Silph Co. Field Kit, bag descriptions, a second set of wild Pokémon after your first Hall of Fame, a Linking Cord that evolves every trade evolution, evolution items in the Pokémon League shop, '
         f'and a Form Trader for Alolan and Galarian forms. Details are in the notes below. <strong>{DISCLAIMER}</strong></p>'
         '<p><strong>How much has been played:</strong> the developer has played New Game through Lavender Town on earlier builds. Most of the new parts have only been checked in small emulator tests on prepared saves, not played through. '
         'Expect bugs, including possible softlocks. <strong>Johto is unfinished.</strong></p>'
         '<p>Start a <strong>New Game</strong>; saves from older prototypes are not supported. Keep this build and its saves separate.</p>')

READ_ME = f'''Pokemon Psyduck Yellow - {LABEL} (prototype 0200) BETA - {DATE}

*** {DISCLAIMER.upper()} ***
*** BETA, FOR TESTING ONLY. NOT A COMPLETE GAME. ***
The Kanto campaign (Pallet Town to your first Hall of Fame) is built, and more of the Johto postgame is built too, but Johto as a whole is UNFINISHED and has not been played through.

HOW TO PLAY
1. Open the patching page: {PAGE}
2. Choose your OWN, original, unmodified USA HeartGold .nds file (not another prototype).
3. Click "Create my playable NDS", wait for the checks to finish, then download the result ("{OUT_NAME}") and load it in your DS emulator.
4. Start a NEW GAME. Saves from older prototypes do not work. Keep this build and its saves separate, and never reuse emulator save states between versions.
Nothing is uploaded; the patching happens in your browser and every step is hash-checked. Expected final SHA256: {{sha}}

WHAT IS NEW SINCE 0.1.6.9
''' + '\n'.join('- ' + x.replace('**', '') for x in NEW_IN_0200) + f'''
- The save layout is unchanged.

WHAT HAS BEEN TESTED
{TESTED}

KNOWN ISSUES
''' + '\n'.join('- ' + x for x in KNOWN_ISSUES) + f'''

Public files are patches and documentation only. No ROM, save or game file is distributed; you must supply your own legally obtained game. The source needed to rebuild this version (tools, data, notes, BUILDING.md, development documents) is at {SOURCE_URL}. Credits: BluRosie/hg-engine, the pret projects, RomPatcher.js (see HG-ENGINE-CREDITS.md and LICENSE.txt in this folder).
'''

LOG_ENTRY = f'''

## {DATE} — {LABEL} (prototype 0200, BETA)

**{DISCLAIMER} BETA, FOR TESTING ONLY. Not a complete game. The Kanto campaign is built; more of the Johto postgame is built but Johto is unfinished and has not been played through.**

[Create {LABEL}]({PAGE}). It builds from your original USA HeartGold file in your browser; nothing is uploaded. The finished game is named "{OUT_NAME}".

What changed since 0.1.6.9 (internal builds 0186-0230):
''' + '\n'.join('- ' + x for x in NEW_IN_0200) + '''
- Not changed: the save layout.

Known issues: ''' + ' '.join(KNOWN_ISSUES) + '\n'

CHANGELOG_ENTRY = f'''## {LABEL} (prototype 0200) — {DATE}
**{DISCLAIMER}**
''' + '\n'.join('- ' + x for x in NEW_IN_0200[1:]) + '''
- Checked mostly with small emulator tests on prepared saves; only some Johto parts are confirmed on a real 3DS.

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

## What's new since 0.1.6.9
''' + '\n'.join('- ' + x for x in NEW_IN_0200) + f'''

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
    assert html.count('0169-BETA') >= 2 and html.count(OLD_OUT_NAME) >= 1, 'page labels changed'
    html = html.replace('0169-BETA', VERSION).replace(OLD_OUT_NAME, OUT_NAME)
    lines = html.split('\n')
    i = next(k for k, l in enumerate(lines) if l.startswith('<p><strong>BETA 0.1.6.9'))
    lines[i] = BLURB
    html = '\n'.join(lines)
    visible = re.sub(r'<script id="package".*?</script>', '', html, flags=re.S)
    assert '0169' not in visible.replace('since 0.1.6.9', '').replace('0.1.6.9', ''), 'stale 0169 label left in the page'
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
    marker = '## BETA 0.1.6.9 (prototype 0169)'
    assert text.count(marker) == 1
    changelog.write_text(text.replace(marker, clean('CHANGELOG entry', CHANGELOG_ENTRY) + marker), encoding='utf-8')
    readme = (rel / 'README.md').read_text(encoding='utf-8')

    def swap(old_text, new_text, count=1):
        nonlocal readme
        assert readme.count(old_text) == count, (old_text, readme.count(old_text))
        readme = readme.replace(old_text, clean('README', new_text))
    # the intro lines mention the withheld content: drop those phrases (the owner's rule applies to every line this release touches)
    swap(', Mega Evolution for the starters,', ',')
    swap('; Psyduck and Eevee can **Mega Evolve**;', ';')
    swap('The newest release (**BETA 0.1.6.9, prototype 0169**) is for testing. **It is NOT a complete game.**',
         f'The newest release (**{LABEL}, prototype 0200**) is for testing. **It is NOT a complete game.** *{DISCLAIMER}*')
    swap('the **first parts of the Johto postgame** are in,', '**more of the Johto postgame** is in,')
    swap('## Where it stands right now (BETA 0.1.6.9, prototype 0169)', f'## Where it stands right now ({LABEL}, prototype 0200)')
    readme = re.sub(r'- \*\*Played by the developer:\*\*[^\n]*', clean('README', "- **Played by the developer:** New Game through Lavender Town on earlier builds. Most of what is new in 0200 has only had small emulator tests on prepared saves; the Johto Gym Leaders' presence and level scaling and Morty's battle are confirmed on a real 3DS. Expect bugs, including softlocks."), readme, count=1)
    new_line = '- **New in 0200:** ' + ' '.join(re.sub(r'\*\*', '', x) for x in NEW_IN_0200[1:]) + '\n'
    swap('- **New in 0169:**', new_line + '- **New in 0169:**')
    swap('[hosted BETA 0.1.6.9 patching page](https://raw.githack.com/Doctor-Pokemon/Psyduck-Yellow-Releases/main/prototype-0169/index.html)', f'[hosted {LABEL} patching page]({PAGE})')
    entry = (f'- **{LABEL} (prototype 0200) — {DATE} (beta, testing only).** {DISCLAIMER} More of the Johto postgame, HMs from the Kanto gyms, the Silph Co. Field Kit, bag descriptions, a second set of wild Pokémon after the first Hall of Fame, '
             'a Linking Cord that evolves every trade evolution, evolution items in the Pokémon League shop and a Form Trader for Alolan and Galarian forms. Kanto complete to the first Hall of Fame; Johto unfinished.\n')
    swap('## Release history (newest first)\n', '## Release history (newest first)\n' + entry)
    (rel / 'README.md').write_text(readme, encoding='utf-8')
    (rel.parent / 'RELEASE_BODY.md').write_text(clean('RELEASE_BODY', RELEASE_BODY.replace('{sha}', new_sha)), encoding='utf-8')
    (rel.parent / 'RELEASE_TITLE.txt').write_text(TITLE, encoding='utf-8')
    print(json.dumps({'output_sha256': new_sha, 'patch_sha256': patch_sha, 'patch_bytes': size_patch, 'out_name': OUT_NAME, 'title': TITLE}))


if __name__ == '__main__':
    main(*sys.argv[1:5])
