#!/usr/bin/env python3
"""Turn the guided-pr-review template into a guided *plan* template.

Keeps: tab bar, overview + animated before/after flow, chapter layout (sticky prose |
diagrams), diagram renderers, code viewer for context files, path:line links, Ask panel.
Drops: Diff tab, file diffs, GitHub review panel.
Adds: per-chapter "touches", examples (compare / chat / stats / code), decisions,
notes, and a Decisions tab with a "Copy response" button.
"""
import sys

src, out = sys.argv[1], sys.argv[2]
s = open(src).read()


def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n >= 1, f"not found: {old[:80]!r}"
    if count == 1:
        assert n == 1, f"{n} matches for: {old[:80]!r}"
    s = s.replace(old, new) if count == 0 else s.replace(old, new, count)


def rep_block(start, end, new):
    """Replace s[start:end) located by unique markers; end marker is kept."""
    global s
    a = s.index(start)
    assert s.count(start) == 1, f"start not unique: {start[:60]!r}"
    b = s.index(end, a)
    s = s[:a] + new + s[b:]


# ---------- markup ----------
rep('aria-label="Review views"', 'aria-label="Plan views"')
rep('data-tab="ov">Overview</button>', 'data-tab="ov">Decisions <span class="cnt" id="decCnt"></span></button>')
rep('data-tab="guide">Guide</button>', 'data-tab="guide">Plan</button>')
rep('      <button class="tab" role="tab" id="tab-diff" aria-controls="p-diff" aria-selected="false" data-tab="diff">Diff</button>\n', '')
rep('title="Chapters marked reviewed"', 'title="Chapters marked read"')
rep('<button class="rev-btn" id="revBtn"', '<button class="rev-btn" id="revBtn" hidden')
rep('<aside class="ask" id="ask" aria-label="Ask about this PR">', '<aside class="ask" id="ask" aria-label="Ask about this plan">')
rep('<b>Ask about this PR</b>', '<b>Ask about this plan</b>')
rep('placeholder="Ask about the code, a risk, or why something changed…"', 'placeholder="Ask about the plan, a risk, or the code it touches…"')

rep_block('  <section class="panel" id="p-ov"', '  <section class="panel" id="p-diff"', '''  <section class="panel" id="p-ov" role="tabpanel" aria-labelledby="tab-ov" hidden>
    <div class="ov-tab">
      <div style="display:grid;gap:16px;align-content:start">
        <div class="card"><h2 class="sec-h">Decisions</h2><p class="foot-n" style="margin:0 0 12px">The suggested option is what the plan assumes. Change any of them, add notes on the chapters, then copy your response back to Claude.</p><div id="decList"></div></div>
        <div class="card"><h2 class="sec-h">Your response</h2><div class="resp-acts"><button class="send" id="copyResp">Copy response</button><span class="foot-n" id="copyNote"></span></div><textarea id="respText" class="resp" readonly rows="10" aria-label="Your response"></textarea></div>
      </div>
      <div style="display:grid;gap:16px;align-content:start">
        <div class="card verdict" id="verdict"></div>
        <div class="card"><h2 class="sec-h">Not changing</h2><ul class="scope" id="scope"></ul></div>
      </div>
    </div>
  </section>

''')

