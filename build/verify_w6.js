const fs = require('fs');
const { JSDOM } = require('jsdom');
const html = fs.readFileSync(process.argv[2], 'utf8');
const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true });
const { window } = dom; const doc = window.document;
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const errors = [];
  window.addEventListener('error', e => errors.push(e.error ? e.error.message : e.message));
  await wait(2000);
  const ti = doc.getElementById('teamInput');
  if (ti) { ti.value = 'Alabama'; ti.dispatchEvent(new window.Event('input',{bubbles:true})); ti.dispatchEvent(new window.Event('change',{bubbles:true})); }
  await wait(400);
  const txt = doc.body.textContent;
  console.log('mentions Georgia:', txt.includes('Georgia'), '| 5-1:', /5\s*[-–]\s*1/.test(txt), '| Week 1–6:', txt.includes('Week 1–6'));
  console.log('game cards:', doc.querySelectorAll('.game-card-clickable').length, 'all cards:', doc.querySelectorAll('[class*=game-card]').length);
  doc.getElementById('tabBtnLeaderboard').dispatchEvent(new window.Event('click', { bubbles: true }));
  await wait(300);
  console.log('leaderboard rows:', doc.querySelectorAll('#lbBody tr').length);
  console.log('Rush SR% label present:', txt.includes('Rush SR%') || doc.body.innerHTML.includes('Rush SR%'));
  console.log('TOTAL runtime errors:', errors.length, errors.slice(0,5));
})();
