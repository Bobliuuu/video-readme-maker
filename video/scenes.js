/* Scene library. Every scene is a pure function of local time t (seconds): draw(t, d, p, D) -> html. */
const D = window.__DATA, $ = s => document.querySelector(s);
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const ease = x => { x = clamp(x); return 1 - Math.pow(1 - x, 3) };
const prog = (t, t0, dur = .6) => ease((t - t0) / dur);
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const fmtN = (n, v) => (n.pre || '') + v.toLocaleString('en-US', { minimumFractionDigits: n.dec, maximumFractionDigits: n.dec }) + (n.unit || '');
const count = (n, k) => fmtN(n, n.v * clamp(k));
const spread = (i, n, d) => .5 + (d - 1.6) * (n <= 1 ? 0 : i / n) * .85; // reveal start for item i of n

function bullets(t, d, p) {
  const b = p.bullets || [];
  return `<div class="h2 grad" style="opacity:${prog(t, .1)}">${esc(p.heading || '')}</div>` + b.map((x, i) => {
    const k = prog(t, spread(i, b.length, d));
    return `<div class="bul" style="opacity:${k};transform:translateX(${(1 - k) * 40}px)"><i style="background:${p.color || 'var(--a)'}"></i><div>${esc(x)}</div></div>`
  }).join('');
}

