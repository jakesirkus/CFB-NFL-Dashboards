// Pace + projected score smoke test. usage: node verify_pace.js PAGE.html "Team A" "Team B" "Team with a box score"
const fs=require('fs'), path=require('path'); const {JSDOM}=require('jsdom'); const page=process.argv[2];
const dom=new JSDOM(fs.readFileSync(page,'utf8'),{runScripts:'dangerously',pretendToBeVisual:true,url:'http://localhost/',
  beforeParse(w){ w.fetch=async(u)=>{ const f=path.join(path.dirname(page),String(u).replace(/^https?:\/\/[^/]+\//,'')); const b=fs.readFileSync(f,'utf8'); return {ok:true,status:200,json:async()=>JSON.parse(b),text:async()=>b}; }; }});
const w=dom.window,d=w.document,wait=ms=>new Promise(r=>setTimeout(r,ms)); const e=[]; w.addEventListener('error',x=>e.push(x.message));
(async()=>{await wait(2000);
 d.getElementById('tabBtnMatchup').click(); await wait(150);
 const A=d.getElementById('mtA'),B=d.getElementById('mtB'); A.value=process.argv[3]; B.value=process.argv[4]; A.dispatchEvent(new w.Event('change')); await wait(150);
 const card=d.querySelector('#mtOut .mt-card'); console.log('card:',card.querySelector('h3').textContent,'|',card.children[2].textContent.replace(/\s+/g,' '));
 [...card.querySelectorAll('tr')].slice(0,5).forEach(r=>console.log('  ',r.textContent.replace(/\s+/g,' ')));
 const s=d.getElementById('mtSite'); s.value='n'; s.dispatchEvent(new w.Event('change')); await wait(100);
 console.log('neutral:',d.querySelector('#mtOut .mt-card').children[2].textContent.replace(/\s+/g,' '));
 d.getElementById('tabBtnLeaderboard').click(); await wait(200);
 console.log('lb pace cols:',[...d.querySelectorAll('#lbHead th')].map(t=>t.textContent).filter(x=>/Sec|Plays|Drives|TOP/.test(x)).join(' | '));
 d.getElementById('tabBtnTeam').click(); await wait(100);
 const ti=d.getElementById('teamInput'); ti.value=process.argv[5]; ti.dispatchEvent(new w.Event('input',{bubbles:true})); ti.dispatchEvent(new w.Event('change',{bubbles:true})); await wait(400);
 console.log('tiles:',[...d.querySelectorAll('.tile')].map(t=>t.textContent).filter(x=>/play \(adj|Pace/.test(x)).join(' | '));
 const cards=d.querySelectorAll('.game-card-clickable'); cards[cards.length-1].dispatchEvent(new w.Event('click',{bubbles:true})); await wait(1500);
 console.log('box:',[...d.querySelectorAll('tr')].map(r=>r.textContent.trim().replace(/\s+/g,' ')).filter(x=>/^(Time of Possession|Sec\/Play)/.test(x)).join(' | '));
 console.log('errors',e.length,e.slice(0,3)); })();
