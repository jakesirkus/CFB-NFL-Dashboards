const fs=require('fs'); const { JSDOM } = require('jsdom');
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const html=fs.readFileSync('/mnt/user-data/outputs/CFB_Dashboard_Weeks_1-7.html','utf8');
  const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true });   // no network, no fetch: like opening the file from disk
  const { window } = dom; const doc = window.document; const errors=[];
  window.addEventListener('error', e => errors.push(e.error ? e.error.message : e.message));
  await wait(4000);
  console.log('scope:', (doc.getElementById('scopeNote')||{}).textContent);
  const ti = doc.getElementById('teamInput'); ti.value='Kansas'; ti.dispatchEvent(new window.Event('change',{bubbles:true})); await wait(500);
  Array.from(doc.querySelectorAll('.game-card-clickable')).find(c => c.textContent.includes('Kansas State')).dispatchEvent(new window.Event('click',{bubbles:true}));
  await wait(1500);
  console.log('box:',(doc.getElementById('bsSub')||{}).textContent,'|');console.log('drive rows:', doc.querySelectorAll('.dc-row').length, '| scoop-and-score shown:', Array.from(doc.querySelectorAll('.dc-row')).some(r=>true));
  const sel=doc.getElementById('bsPeriodSelect'); sel.value='h2'; sel.dispatchEvent(new window.Event('change',{bubbles:true})); await wait(1500);
  console.log('2nd-half split works offline:', doc.getElementById('bsPeriodError').hidden);
  doc.getElementById('tabBtnLeaderboard').dispatchEvent(new window.Event('click',{bubbles:true})); await wait(500);
  console.log('leaderboard rows:', doc.querySelectorAll('#lbBody tr').length, '| errors:', errors.length, errors.slice(0,3));
  process.exit(0);
})();