const S = {
  title(t, d, p) {
    return `<div style="height:100%;display:flex;flex-direction:column;justify-content:center">
    <div class="h1 grad" style="opacity:${prog(t, .15, .9)};transform:translateY(${(1 - prog(t, .15, .9)) * 30}px)">${esc(p.title)}</div>
    <div class="sub" style="margin:26px 0 44px;opacity:${prog(t, .6)}">${esc(p.subtitle || '')}</div>
    <div>${(p.chips || []).map((c, i) => `<span class="chip mono" style="opacity:${prog(t, 1 + i * .25)}">${esc(c)}</span>`).join('')}</div></div>`
  },
  problem: bullets, idea: bullets, caveats: (t, d, p) => bullets(t, d, { color: 'var(--c)', ...p }),
  stat(t, d, p) {
    const k = prog(t, .3, Math.min(2.2, d * .5));
    return `<div style="height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center">
    <div class="sub" style="opacity:${prog(t, .1)};margin-bottom:10px">${esc(p.kicker || '')}</div>
    <div class="grad mono" style="font-size:260px;font-weight:800;line-height:1">${count(p.number, k)}</div>
    <div style="font-size:56px;font-weight:700;margin-top:18px;opacity:${prog(t, 1)}">${esc(p.label)}</div>
    <div class="sub" style="margin-top:14px;opacity:${prog(t, 1.3)}">${esc(p.sub || '')}</div></div>`
  },
  comparison(t, d, p) {
    const side = (s, i, col) => {
      const k = prog(t, .3 + i * .5, 1.6);
      return `<div class="card" style="flex:1;padding:48px;text-align:center;opacity:${prog(t, .2 + i * .4)};border-color:${col}">
      <div style="font-size:40px;color:var(--muted)">${esc(s.label)}</div>
      <div class="mono" style="font-size:130px;font-weight:800;color:${col};margin:24px 0">${count(s.number, k)}</div>
      <div class="sub" style="font-size:30px">${esc(s.sub || '')}</div></div>`
    };
    const r = p.ratio ? `<div class="mono grad" style="font-size:84px;font-weight:800;opacity:${prog(t, 1.4)};transform:scale(${.8 + .2 * prog(t, 1.4)})">${count(p.ratio, prog(t, 1.4, 1.2))}</div>` : '';
    return `<div class="h2 grad" style="opacity:${prog(t, .05)}">${esc(p.heading || '')}</div>
    <div style="display:flex;gap:36px;align-items:center">${side(p.left, 0, 'var(--muted)')}${r}${side(p.right, 1, 'var(--a)')}</div>
    <div class="sub" style="text-align:center;margin-top:30px;opacity:${prog(t, 2)}">${esc(p.sub || '')}</div>`
  },
  results(t, d, p) {
    const it = p.items;
    return `<div class="h2 grad" style="opacity:${prog(t, .05)}">${esc(p.heading || 'Results')}</div>
    <div style="display:grid;grid-template-columns:repeat(${Math.min(3, it.length)},1fr);gap:30px">` + it.map((x, i) => {
      const s = spread(i, it.length, d) * .7;
      return `<div class="card" style="padding:40px;opacity:${prog(t, s)};transform:translateY(${(1 - prog(t, s)) * 30}px)">
      <div class="mono" style="font-size:86px;font-weight:800;color:var(--a)">${count(x.number, prog(t, s + .2, 1.3))}</div>
      <div style="font-size:32px;color:var(--muted);margin-top:10px">${esc(x.label)}</div></div>`
    }).join('') + `</div>`
  },
  table(t, d, p) {
    const m = p.table;
    const rows = m.rows.map((r, i) => {
      const k = prog(t, spread(i, m.rows.length, d) * .8 + .3);
      return `<tr class="${m.highlight === i ? 'hl' : ''}" style="opacity:${k}">` + r.map((c, j) => `<td style="text-align:${m.align[j]}">${esc(c)}</td>`).join('') + `</tr>`
    }).join('');
    return `<div class="h2 grad" style="opacity:${prog(t, .05)}">${esc(p.heading || m.title)}</div><div class="card" style="padding:14px 20px"><table><tr>${m.head.map((h, j) => `<th style="text-align:${m.align[j]}">${esc(h)}</th>`).join('')}</tr>${rows}</table></div>
    <div class="sub mono" style="font-size:22px;margin-top:18px;opacity:${prog(t, 1)}">${m.source ? 'source: ' + esc(m.source) : ''}</div>`
  },
  chart(t, d, p) {
    const m = p.chart, W = 1680; let H = 700; if (m.type === 'bar') H = Math.min(110, 640 / m.bars.length) * m.bars.length + 60;
    let svg = '';
    const k = prog(t, .4, Math.min(3, d * .6));
    if (m.type === 'bar') {
      const bars = m.bars, vmax = Math.max(...bars.map(b => b.value)), lw = 430, rh = Math.min(110, 640 / bars.length);
      svg = bars.map((b, i) => {
        const kk = prog(t, .4 + i * .45, 1.6), y = 30 + i * rh, w = Math.max(6, (W - lw - 330) * b.value / vmax * kk);
        return `<text x="${lw - 24}" y="${y + rh * .5}" text-anchor="end" font-size="34" fill="${b.hl ? '#e6edf6' : '#8a98ad'}" font-weight="${b.hl ? 800 : 500}" opacity="${kk}">${esc(b.label)}</text>
        <rect x="${lw}" y="${y}" width="${w}" height="${rh * .66}" rx="10" fill="${b.hl ? 'var(--a)' : '#2b3750'}"/>
        <text x="${lw + w + 18}" y="${y + rh * .45}" font-size="34" font-weight="800" class="mono" fill="#e6edf6" opacity="${kk}">${fmtN(b, b.value * kk)}</text>`
      }).join('');
    } else {
      const pts = m.type === 'line' ? m.series.flatMap(s => s.pts) : m.pts.map(q => [q.x, q.y]);
      const x0 = Math.min(...pts.map(q => q[0])), x1 = Math.max(...pts.map(q => q[0])), y1 = Math.max(...pts.map(q => q[1])) * 1.08;
      const L = 110, R = W - 80, T = 20, B = H - 90, X = x => L + (R - L) * (x - x0) / ((x1 - x0) || 1), Y = y => B - (B - T) * y / y1;
      svg = [0, 1, 2, 3, 4].map(i => `<line x1="${L}" x2="${R}" y1="${B - (B - T) * i / 4}" y2="${B - (B - T) * i / 4}" stroke="#263044"/><text x="${L - 14}" y="${B - (B - T) * i / 4 + 8}" text-anchor="end" font-size="22" fill="#8a98ad" class="mono">${(y1 * i / 4).toPrecision(3)}</text>`).join('') +
        `<text x="${(L + R) / 2}" y="${H - 28}" text-anchor="middle" font-size="26" fill="#8a98ad">${esc(m.xlabel)}</text><text x="30" y="${(T + B) / 2}" transform="rotate(-90 30 ${(T + B) / 2})" text-anchor="middle" font-size="26" fill="#8a98ad">${esc(m.ylabel)}</text>`;
      if (m.type === 'line') {
        const pal = ['var(--a)', 'var(--b)', 'var(--c)', 'var(--good)'];
        m.series.forEach((s, si) => {
          const n = s.pts.length, d_ = s.pts.map((q, i) => `${i ? 'L' : 'M'}${X(q[0]).toFixed(1)},${Y(q[1]).toFixed(1)}`).join(' ');
          svg += `<path d="${d_}" pathLength="1" fill="none" stroke="${pal[si % 4]}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1" stroke-dashoffset="${1 - prog(t, .5 + si * .6, 2.4)}"/>` +
            s.pts.map((q, i) => `<circle cx="${X(q[0])}" cy="${Y(q[1])}" r="9" fill="${pal[si % 4]}" opacity="${prog(t, .5 + si * .6 + 2.4 * i / n, .3)}"/>`).join('') +
            (s.name ? `<text x="${X(s.pts[n - 1][0]) - 14}" y="${Y(s.pts[n - 1][1]) - 20}" text-anchor="end" font-size="30" font-weight="800" fill="${pal[si % 4]}" opacity="${prog(t, 3)}">${esc(s.name)}</text>` : '');
        });
        svg += [x0, x1].map(x => `<text x="${X(x)}" y="${B + 36}" text-anchor="middle" font-size="22" fill="#8a98ad" class="mono">${x.toLocaleString('en-US')}</text>`).join('');
      } else {
        svg += m.pts.map((q, i) => { const kk = prog(t, .5 + i * .4, .5); return `<circle cx="${X(q.x)}" cy="${Y(q.y)}" r="${(q.hl ? 18 : 13) * kk}" fill="${q.hl ? 'var(--a)' : 'var(--c)'}"/><text x="${X(q.x) + 26}" y="${Y(q.y) + 9}" font-size="28" fill="#e6edf6" opacity="${kk}">${esc(q.label)}</text>` }).join('');
      }
    }
    return `<div class="h2 grad" style="opacity:${prog(t, .05)}">${esc(p.heading || m.title)}</div><div class="sub" style="font-size:28px;margin:-18px 0 8px;opacity:${prog(t, .2)}">${esc(m.subtitle || '')}</div>
    <svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" style="overflow:visible">${svg}</svg>`
  },
  architecture(t, d, p) {
    const m = p.diagram, sc = Math.min(1680 / m.w, 700 / m.h), n = m.nodes.length, col = { box: 'var(--a)', store: 'var(--c)', accent: 'var(--b)', io: 'var(--good)' };
    const order = {}; m.nodes.forEach((x, i) => order[x.id] = i);
    const wrap = (s, k) => { const out = []; let c = ''; s.split(' ').forEach(w => { if ((c + ' ' + w).length > k && c) { out.push(c); c = w } else c = (c + ' ' + w).trim() }); if (c) out.push(c); return out.slice(0, 2) };
    let g = m.edges.map(e => {
      const k = prog(t, spread(Math.max(order[e.from], order[e.to]), n, d) * .8 + .5, .7), pts = e.pts.map(q => q.join(',')).join(' ');
      const [a, b] = [e.pts[0], e.pts[e.pts.length - 1]];
      return `<polyline points="${pts}" pathLength="1" fill="none" stroke="#8a98ad" stroke-width="3" stroke-dasharray="1" stroke-dashoffset="${1 - k}"/>` +
        (k > .98 ? `<circle cx="${b[0]}" cy="${b[1]}" r="6" fill="#8a98ad"/>` : '') + (e.label ? `<text x="${(a[0] + b[0]) / 2}" y="${(a[1] + b[1]) / 2 - 10}" text-anchor="middle" font-size="16" class="mono" fill="#8a98ad" opacity="${k}">${esc(e.label)}</text>` : '')
    }).join('');
    g += m.nodes.map((x, i) => {
      const k = prog(t, spread(i, n, d) * .8, .5);
      return `<g opacity="${k}" transform="translate(0 ${(1 - k) * 14})"><rect x="${x.x}" y="${x.y}" width="${x.w}" height="${x.h}" rx="14" fill="#131a26" stroke="${col[x.kind] || col.box}" stroke-width="3"/>
      <text x="${x.x + x.w / 2}" y="${x.y + 40}" text-anchor="middle" font-size="22" font-weight="800" fill="#e6edf6">${esc(x.label)}</text>` +
        wrap(x.sub, 27).map((l, j) => `<text x="${x.x + x.w / 2}" y="${x.y + 66 + j * 20}" text-anchor="middle" font-size="15" class="mono" fill="#8a98ad">${esc(l)}</text>`).join('') + `</g>`
    }).join('');
    return `<div class="h2 grad" style="opacity:${prog(t, .05)}">${esc(p.heading || m.title)}</div><div style="display:flex;justify-content:center"><svg width="${m.w * sc}" height="${m.h * sc}" viewBox="0 0 ${m.w} ${m.h}">${g}</svg></div>`
  },
  code(t, d, p) {
    const lines = p.code.replace(/\n+$/, '').split('\n');
    const col = l => esc(l).replace(/(#.*$)/, '<span class="cm">$1</span>').replace(/(&quot;.*?&quot;|".*?"|'.*?')/g, '<span class="st">$1</span>').replace(/\b(def|return|import|from|for|in|if|else|class|const|let|function|await|async|fn|pub|use|while|as|with|print)\b/g, '<span class="kw">$1</span>');
    return `<div class="h2 grad" style="opacity:${prog(t, .05)}">${esc(p.heading || '')}</div><div class="card" style="padding:34px 44px"><pre class="mono">` +
      lines.map((l, i) => { const k = prog(t, .4 + i * (Math.min(d - 2, 6) / lines.length), .35); const hl = (p.highlight || []).includes(i + 1); return `<div style="opacity:${k};background:${hl ? 'rgba(39,200,232,.14)' : 'none'};margin:0 -20px;padding:0 20px;border-radius:8px">${col(l) || ' '}</div>` }).join('') + `</pre></div>`
  },
  terminal(t, d, p) {
    let tt = .5, out = '';
    for (const l of p.lines) {
      if (l.cmd !== undefined) { const n = l.cmd.length, dur = n / 38, k = clamp((t - tt) / dur), shown = l.cmd.slice(0, Math.floor(n * k)); if (t >= tt) out += `<div><span style="color:var(--good)">$</span> ${esc(shown)}${k < 1 ? '<span style="color:var(--a)">▍</span>' : ''}</div>`; tt += dur + .35 }
      else { if (t >= tt) out += `<div style="color:#b7c3d6;opacity:${prog(t, tt, .2)}">${esc(l.out)}</div>`; tt += .25 }
    }
    return `<div class="h2 grad" style="opacity:${prog(t, .05)}">${esc(p.heading || '')}</div><div class="card" style="overflow:hidden"><div style="background:#1b2435;padding:14px 22px;display:flex;gap:10px"><b style="width:16px;height:16px;border-radius:50%;background:#ff5f57"></b><b style="width:16px;height:16px;border-radius:50%;background:#febc2e"></b><b style="width:16px;height:16px;border-radius:50%;background:#28c840"></b></div>
    <pre class="mono" style="padding:30px 40px;min-height:520px;font-size:30px">${out}</pre></div>`
  },
  end(t, d, p) {
    return `<div style="height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center">
    <div class="h1 grad" style="opacity:${prog(t, .2, .9)}">${esc(p.title)}</div>
    <div class="sub" style="margin-top:30px;opacity:${prog(t, .8)}">${esc(p.subtitle || '')}</div>
    <div class="mono card" style="margin-top:50px;padding:20px 44px;font-size:40px;color:var(--a);opacity:${prog(t, 1.3)}">${esc(p.url || '')}</div></div>`
  }
};

let SC = [];
function build() {
  const th = D.meta.theme || {};
  for (const [k, v] of Object.entries({ bg: '--bg', panel: '--panel', line: '--line', text: '--text', muted: '--muted', accent: '--a', accent2: '--b', accent3: '--c', good: '--good' })) if (th[k]) document.documentElement.style.setProperty(v, th[k]);
  $('#hname').textContent = D.meta.name; let st = 0;
  SC = D.scenes.map(s => { const o = { ...s, start: st }; st += s.dur; o.el = document.createElement('div'); o.el.className = 'scene'; o.el.style.display = 'none'; $('#scenes').appendChild(o.el); return o });
  window.TOTAL = st;
}
function renderScene(id, t) {
  const i = SC.findIndex(s => s.id === id), s = SC[i];
  SC.forEach(x => x.el.style.display = x.id === id ? 'flex' : 'none');
  const d = s.dur, a = ease(t / .45), b = ease((d - t) / .45);
  s.el.style.opacity = Math.min(a, b); s.el.style.transform = `translateY(${(1 - a) * 24 - (1 - b) * 12}px)`;
  s.el.innerHTML = S[s.type](t, d, s, D);
  const cp = (s.caps || []).find(c => t >= c.t0 && t < c.t1);
  $('#cap').innerHTML = cp && D.meta.captions !== false ? `<span>${esc(cp.text)}</span>` : '';
  $('#hstep').textContent = `${String(i + 1).padStart(2, '0')} / ${String(SC.length).padStart(2, '0')}`;
  $('#bar').style.width = ((s.start + t) / window.TOTAL * 100) + '%';
}
window.renderScene = renderScene;
window.renderGlobal = g => { const s = SC.find(x => g >= x.start && g < x.start + x.dur) || SC[SC.length - 1]; renderScene(s.id, g - s.start) };
window.getInfo = () => ({ scenes: SC.map(s => ({ id: s.id, dur: s.dur, start: s.start })), total: window.TOTAL, fps: D.meta.fps });
build(); window.READY = true;
