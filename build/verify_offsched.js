// Off-schedule runs: box score row (+ Q1 split) and leaderboard columns (raw + adjusted).
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
  console.log('box title:', (doc.getElementById('bsTitle') || {}).textContent);
  console.log('rushing rows:', rows.filter(r => /^(Stuffed|Opportunity|Off-Schedule) Runs/.test(r)));
  // a quarter split, if the page has split buttons
  const q = [...doc.querySelectorAll('button')].find(b => b.textContent.trim() === 'Q1');
  if (q) { q.click(); await wait(800); console.log('Q1 off-sched:', [...doc.querySelectorAll('tr')].map(r => r.textContent.trim().replace(/\s+/g, ' ')).filter(r => /^Off-Schedule/.test(r))); }
  doc.getElementById('tabBtnLeaderboard').click(); await wait(300);
  const head = [...doc.querySelectorAll('#lbHead th')].map(t => t.textContent);
  console.log('leaderboard has columns:', head.filter(h => /Off-Sched/.test(h)));
  const th = [...doc.querySelectorAll('#lbHead th')].find(t => /Off-Sched Run % \(Off\)/.test(t.textContent)); th.click(); await wait(200);
  console.log('sorted by off-sched (off), top 3:', [...doc.querySelectorAll('#lbBody tr')].slice(0, 3).map(r => r.textContent.replace(/\s+/g, ' ').slice(0, 40)));
  doc.getElementById('modeAdj').click(); await wait(200);
  console.log('adjusted top 3:', [...doc.querySelectorAll('#lbBody tr')].slice(0, 3).map(r => r.textContent.replace(/\s+/g, ' ').slice(0, 40)));
  console.log('runtime errors:', errors.length, errors.slice(0, 3));
})();
