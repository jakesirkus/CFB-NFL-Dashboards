// Schedule tab smoke test. usage: node verify_schedule.js PAGE.html
const fs=require('fs'); const {JSDOM}=require('jsdom');
const dom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{runScripts:'dangerously',pretendToBeVisual:true}); const w=dom.window,d=w.document,wait=ms=>new Promise(r=>setTimeout(r,ms)); const e=[]; w.addEventListener('error',x=>e.push(x.message));
(async()=>{await wait(1500); d.getElementById('tabBtnSchedule').click(); await wait(200);
 const rows=()=>[...d.querySelectorAll('#scBody tr')].map(r=>[...r.children].map(c=>c.textContent).join(' | '));
 console.log('header:',[...d.querySelectorAll('#scHead th')].map(t=>t.textContent).join(' | ')); console.log('rows',rows().length); rows().slice(0,3).forEach(r=>console.log('  ',r));
 const hd=[...d.querySelectorAll('#scHead th')]; hd[12].click(); await wait(100); console.log('sorted by Opp Pass D:'); rows().slice(0,3).forEach(r=>console.log('  ',r));
 const cell=d.querySelector('#scBody tr td:nth-child(13)'); console.log('cell tooltip:',cell&&cell.title);
 d.getElementById('tabBtnRankings').click(); await wait(100); console.log('rankings active:',d.querySelector('[data-view="rankings"]').classList.contains('active'),'| schedule hidden:',!d.querySelector('[data-view="schedule"]').classList.contains('active'));
 d.getElementById('tabBtnTeam').click(); await wait(100); console.log('team active:',d.querySelector('[data-view="team"]').classList.contains('active'),'| errors',e.length,e.slice(0,2)); })();
