// Rankings tab smoke test. usage: node verify_rankings.js PAGE.html
const fs=require('fs'); const {JSDOM}=require('jsdom');
const dom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{runScripts:'dangerously',pretendToBeVisual:true}); const w=dom.window,d=w.document,wait=ms=>new Promise(r=>setTimeout(r,ms)); const e=[]; w.addEventListener('error',x=>e.push(x.message));
(async()=>{await wait(1500); d.getElementById('tabBtnRankings').click(); await wait(200);
 const rows=()=>[...d.querySelectorAll('#rkBody tr')].map(r=>[...r.children].map(c=>c.textContent).join(' | '));
 console.log('header:',[...d.querySelectorAll('#rkHead th')].map(t=>t.textContent).join(' | ')); console.log('rows',rows().length); rows().slice(0,4).forEach(r=>console.log('  ',r));
 const hd=[...d.querySelectorAll('#rkHead th')]; hd[11].click(); await wait(100); console.log('sorted by avg opp (hardest first):'); rows().slice(0,3).forEach(r=>console.log('  ',r));
 const sel=d.getElementById('rkConfFilter'); sel.value=sel.options[2].value; sel.dispatchEvent(new w.Event('change')); await wait(100); console.log('filter',sel.value,'rows',rows().length);
 d.getElementById('tabBtnTeam').click(); await wait(100); console.log('team view active:',d.querySelector('[data-view="team"]').classList.contains('active'),'| rankings hidden:',!d.querySelector('[data-view="rankings"]').classList.contains('active'),'| errors',e.length,e.slice(0,2)); })();
