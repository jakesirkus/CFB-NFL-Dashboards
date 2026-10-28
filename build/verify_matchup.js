// Matchup tab smoke test. usage: node verify_matchup.js PAGE.html "Team A" "Team B"
const fs=require('fs'); const {JSDOM}=require('jsdom');
const dom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{runScripts:'dangerously',pretendToBeVisual:true}); const w=dom.window,d=w.document,wait=ms=>new Promise(r=>setTimeout(r,ms)); const e=[]; w.addEventListener('error',x=>e.push(x.message));
(async()=>{await wait(1500); d.getElementById('tabBtnMatchup').click(); await wait(150);
 const A=d.getElementById('mtA'),B=d.getElementById('mtB'); A.value=process.argv[3]; B.value=process.argv[4]; A.dispatchEvent(new w.Event('change')); await wait(150);
 const dump=()=>[...d.querySelectorAll('#mtOut table.mt')].map(t=>[...t.querySelectorAll('tr')].map(r=>r.textContent.replace(/\s+/g,' ').trim()));
 let T=dump(); console.log('note:',d.getElementById('mtNote').textContent.slice(0,60)); console.log('unit table:'); T[0].forEach(r=>console.log('  ',r));
 console.log('A off vs B def (first 8 rows):'); T[1].slice(0,8).forEach(r=>console.log('  ',r)); console.log('subs:',[...d.querySelectorAll('#mtOut .mt-sub')].map(x=>x.textContent).join(' || '));
 d.getElementById('modeAdj').click(); await wait(150); T=dump(); console.log('after Adjusted toggle, note:',d.getElementById('mtNote').textContent.slice(0,40),'| row:',T[1][2]);
 d.getElementById('mtSwap').click(); await wait(100); console.log('swapped ->',d.getElementById('mtA').value,'vs',d.getElementById('mtB').value);
 d.getElementById('tabBtnTeam').click(); await wait(100); console.log('team active:',d.querySelector('[data-view="team"]').classList.contains('active'),'| errors',e.length,e.slice(0,3)); })();