# ---------- styles ----------
rep('</style>', '''
/* ---------- plan blocks ---------- */
.touches{display:grid;gap:4px;margin:12px 0 0;padding:0;list-style:none;font-size:12.5px;color:var(--fg-2)}
.touches li{display:flex;gap:6px;align-items:baseline}
.touches li::before{content:"↳";color:var(--muted);font-family:var(--mono)}
.ex{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 16px 14px;margin:0;min-width:0}
.ex-h{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}
.ex-h b{font-size:13px}
.ex-k{font:500 10.5px var(--mono);letter-spacing:.04em;text-transform:uppercase;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:1px 6px}
.ex-cap{color:var(--fg-2);font-size:12.5px;margin:0 0 10px;max-width:72ch}
.ex .dg-replay{margin-left:auto}
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media (max-width:760px){.cmp{grid-template-columns:1fr}}
.cmp-col{border:1px solid var(--line);border-radius:8px;overflow:hidden;min-width:0;background:var(--surface)}
.cmp-h{font-size:11.5px;font-weight:600;padding:6px 10px;border-bottom:1px solid var(--line);background:var(--surface-2);display:flex;gap:6px;align-items:center}
.cmp-h .pill{font:500 10px var(--mono);text-transform:uppercase;letter-spacing:.04em;border-radius:4px;padding:0 5px}
.cmp-col.before .pill{color:var(--del);background:var(--del-bg)} .cmp-col.after .pill{color:var(--add);background:var(--add-bg)}
.cmp-b{font:12px/1.55 var(--mono);padding:6px 0;overflow-x:auto}
.cmp-b div{padding:0 10px;white-space:pre;min-height:1.55em}
.cmp-b .add{background:var(--add-bg);color:var(--add)} .cmp-b .del{background:var(--del-bg);color:var(--del)} .cmp-b .now{font-weight:600;color:var(--fg)} .cmp-b .dim{color:var(--muted)}
.chat{display:grid;gap:8px;padding:4px 2px}
.chat .m{max-width:86%;padding:7px 11px;border-radius:12px;font-size:13px;line-height:1.45}
.chat .m.user{justify-self:end;background:var(--fg);color:var(--bg);border-bottom-right-radius:3px}
.chat .m.bot{background:var(--surface-2);border:1px solid var(--line);border-bottom-left-radius:3px}
.chat .m.bot.bad{border-color:var(--del-bg-2);background:var(--del-bg)}
.chat .m.bot.good{border-color:var(--add-bg-2);background:var(--add-bg)}
.chat .m.tool{font:12px var(--mono);color:var(--fg-2);background:transparent;border:1px dashed var(--line-2);border-radius:8px;padding:4px 9px}
.chat .m.note{justify-self:center;font-size:11.5px;color:var(--muted);background:none;padding:0}
.chat .tag{display:inline-block;margin-left:6px;font:500 10px var(--mono);text-transform:uppercase;letter-spacing:.03em;padding:0 5px;border-radius:4px;background:var(--surface);border:1px solid var(--line);color:var(--muted);vertical-align:1px}
.chat .m.bad .tag{color:var(--del);border-color:var(--del-bg-2)} .chat .m.good .tag{color:var(--add);border-color:var(--add-bg-2)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}
.stat{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:var(--surface)}
.stat .v{font-size:22px;font-weight:600;line-height:1.2;font-variant-numeric:tabular-nums}
.stat .l{font-size:12.5px;color:var(--fg)} .stat .s{font-size:11.5px;color:var(--muted)}
.stat.bad .v{color:var(--del)} .stat.good .v{color:var(--add)}
.excode{margin:0;font:12px/1.55 var(--mono);background:var(--surface-2);border:1px solid var(--line);border-radius:8px;padding:10px 12px;overflow-x:auto}
.anim > *{transition:opacity .35s ease, transform .35s ease}
.anim.hide > *{opacity:0;transform:translateY(4px)}
.dec{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:var(--surface);display:grid;gap:6px}
.dec + .dec{margin-top:10px}
.dec-q{font-size:13px;font-weight:600;display:flex;gap:8px;align-items:baseline}
.dec-q .n{font:500 10.5px var(--mono);color:var(--accent);background:var(--accent-bg);border-radius:4px;padding:0 5px;flex:none}
.dec-o{display:flex;gap:8px;align-items:flex-start;font-size:13px;padding:5px 8px;border-radius:7px;border:1px solid transparent;cursor:pointer}
.dec-o:hover{background:var(--surface-2)}
.dec-o input{margin-top:3px;accent-color:var(--accent)}
.dec-o.on{border-color:var(--accent);background:var(--accent-bg)}
.dec-o small{display:block;color:var(--muted);font-size:11.5px}
.dec-o .sug{font:500 10px var(--mono);text-transform:uppercase;color:var(--add);margin-left:6px}
.dec-why{font-size:12px;color:var(--fg-2);margin:0}
.dec-go{font-size:12px}
.note-box{width:100%;min-height:54px;font:13px/1.45 var(--ui);color:var(--fg);background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:7px 9px;resize:vertical}
.resp{width:100%;font:12px/1.5 var(--mono);color:var(--fg);background:var(--surface-2);border:1px solid var(--line);border-radius:8px;padding:10px;resize:vertical}
.resp-acts{display:flex;gap:10px;align-items:center;margin-bottom:10px}
.scope{margin:0;padding-left:18px;display:grid;gap:6px;color:var(--fg-2);font-size:13px}
.tier.problem{color:var(--del);border-color:var(--del-bg-2)} .tier.guard{color:var(--accent);border-color:var(--accent-bg)} .tier.rollout{border-style:dashed}
#decCnt:empty{display:none}
</style>''')

