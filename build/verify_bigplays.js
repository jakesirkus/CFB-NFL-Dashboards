// Box score Big Plays rows (20+/30+/40+) with hover lists, full game and a split.
// usage: node verify_box_esr.js PAGE.html "Team Name"   (CFB page fetches period shards from disk next to the page)
const fs = require('fs'), path = require('path');
const { JSDOM } = require('jsdom');
const page = process.argv[2], team = process.argv[3] || 'Alabama';
const html = fs.readFileSync(page, 'utf8');
const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'http://localhost/' ,
  beforeParse(w) {   // serve the split shards (fetch('periods/pack_XX.json')) from the page's folder
    w.fetch = async (u) => { const f = path.join(path.dirname(page), String(u).replace(/^https?:\/\/[^/]+\//, ''));
      const body = fs.readFileSync(f, 'utf8'); return { ok: true, status: 200, json: async () => JSON.parse(body), text: async () => body }; };
  } });
const { window } = dom; const doc = window.document;
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const errors = [];
  window.addEventListener('error', e => errors.push(e.error ? e.error.message : e.message));
  await wait(2000);
  const ti = doc.getElementById('teamInput');
  ti.value = team; ti.dispatchEvent(new window.Event('input', { bubbles: true })); ti.dispatchEvent(new window.Event('change', { bubbles: true }));
  await wait(500);
  const cards = doc.querySelectorAll('.game-card-clickable');
  cards[cards.length - 1].dispatchEvent(new window.Event('click', { bubbles: true }));
  await wait(1500);
  const box = doc.body.textContent;
  const rows = [...doc.querySelectorAll('tr')].map(r => r.textContent.trim().replace(/\s+/g, ' '));
  const dump = () => [...doc.querySelectorAll('tr')].map(r => r.textContent.trim().replace(/\s+/g, ' '));
  console.log('box title:', (doc.getElementById('bsTitle') || {}).textContent);
  const cnt = [...doc.querySelectorAll('span.bp-cnt')];
  console.log('big-play cells with lists:', cnt.length);
  const r40 = [...doc.querySelectorAll('tr')].find(r => r.firstChild && r.firstChild.textContent === '40+ Yard Plays');
  console.log('40+ row cells:', r40 ? [...r40.children].slice(1).map(td => (td.querySelector('.bp-cnt') ? td.querySelector('.bp-cnt').firstChild.textContent + ' [' + td.querySelectorAll('.bp-item').length + ' listed]' : td.textContent)) : 'MISSING');
  if (cnt.length) { const it = cnt[cnt.length - 1].querySelectorAll('.bp-item'); console.log('sample popup item:', it[0].textContent.replace(/\s+/g, ' ').slice(0, 140)); }
  const sel = doc.getElementById('bsPeriodSelect');
  if (sel) { sel.value = 'q2'; sel.dispatchEvent(new window.Event('change', { bubbles: true })); await wait(1500);
    const r = [...doc.querySelectorAll('tr')].find(r => r.firstChild && r.firstChild.textContent === '20+ Yard Plays');
    console.log('Q2 split 20+ row:', r ? r.textContent.replace(/\s+/g, ' ').slice(0, 60) : 'MISSING', '| options', [...sel.options].map(o => o.value).join(',')); }
  console.log('runtime errors:', errors.length, errors.slice(0, 3));
})();
