#!/usr/bin/env node
// Frame-by-frame renderer: headless Chrome (puppeteer-core) -> ffmpeg. One mp4 segment per scene, then concat (video only).
// node render.js --data out/data.json --out out [--scene id] [--stills 1,5] [--conc 4] [--chrome path]
const fs = require('fs'), path = require('path'), { spawn, spawnSync } = require('child_process');
const puppeteer = require('puppeteer-core');
const args = process.argv.slice(2);
const A = (k, d) => { const i = args.indexOf('--' + k); return i < 0 ? d : (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true) };
const ROOT = __dirname, OUT = path.resolve(A('out', path.join(ROOT, 'out'))), SEG = path.join(OUT, 'seg');
const DATAF = path.resolve(A('data', path.join(OUT, 'data.json')));
const CHROME = A('chrome', process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');
if (!fs.existsSync(CHROME)) { console.error('Chrome not found at ' + CHROME + ' (set CHROME=/path/to/chrome)'); process.exit(2) }
const DATA = JSON.parse(fs.readFileSync(DATAF, 'utf8'));
const FPS = DATA.meta.fps, W = DATA.meta.width, H = DATA.meta.height;
const CRF = String(A('crf', DATA.meta.crf || 22));
fs.mkdirSync(SEG, { recursive: true });
async function newPage(browser) {
  const p = await browser.newPage(); await p.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  await p.evaluateOnNewDocument(d => { window.__DATA = d }, DATA);
  await p.goto('file://' + path.join(ROOT, 'player.html')); await p.waitForFunction('window.READY===true'); return p
}
function ffmpegPipe(file) {
  return spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', CRF, '-pix_fmt', 'yuv420p', '-r', String(FPS), '-movflags', '+faststart', file], { stdio: ['pipe', 'inherit', 'inherit'] })
}
async function renderSeg(browser, sc) {
  const file = path.join(SEG, sc.id + '.mp4'), page = await newPage(browser), n = Math.round(sc.dur * FPS);
  const ff = ffmpegPipe(file), done = new Promise(r => ff.on('close', r));
  for (let i = 0; i < n; i++) {
    await page.evaluate((id, t) => renderScene(id, t), sc.id, i / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); await done; await page.close(); console.log('segment', sc.id, n, 'frames'); return file
}
(async () => {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--hide-scrollbars', '--force-device-scale-factor=1', '--font-render-hinting=none'] });
  const page = await newPage(browser), info = await page.evaluate(() => getInfo());
  if (A('stills')) {
    fs.mkdirSync(path.join(OUT, 'stills'), { recursive: true });
    for (const t of String(A('stills')).split(',').map(Number)) { await page.evaluate(t => renderGlobal(t), t); await page.screenshot({ path: path.join(OUT, 'stills', 't' + t.toFixed(1) + '.png') }) }
    await browser.close(); return
  }
  await page.close();
  const scenes = info.scenes.filter(s => !A('scene') || s.id === A('scene'));
  const conc = Number(A('conc', 4)), q = [...scenes];
  await Promise.all(Array.from({ length: conc }, async () => { while (q.length) { await renderSeg(browser, q.shift()) } }));
  await browser.close();
  if (!A('scene')) {
    const list = path.join(OUT, 'concat.txt'); fs.writeFileSync(list, info.scenes.map(s => `file '${path.join(SEG, s.id + '.mp4')}'`).join('\n'));
    const final = path.join(OUT, 'video_silent.mp4');
    const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', final], { stdio: 'inherit' });
    console.log('wrote', final, 'status', r.status);
  }
})();