# ---------- JS: labels ----------
rep("const TIER_LABEL = { core: 'Core', supporting: 'Supporting', wiring: 'Wiring', data: 'Data', tests: 'Tests', generated: 'Generated', docs: 'Docs' };",
    "const TIER_LABEL = { core: 'Core', supporting: 'Supporting', wiring: 'Wiring', data: 'Data', tests: 'Tests', generated: 'Generated', docs: 'Docs', problem: 'Problem', guard: 'Guard', rollout: 'Rollout' };")
rep("$('#progTxt').textContent = `${d} / ${n} reviewed`;", "$('#progTxt').textContent = `${d} / ${n} read`;")
rep("'Ask anything about this PR. Claude reads the diffs, opens whole files and searches the code before it answers. File references in answers jump to the line.'",
    "'Ask anything about this plan. Claude reads the code it touches before it answers. File references in answers open the code at that line.'")
rep("why the PR needs ${", "why the plan touches ${")

# ---------- JS: header ----------
rep_block('function renderHead() {', '/* ---------- overview (guide top) ---------- */', '''function renderHead() {
  $('#prTitle').textContent = PR.title;
  $('#barId').textContent = `${PR.repo.split('/').pop()} · ${PR.number}`;
  const nDec = CHAPTERS.reduce((a, c) => a + (c.decisions || []).length, 0);
  $('#prMeta').append(...[
    h('span', { class: 'who' }, h('span', { class: 'av' }, (PR.author || '?')[0]), PR.author),
    h('span', { class: 'tier' }, 'Plan · not built'),
    h('span', {}, `${CHAPTERS.length} chapters`),
    nDec ? h('span', {}, `${nDec} decisions`) : null,
    h('span', { class: 'br', title: `code cited from ${PR.base} @ ${String(PR.headSha).slice(0, 8)}` }, `${PR.base} @ ${String(PR.headSha).slice(0, 8)}`),
    PR.url ? h('a', { href: PR.url, target: '_blank', rel: 'noopener' }, `${PR.number} ↗`) : null,
  ].filter(Boolean));
}

''')

