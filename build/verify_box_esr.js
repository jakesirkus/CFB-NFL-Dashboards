// Opens a game's box score and checks the early-down success rate rows render.
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
  const ovr = rows.findIndex(r => r.startsWith('Success Rate'));
  console.log('box title:', (doc.getElementById('bsTitle') || {}).textContent);
  console.log('overall rows:', rows.slice(ovr, ovr + 2));
  console.log('early-downs rows:', rows.filter((r,i) => /^Success Rate/.test(r) && i>ovr+1).concat(rows.filter(r=>/^Early Down Success Rate/.test(r))));
  console.log('has "Early Down Success Rate":', box.includes('Early Down Success Rate'), '| runtime errors:', errors.length, errors.slice(0, 3));
})();
