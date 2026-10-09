#!/usr/bin/env python3
"""Build a guided plan page: DIR/plan.json + assets/template.html -> DIR/plan.html."""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True  # keep the sibling skill's folder clean
sys.path.insert(0, os.path.join(HERE, '..', '..', 'guided-pr-review', 'scripts'))
try:
    from build_review import check_diagram, diagrams_of
    from fetch_pr import lang_for
except ImportError:
    sys.exit('✗ needs the guided-pr-review skill next to this one (diagram checks are shared)')

EXAMPLE_KINDS = {'compare', 'chat', 'stats', 'code'}
CITE = re.compile(r'^`?([\w./-]+\.\w+):(\d+)')


def git(root, *args):
    if not os.path.exists(os.path.join(root, '.git')):
        return ''
    try:
        return subprocess.run(['git', '-C', root, *args], capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ''


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else '.'
    P = json.load(open(os.path.join(d, 'plan.json'), encoding='utf-8'))
    errors, warns = [], []
    for k in ('name', 'title', 'repo', 'chapters'):
        if not P.get(k):
            errors.append(f'plan.json needs "{k}"')
    root = os.path.expanduser(P.get('root') or os.getcwd())

    ctx, lines = [], {}
    for p in P.get('context_files', []):
        fp = os.path.join(root, p)
        if not os.path.isfile(fp):
            errors.append(f'context file not found: {fp}')
            continue
        text = open(fp, encoding='utf-8', errors='replace').read()
        ctx.append({'path': p, 'lang': lang_for(p), 'text': text})
        lines[p] = len(text.splitlines())

    def cite_ok(path, line, where, strict):
        bad = (errors if strict else warns).append
        if path not in lines:
            bad(f'{where}: {path} is not in context_files, so its link will not open')
        elif line and not str(line).isdigit():
            bad(f'{where}: line {line!r} must be a single line number')
        elif line and not 1 <= int(line) <= lines[path]:
            bad(f'{where}: {path}:{line} is past the end of the file ({lines[path]} lines)')

    chs = P.get('chapters', [])
    ids = []
    for i, c in enumerate(chs, 1):
        c['files'] = []
        for j, dg in enumerate(diagrams_of(c), 1):
            check_diagram(dg, f'chapter {i} diagram {j}', len(chs), errors, warns)
        for ex in c.get('examples', []):
            if ex.get('kind') not in EXAMPLE_KINDS:
                errors.append(f"chapter {i}: example kind must be one of {sorted(EXAMPLE_KINDS)}, got {ex.get('kind')!r}")
            elif ex['kind'] == 'code' and not ex.get('text'):
                errors.append(f'chapter {i}: a code example needs "text"')
        for dec in c.get('decisions', []):
            ids.append(dec.get('id'))
            if not dec.get('q') or any(not (o.get('value') and o.get('label')) for o in dec.get('options', [])):
                errors.append(f"chapter {i}: decision {dec.get('id')} needs \"q\", and every option needs \"value\" and \"label\"")
            if len(dec.get('options', [])) < 2:
                errors.append(f"chapter {i}: decision {dec.get('id')} needs at least two options")
            elif sum(bool(o.get('rec')) for o in dec['options']) != 1:
                errors.append(f"chapter {i}: decision {dec.get('id')} needs exactly one option with \"rec\": true")
        for w in c.get('watch', []):
            if w.get('path'):
                cite_ok(w['path'], w.get('line'), f'chapter {i} watch', True)
        for t in c.get('touches', []):
            m = CITE.match(t)
            if m:
                cite_ok(m[1], m[2], f'chapter {i} touches', False)
    if len(ids) != len(set(ids)):
        errors.append('decision ids must be unique across the plan')
    if P.get('flow'):
        check_diagram({**P['flow'], 'kind': 'flow'}, 'flow', len(chs), errors, warns)
    for j, dg in enumerate(P.get('diagrams', []), 1):
        check_diagram(dg, f'overview diagram {j}', len(chs), errors, warns)

    for w in warns:
        print('  !', w)
    if errors:
        for e in errors:
            print('  ✗', e)
        sys.exit(1)

    ticket = P.get('ticket') or {}
    pr = {
        'repo': P['repo'], 'number': ticket.get('id') or os.path.basename(os.path.abspath(d)), 'title': P['title'], 'url': ticket.get('url'),
        'author': P.get('author') or os.environ.get('USER', ''), 'body': '',
        'base': P.get('ref') or git(root, 'rev-parse', '--abbrev-ref', 'HEAD') or 'working tree',
        'headSha': P.get('sha') or git(root, 'rev-parse', 'HEAD'), 'head': 'plan',
        'additions': 0, 'deletions': 0, 'files': [], 'imports': [], 'commits': [], 'poster': None,
    }
    guide = {k: P[k] for k in ('name', 'overview', 'flow', 'diagrams', 'chapters', 'verdict', 'scope', 'ask') if k in P}
    blob = json.dumps({'pr': pr, 'guide': guide, 'context': ctx}, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    html = open(os.path.join(HERE, '..', 'assets', 'template.html'), encoding='utf-8').read()
    title = P['name'].replace('<', '').replace('&', 'and')
    html = html.replace('__TITLE__', title, 1).replace('__REVIEW_DATA__', blob, 1)
    out = os.path.join(d, 'plan.html')
    open(out, 'w', encoding='utf-8').write(html)
    print(f'wrote {out}  {len(html) / 1e6:.2f} MB  {len(chs)} chapters  {len(ids)} decisions  {len(ctx)} context files')


if __name__ == '__main__':
    main()