# ---------- JS: chapters ----------
rep_block('function renderChapters() {', 'let CUR_CH = null;', r'''const DEC = Object.assign({}, store.get('dec', {}));
const NOTES = Object.assign({}, store.get('notes', {}));
const ALL_DECS = [];
CHAPTERS.forEach((c, i) => (c.decisions || []).forEach(d => ALL_DECS.push({ ...d, ch: i })));
const decRec = d => (d.options.find(o => o.rec) || d.options[0]).value;
const decVal = d => DEC[d.id] ?? decRec(d);
function renderDecision(d, n, where = 'ch') {
  const box = h('div', { class: 'dec', 'data-dec': d.id });
  box.append(h('div', { class: 'dec-q' }, h('span', { class: 'n' }, `D${n}`), h('span', { html: inline(d.q) })));
  if (d.why) box.append(withCites(h('p', { class: 'dec-why', html: inline(d.why) })));
  d.options.forEach(o => {
    const id = `dec-${where}-${d.id}-${o.value}`;
    const inp = h('input', { type: 'radio', name: `dec-${where}-${d.id}`, id, value: o.value });
    const lab = h('label', { class: 'dec-o', for: id }, inp, h('span', {}, h('span', { html: inline(o.label) }), o.rec ? h('span', { class: 'sug' }, 'suggested') : null, o.note ? h('small', { html: inline(o.note) }) : null));
    inp.addEventListener('change', () => { DEC[d.id] = o.value; store.set('dec', DEC); syncDecisions(); });
    box.append(lab);
  });
  return box;
}
function syncDecisions() {
  ALL_DECS.forEach(d => {
    const v = decVal(d);
    $$(`.dec[data-dec="${CSS.escape(d.id)}"]`).forEach(box => $$('.dec-o', box).forEach(l => {
      const inp = l.querySelector('input'); inp.checked = inp.value === v; l.classList.toggle('on', inp.checked);
    }));
  });
  const changed = ALL_DECS.filter(d => decVal(d) !== decRec(d)).length;
  $('#decCnt').textContent = changed ? `${changed} changed` : '';
  buildResponse();
}
const chatSpeed = 380;
function animate(el) {
  if (REDUCED || !PLAY_IO) return null;
  el.classList.add('anim');
  el._play = () => {
    const kids = [...el.children];
    el.classList.add('hide');
    kids.forEach(k => { k.style.transitionDelay = '0ms'; });
    void el.offsetWidth;
    el.classList.remove('hide');
    kids.forEach((k, j) => { k.style.transitionDelay = `${j * chatSpeed}ms`; });
  };
  PLAY_IO.observe(el);
  return h('button', { class: 'dg-replay', type: 'button', title: 'Play the animation again', onclick: () => el._play() }, 'Replay');
}
function cmpCol(side, col) {
  const lines = (col.lines || []).map(t => {
    let cls = '', txt = t;
    if (t.startsWith('+')) { cls = 'add'; txt = ' ' + t.slice(1); }
    else if (t.startsWith('-')) { cls = 'del'; txt = ' ' + t.slice(1); }
    else if (t.startsWith('>')) { cls = 'now'; txt = ' ' + t.slice(1); }
    else if (t.startsWith('#')) { cls = 'dim'; txt = ' ' + t.slice(1); }
    else txt = ' ' + t;
    return h('div', { class: cls }, txt);
  });
  return h('div', { class: `cmp-col ${side}` }, h('div', { class: 'cmp-h' }, h('span', { class: 'pill' }, side === 'before' ? 'today' : 'after'), col.label || ''), h('div', { class: 'cmp-b' }, lines));
}
function renderExample(ex) {
  const head = h('div', { class: 'ex-h' }, h('span', { class: 'ex-k' }, ex.kind === 'compare' ? 'before / after' : ex.kind === 'chat' ? 'example' : ex.kind === 'stats' ? 'numbers' : 'example'), h('b', { html: inline(ex.title || '') }));
  const fig = h('figure', { class: 'ex' }, head, ex.caption ? withCites(h('p', { class: 'ex-cap', html: inline(ex.caption) })) : null);
  if (ex.kind === 'compare') {
    const body = h('div', { class: 'cmp' }, cmpCol('before', ex.before || {}), cmpCol('after', ex.after || {}));
    fig.append(body);
  } else if (ex.kind === 'chat') {
    const body = h('div', { class: 'chat' }, (ex.turns || []).map(t => h('div', { class: `m ${t.who}${t.tone ? ' ' + t.tone : ''}` }, h('span', { html: inline(t.text) }), t.tag ? h('span', { class: 'tag' }, t.tag) : null)));
    fig.append(body);
    const rb = animate(body); if (rb) head.append(rb);
  } else if (ex.kind === 'stats') {
    const body = h('div', { class: 'stats' }, (ex.items || []).map(it => h('div', { class: `stat${it.tone ? ' ' + it.tone : ''}` }, h('div', { class: 'v' }, it.v), h('div', { class: 'l', html: inline(it.l) }), it.s ? h('div', { class: 's', html: inline(it.s) }) : null)));
    fig.append(body);
    const rb = animate(body); if (rb) head.append(rb);
  } else if (ex.kind === 'code') {
    fig.append(h('pre', { class: 'excode' }, h('code', { html: hl(ex.text || '', ex.lang) })));
  }
  return fig;
}
function renderChapters() {
  const wrap = $('#chapters'), N = CHAPTERS.length;
  let decN = 0;
  CHAPTERS.forEach((c, i) => {
    const cb = h('input', { type: 'checkbox', id: `chk-${i}` });
    cb.checked = !!REV.ch[i];
    cb.addEventListener('change', () => { REV.ch[i] = cb.checked; saveRev(); updateProgress(); });
    const side = h('div', { class: 'ch-side' },
      h('h3', { class: 'ch-title' }, c.title),
      h('div', { class: 'ch-row' }, h('span', { class: 'n' }, `${pad2(i + 1)} / ${pad2(N)}`), h('label', { for: cb.id }, cb, 'Read'), c.tier ? h('span', { class: `tier ${c.tier}` }, TIER_LABEL[c.tier] || c.tier) : null),
      h('div', { class: 'prose' }, (c.explain || []).map(p => withCites(h('p', { html: inline(p) })))),
      c.touches?.length ? h('div', { class: 'blk-h' }, 'Touches') : null,
      c.touches?.length ? h('ul', { class: 'touches' }, c.touches.map(t => withCites(h('li', {}, h('span', { html: inline(t) }))))) : null,
    );
    if (c.watch?.length) {
      side.append(h('div', { class: 'blk-h' }, 'Risks and open questions'));
      side.append(h('div', { class: 'watch' }, c.watch.map((w, wi) => {
        const lv = ['risk', 'question', 'nit'].includes(w.level) ? w.level : 'risk';
        const acts = h('div', { class: 'wa' });
        if (w.path) acts.append(h('button', { onclick: () => goTo(w.path, w.line) }, w.line ? `${splitPath(w.path)[1]}:${w.line}` : splitPath(w.path)[1]));
        acts.append(h('button', { 'data-askflag': `${i}:${wi}` }, 'Ask'));
        return h('div', { class: 'w' }, h('span', { class: `lv lv-${lv}` }, lv), h('div', {}, withCites(h('div', { html: inline(w.text) })), acts));
      })));
    }
    side.append(h('div', { class: 'blk-h' }, 'Your note'));
    const nb = h('textarea', { class: 'note-box', id: `note-${i}`, placeholder: 'Anything to change in this chapter? It goes into your response.' });
    nb.value = NOTES[i] || '';
    nb.addEventListener('input', () => { NOTES[i] = nb.value; store.set('notes', NOTES); buildResponse(); });
    side.append(nb);
    const qs = (c.ask || []).slice(0, 4);
    side.append(h('div', { class: 'blk-h' }, 'Ask'));
    side.append(h('div', { class: 'chips' },
      qs.map(q => h('button', { class: 'chip', onclick: () => askNow(q, { kind: 'chapter', ch: i }) }, q)),
      h('button', { class: 'chip deep', onclick: () => askNow(`Walk me through chapter ${i + 1} ("${c.title}") in depth: what changes at runtime, which code it touches (read it), and what could break.`, { kind: 'chapter', ch: i }) }, 'Explain this chapter in depth')));
    const main = h('div', { class: 'ch-main' });
    const sec = h('section', { class: 'chapter', id: `ch-${i + 1}`, 'data-ch': i, 'aria-label': `Chapter ${i + 1}: ${c.title}` }, side, main);
    sec.addEventListener('mouseenter', () => markFlow(i));
    sec.addEventListener('mouseleave', () => markFlow(null));
    wrap.append(sec);
    if (c.diagrams?.length) {
      const dw = h('div', { class: 'dg-col' });
      main.append(dw);
      c.diagrams.forEach(d => mountDiagram(dw, d));
      if (!dw.children.length) dw.remove();
    }
    (c.examples || []).forEach(ex => main.append(renderExample(ex)));
    if (c.decisions?.length) {
      const dc = h('figure', { class: 'ex' }, h('div', { class: 'ex-h' }, h('span', { class: 'ex-k' }, 'decide'), h('b', {}, c.decisions.length > 1 ? 'Decisions for this chapter' : 'Decision for this chapter')));
      c.decisions.forEach(d => { decN += 1; d._n = decN; dc.append(renderDecision(d, decN)); });
      main.append(dc);
    }
  });
}
''')

