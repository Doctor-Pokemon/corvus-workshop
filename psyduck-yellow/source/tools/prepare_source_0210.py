"""Prepare the public SOURCE branch publish-0210 for BETA 0.2.1.0 (owner order 2026-11-11, same method as publish-0200: the sources minus .nds/.sav/.dsv and the development documents, Doctor-Pokemon account only).
Works in a scratch clone of Doctor-Pokemon/corvus-workshop (branch publish-0200 checked out as publish-0210); nothing is pushed here. The tools of the local-only stone work (stone_check.py, stone_shop.py) are NOT published, and the sentences that describe that work are scrubbed from every .md (it is not in this build).
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
WITHHELD = re.compile(r'mega|psyduckite|eonite|novareonite|typhlosionite|feraligite|meganiumite|charizardite|raichunite|stellareonite|stone[ _-]?check|stone[ _-]?shop|starter stones?|classic ribbon|cherish ball|origin game 254', re.I)
HOLD_AT_PREVIOUS = ('CHECKPOINT.md', 'CAMPAIGN-FIRST-PLAN.md', 'JOHTO-POSTGAME-PLAN.md', 'PROTOTYPE-0030-PLAN.md')
NOT_PUBLIC = {'prepare_source_0210.py'}      # local-only tools of unreleased work
PRIVATE = re.compile(r"wife|personal icon|personal-icon|cartoon|@gmail|ghp_|github_pat_|Bearer |Authorization:|x-access-token", re.I)
TUNNEL = re.compile(r'https?://[A-Za-z0-9.-]*trycloudflare\.com\S*')
USER_PATH = re.compile(r'(?i)((?:[A-Z]:|/mnt/[a-z])[\\/]+Users[\\/]+)thata\b')
LABEL = 'BETA 0.2.1.0'
PAGE = 'https://raw.githack.com/Doctor-Pokemon/Psyduck-Yellow-Releases/main/prototype-0210/index.html'
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
    run('git', '-C', str(src), 'checkout', '-q', '-b', 'publish-0210')
    for key in ('user.name', 'user.email'):
        value = subprocess.run(['git', '-C', str(main_repo), 'config', key], capture_output=True, text=True).stdout.strip()
        run('git', '-C', str(src), 'config', key, value)
    dest = src / 'psyduck-yellow' / 'source'
    with tempfile.TemporaryDirectory() as tmp:
        archive = subprocess.run(['git', '-C', str(main_repo), 'archive', 'campaign-loop', 'yellow-heartgold'], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', tmp], input=archive, check=True)
        copied = 0
        for f in (Path(tmp) / 'yellow-heartgold').rglob('*'):
            if f.is_file() and not ROM_FILE.search(f.name) and f.name not in NOT_PUBLIC:
                target = dest / f.relative_to(Path(tmp) / 'yellow-heartgold')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, target)
                copied += 1
    for n in ('0027', '0030', '0032'):
        run('git', '-C', str(src), 'checkout', 'HEAD', '--', f'psyduck-yellow/source/PROTOTYPE-{n}-PLAN.md')
    shutil.copyfile(main_repo / 'JOHTO-POSTGAME-PLAN.md', dest / 'JOHTO-POSTGAME-PLAN.md')
    for name in HOLD_AT_PREVIOUS:                                       # development documents that also describe local-only work: keep the BETA 0.2.0.0 snapshot
        run('git', '-C', str(src), 'checkout', 'HEAD', '--', f'psyduck-yellow/source/{name}')
    total = 0
    for md in dest.rglob('*.md'):
        if md.name in HOLD_AT_PREVIOUS:
            continue
        text = md.read_text(encoding='utf-8', errors='replace')
        new, dropped = scrub_text(text)
        total += dropped
        if new != text:
            md.write_text(new, encoding='utf-8')
    # README files and the development log
    root = (src / 'README.md').read_text(encoding='utf-8')
    old_label, old_page = 'BETA 0.2.0.0 (prototype 0200)', 'prototype-0200/index.html'
    root = root.replace(old_label, f'{LABEL} (prototype 0210)').replace(old_page, 'prototype-0210/index.html').replace('Patching page for BETA 0.2.0.0', f'Patching page for {LABEL}')
    assert 'prototype 0210' in root and 'prototype-0210' in root and '0.2.0.0' not in root, 'root README labels not updated'
    (src / 'README.md').write_text(root, encoding='utf-8')
    py = (src / 'psyduck-yellow' / 'README.md').read_text(encoding='utf-8')
    py = py.replace(old_label, f'{LABEL} (prototype 0210)').replace(old_page, 'prototype-0210/index.html').replace('[BETA 0.2.0.0 patching page]', f'[{LABEL} patching page]').replace('Pokemon Psyduck Yellow 0-2-0-0.nds', 'Pokemon Psyduck Yellow 0-2-1-0.nds')
    assert 'prototype 0210' in py and 'prototype-0210' in py and '0-2-1-0' in py and '0.2.0.0' not in py, 'psyduck-yellow README labels not updated'
    (src / 'psyduck-yellow' / 'README.md').write_text(py, encoding='utf-8')
    sys.path.insert(0, str(Path(__file__).parent))
    import build_release_0210 as release
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
