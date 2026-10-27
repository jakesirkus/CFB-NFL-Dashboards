// Team page + leaderboard under Raw vs Opponent-adjusted. usage: node verify_adj.js PAGE.html "Team"
const fs=require('fs'); const {JSDOM}=require("jsdom");
const dom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{runScripts:'dangerously',pretendToBeVisual:true});
const w=dom.window, d=w.document, wait=ms=>new Promise(r=>setTimeout(r,ms)); const errs=[]; w.addEventListener('error',e=>errs.push(e.message));
(async()=>{ await wait(1500); const ti=d.getElementById('teamInput'); ti.value=process.argv[3]; ti.dispatchEvent(new w.Event('change',{bubbles:true})); await wait(300);
 const grab=()=>({ypp:d.getElementById('mYpp').textContent, exp:d.getElementById('mExp').textContent, epa:[...d.querySelectorAll('#epaPanel *')].map(e=>e.childElementCount===0?e.textContent:'').filter(x=>x).slice(0,8).join(' | '), series:d.getElementById('seriesOffVal').textContent+' '+d.getElementById('seriesOffRank').textContent});
 const raw=grab(); d.getElementById('modeAdj').click(); await wait(200); const adj=grab();
 d.getElementById('tabBtnLeaderboard').click(); await wait(200); const lbA=[...d.querySelectorAll('#lbBody tr')].slice(0,5).map(r=>r.children[0].textContent+' '+r.children[3].textContent);
 d.getElementById('modeRaw').click(); await wait(200); const lbR=[...d.querySelectorAll('#lbBody tr')].slice(0,5).map(r=>r.children[0].textContent+' '+r.children[3].textContent);
 console.log('RAW',JSON.stringify(raw)); console.log('ADJ',JSON.stringify(adj)); console.log('note:',d.getElementById('adjNote').hidden?'(hidden in raw)':'shown');
 console.log('LB raw top5:',lbR.join(' ; ')); console.log('LB adj top5:',lbA.join(' ; ')); console.log('errors',errs.length,errs.slice(0,3)); })();