# ---------- JS: decisions tab ----------
rep_block('function renderOverviewTab() {', '/* ---------- diff tab ---------- */', r'''function buildResponse() {
  const ta = $('#respText');
  if (!ta) return;
  let s = `# Re: ${PR.number} plan — ${PR.title}\n\n## Decisions\n`;
  ALL_DECS.forEach((d, k) => {
    const v = decVal(d), o = d.options.find(x => x.value === v) || d.options[0];
    const rec = d.options.find(x => x.rec) || d.options[0];
    s += `${k + 1}. [Ch ${d.ch + 1}] ${d.q.replace(/\*\*|`/g, '')}\n   → **${o.label.replace(/\*\*|`/g, '')}** \`${v}\`` + (v === rec.value ? (DEC[d.id] ? '  _(kept as suggested)_' : '  _(not changed; suggested kept)_') : `  ✎ (was: ${rec.label.replace(/\*\*|`/g, '')})`) + '\n';
  });
  const notes = CHAPTERS.map((c, i) => [i, (NOTES[i] || '').trim()]).filter(([, t]) => t);
  if (notes.length) {
    s += `\n## Notes\n`;
    notes.forEach(([i, t]) => { s += `- **Ch ${i + 1} · ${CHAPTERS[i].title}**\n${t.split('\n').map(l => '  > ' + l).join('\n')}\n`; });
  }
  const checks = (G.verdict?.checks || []).map((c, i) => [c, !!REV.checks[i]]);
  if (checks.some(([, on]) => on)) {
    s += `\n## Checks done\n`;
    checks.filter(([, on]) => on).forEach(([c]) => { s += `- [x] ${c.replace(/\*\*|`/g, '')}\n`; });
  }
  s += `\n_Lines starting with ">" are the reader's own words._\n`;
  ta.value = s;
}
function renderOverviewTab() {
  const v = G.verdict || {};
  const vd = $('#verdict');
  vd.append(h('h2', { class: 'sec-h' }, 'Before we build'));
  if (v.risk) vd.append(h('span', { class: `risk-pill risk-${v.risk}` }, `${v.risk} risk`));
  if (v.summary) vd.append(withCites(h('p', { class: 'prose', style: 'margin:0', html: inline(v.summary) })));
  if (v.checks?.length) {
    vd.append(h('ul', { class: 'checks' }, v.checks.map((c, i) => {
      const cb = h('input', { type: 'checkbox', id: `vchk-${i}` });
      cb.checked = !!REV.checks[i];
      cb.addEventListener('change', () => { REV.checks[i] = cb.checked; saveRev(); buildResponse(); });
      return h('li', {}, h('label', { for: cb.id }, cb, withCites(h('span', { html: inline(c) }))));
    })));
  }
  const sc = $('#scope');
  (G.scope || []).forEach(t => sc.append(withCites(h('li', { html: inline(t) }))));
  const dl = $('#decList');
  ALL_DECS.forEach(d => {
    const box = renderDecision(d, ALL_DECS.indexOf(d) + 1, 'tab');
    box.append(h('button', { class: 'chip dec-go', onclick: () => goChapter(d.ch) }, `Open chapter ${d.ch + 1}: ${CHAPTERS[d.ch].title}`));
    dl.append(box);
  });
  $('#copyResp').addEventListener('click', async () => {
    buildResponse();
    const ta = $('#respText');
    try { await navigator.clipboard.writeText(ta.value); $('#copyNote').textContent = 'Copied. Paste it to Claude.'; }
    catch { ta.focus(); ta.select(); $('#copyNote').textContent = 'Press ⌘C / Ctrl+C to copy the selected text.'; }
  });
  syncDecisions();
}

''')

