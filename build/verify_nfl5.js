const fs=require('fs');const {JSDOM}=require('jsdom');
const html=fs.readFileSync(process.argv[2],'utf8');
const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true});
const w=dom.window, d=w.document; const errs=[];
w.addEventListener('error',e=>errs.push(e.message));
setTimeout(()=>{
  const D=JSON.parse(d.getElementById('dashboard-data').textContent);
  console.log('scope:',d.getElementById('scopeNote')&&d.getElementById('scopeNote').textContent.slice(0,160));
  const t=D.teams['Detroit Lions']; console.log('DET',t.gp,t.wins+'-'+t.losses,'rushSR off',t.radar.offRaw.rushSR,'dbEPA',t.epaPerDropback,'ranks',t.ranks.epaPerDropback);
  console.log('DET games',D.games['Detroit Lions'].map(g=>g.week+g.result+g.ts+'-'+g.os).join(' '));
  const b=D.boxscores['2026_05_DET_ARI']; console.log('w5 box keys',Object.keys(b), 'drives',b.driveChart.length, 'DET overall epa pct',b['Detroit Lions'].overall.epaPlay);
  console.log('errors',errs.length,errs.slice(0,3));
},2500);
