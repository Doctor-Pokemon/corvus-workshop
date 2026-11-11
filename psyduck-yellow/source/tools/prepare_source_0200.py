"""Prepare the public SOURCE branch publish-0200 for BETA 0.2.0.0 (owner order 2026-11-11: publish the sources minus .nds/.sav/.dsv and the development documents, Doctor-Pokemon account only).
Works in a scratch clone of Doctor-Pokemon/corvus-workshop (branch publish-0169 checked out as publish-0200); nothing is pushed here.
 1. overlay `git archive campaign-loop yellow-heartgold` onto psyduck-yellow/source/ (committed state only; ROM/save/zip files are skipped);
 2. restore the three PROTOTYPE-00NN plans that hold tunnel links or a viewing token (0027, 0030, 0032) from the previous branch;
 3. add the root JOHTO-POSTGAME-PLAN.md next to the other plans (the development documents of the Johto work);
 4. scrub every .md under psyduck-yellow/source: sentences about the withheld Mega content (owner rule 2026-11-04), personal-icon sentences, tunnel links, tokens, the owner's e-mail and Windows user name;
 5. update the two README files and the development log for BETA 0.2.0.0; 6. run the safety gate and a secrets grep.
Usage: prepare_source_0200.py <scratch clone> <main repo>"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROM_FILE = re.compile(r'\.(?:nds|gbc|gb|gba|3ds|cia|sav|dsv|srm|zip)$', re.I)
WITHHELD = re.compile(r'mega|psyduckite|eonite|novareonite|typhlosionite|feraligite|meganiumite|charizardite', re.I)
PRIVATE = re.compile(r"wife|personal icon|personal-icon|cartoon|@gmail|ghp_|github_pat_|Bearer |Authorization:|x-access-token", re.I)
TUNNEL = re.compile(r'https?://[A-Za-z0-9.-]*trycloudflare\.com\S*')
USER_PATH = re.compile(r'(?i)((?:[A-Z]:|/mnt/[a-z])[\\/]+Users[\\/]+)thata\b')
LABEL = 'BETA 0.2.0.0'
PAGE = 'https://raw.githack.com/Doctor-Pokemon/Psyduck-Yellow-Releases/main/prototype-0200/index.html'
DISCLAIMER = 'All features may not be in final version.'


def run(*cmd, cwd=None, **kw):
    return subprocess.run(cmd, cwd=cwd, check=True, **kw)


def scrub_text(text):
    out, dropped = [], 0
    for line in text.split('\n'):
        line = TUNNEL.sub('<tunnel link removed>', USER_PATH.sub(r'\1<user>', line))
        if not (WITHHELD.search(line) or PRIVATE.search(line)):
            out.append(line)
            continue
        if line.lstrip().startswith(('|', '```')):                      # table rows and fences: drop the whole line
            dropped += 1
            continue
        parts = re.split(r'(?<=[.!?])\s+', line)
        kept = [p for p in parts if not (WITHHELD.search(p) or PRIVATE.search(p))]
        dropped += len(parts) - len(kept)
        if kept:
            out.append(' '.join(kept))
    return '\n'.join(out), dropped


def main(scratch, main_repo):
    src, main_repo = Path(scratch), Path(main_repo)
    run('git', '-C', str(src), 'checkout', '-q', '-b', 'publish-0200')
    for key in ('user.name', 'user.email'):
        value = subprocess.run(['git', '-C', str(main_repo), 'config', key], capture_output=True, text=True).stdout.strip()
        run('git', '-C', str(src), 'config', key, value)
    dest = src / 'psyduck-yellow' / 'source'
    with tempfile.TemporaryDirectory() as tmp:
        archive = subprocess.run(['git', '-C', str(main_repo), 'archive', 'campaign-loop', 'yellow-heartgold'], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', tmp], input=archive, check=True)
        copied = 0
        for f in (Path(tmp) / 'yellow-heartgold').rglob('*'):
            if f.is_file() and not ROM_FILE.search(f.name):
                target = dest / f.relative_to(Path(tmp) / 'yellow-heartgold')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, target)
                copied += 1
    for n in ('0027', '0030', '0032'):
        run('git', '-C', str(src), 'checkout', 'HEAD', '--', f'psyduck-yellow/source/PROTOTYPE-{n}-PLAN.md')
    shutil.copyfile(main_repo / 'JOHTO-POSTGAME-PLAN.md', dest / 'JOHTO-POSTGAME-PLAN.md')
    total = 0
    for md in dest.rglob('*.md'):
        text = md.read_text(encoding='utf-8', errors='replace')
        new, dropped = scrub_text(text)
        total += dropped
        if new != text:
            md.write_text(new, encoding='utf-8')
    # README files and the development log
    root = (src / 'README.md').read_text(encoding='utf-8')
    root = root.replace('; Psyduck and Eevee can **Mega Evolve**;', ';')
    root = root.replace('**⚠️ Latest: BETA 0.1.6.9 (prototype 0169) — for testing only. It is not a complete game.** The Kanto campaign up to the first Hall of Fame is built, plus the first parts of the Johto postgame;',
                        f'**⚠️ Latest: {LABEL} (prototype 0200) — for testing only. It is not a complete game. {DISCLAIMER}** The Kanto campaign up to the first Hall of Fame is built, plus more of the Johto postgame;')
    root = root.replace('[Patching page for BETA 0.1.6.9 (builds the game in your browser)](https://raw.githack.com/Doctor-Pokemon/Psyduck-Yellow-Releases/main/prototype-0169/index.html)', f'[Patching page for {LABEL} (builds the game in your browser)]({PAGE})')
    assert 'prototype 0200' in root and 'prototype-0200' in root, 'root README labels not updated'
    (src / 'README.md').write_text(root, encoding='utf-8')
    py = (src / 'psyduck-yellow' / 'README.md').read_text(encoding='utf-8')
    py = py.replace('**Latest: BETA 0.1.6.9 (prototype 0169)** — for testing only; not a complete game. The Kanto campaign up to the first Hall of Fame plus the first parts of the Johto postgame;',
                    f'**Latest: {LABEL} (prototype 0200)** — for testing only; not a complete game. {DISCLAIMER} The Kanto campaign up to the first Hall of Fame plus more of the Johto postgame;')
    py = py.replace('[BETA 0.1.6.9 patching page](https://raw.githack.com/Doctor-Pokemon/Psyduck-Yellow-Releases/main/prototype-0169/index.html)', f'[{LABEL} patching page]({PAGE})')
    py = py.replace('Pokemon Psyduck Yellow 0-1-6-9.nds', 'Pokemon Psyduck Yellow 0-2-0-0.nds')
    assert 'prototype 0200' in py and 'prototype-0200' in py and '0-2-0-0' in py, 'psyduck-yellow README labels not updated'
    (src / 'psyduck-yellow' / 'README.md').write_text(py, encoding='utf-8')
    sys.path.insert(0, str(Path(__file__).parent))
    import build_release_0200 as release
    log = src / 'psyduck-yellow' / 'DEVELOPMENT-LOG.md'
    text = log.read_text(encoding='utf-8')
    text = re.sub(r'\*\*Last updated: [^*]*\.\*\*', f'**Last updated: {release.DATE}.**', text, count=1)
    log.write_text(text + release.clean('development log entry', release.LOG_ENTRY), encoding='utf-8')
    run('git', '-C', str(src), 'add', '-A')
    gate = subprocess.run([sys.executable, str(Path(__file__).parent / 'check_repo_safety.py'), '--root', str(src)], capture_output=True, text=True)
    assert gate.returncode == 0, gate.stdout + gate.stderr
    names = subprocess.run(['git', '-C', str(src), 'diff', '--cached', '--name-only'], capture_output=True, text=True, check=True).stdout.split('\n')
    bad = [n for n in names if ROM_FILE.search(n)]
    assert not bad, bad
    leaks = []
    for n in names:
        f = src / n
        if n and f.is_file() and f.suffix in ('.md', '.py', '.json', '.txt', '.html'):
            body = f.read_text(encoding='utf-8', errors='replace')
            for pat in ('ghp_', 'github_pat_', 'trycloudflare', 'x-access-token', '@gmail.com'):
                if pat in body:
                    leaks.append((n, pat))
    print({'files_copied': copied, 'sentences_or_lines_scrubbed': total, 'staged_files': len([n for n in names if n]), 'safety_gate': 'passed', 'leaks': leaks})


if __name__ == '__main__':
    main(*sys.argv[1:3])