# ---------- JS: Ask brief ----------
rep_block('function brief() {', 'function focusText(c) {', r'''function brief() {
  if (brief.v) return brief.v;
  const ov = G.overview || {};
  let s = `You are helping an engineer review an implementation PLAN for ${PR.repo} (${PR.number}): "${PR.title}". Nothing has been built yet. The plan is written against branch ${PR.base} at commit ${String(PR.headSha).slice(0, 8)}; the files the plan touches are attached as read-only context files with their current code.
The reader is on a guided plan page and asks you questions in place. Answer like a senior engineer on the team who wrote this plan and knows the code.

How to answer:
- Lead with the direct answer in one or two sentences, then the supporting detail.
- Ground claims about current behaviour in code you have read with read_file or search. Cite as path:line (current ${PR.base} line numbers); the page turns these into links that open the code.
- Be clear about what is current code and what is proposed by the plan. Never describe proposed code as if it exists.
- If something depends on code that is not attached, say so plainly and name what to check.
- Keep it tight: short paragraphs, bullets for lists, fenced code blocks with a language for sketches. No preamble, no closing summary.

Plan summary:
${[].concat(ov.summary || []).join('\n')}
${(ov.steps || []).map((x, i) => `${i + 1}. ${x}`).join('\n')}

Chapters:
`;
  CHAPTERS.forEach((c, i) => {
    s += `${i + 1}. ${c.title} [${c.tier || 'core'}]\n   ${(c.explain || []).join(' ').slice(0, 900)}\n`;
    (c.touches || []).forEach(t => { s += `   touches: ${t}\n`; });
    (c.watch || []).forEach(w => { s += `   ${w.level || 'risk'}: ${w.text}${w.path ? ` at ${w.path}${w.line ? ':' + w.line : ''}` : ''}\n`; });
    (c.decisions || []).forEach(d => { const v = decVal(d); const o = d.options.find(x => x.value === v); s += `   decision: ${d.q} -> currently "${o ? o.label : v}" (options: ${d.options.map(x => x.label + (x.rec ? ' [suggested]' : '')).join('; ')})\n`; });
    (c.examples || []).forEach(ex => { s += `   example (${ex.kind}): ${ex.title || ''}${ex.caption ? ' — ' + ex.caption : ''}\n`; });
  });
  if (G.scope?.length) s += `\nNot changing: ${G.scope.join(' | ')}\n`;
  if (G.verdict?.checks?.length) s += `\nChecks before building: ${G.verdict.checks.join(' | ')}\n`;
  if (CTX.length) s += `\nContext files you can read with read_file or search: ${CTX.map(c => c.path).join(', ')}\n`;
  if (!Ask.toolsOK) s += `\n(No tools in this view: answer from the plan text above.)\n`;
  return (brief.v = s);
}
''')

# focusText: chapter context = plan text, not a diff
rep("if (c.kind === 'chapter') s += `Diff for this chapter:\\n${chapterDiff(c.ch, Ask.toolsOK ? 45000 : 90000)}\\n`;",
    "if (c.kind === 'chapter') { const ch = CHAPTERS[c.ch]; s += `Plan text for this chapter:\\n${(ch.explain || []).join('\\n')}\\n${(ch.touches || []).map(t => 'touches: ' + t).join('\\n')}\\n`; }")

# boot: no GitHub review panel
rep('initSample();\ninitReview();', 'initSample();')

open(out, 'w').write(s)
print('ok', len(s))
