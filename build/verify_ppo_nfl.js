const fs=require('fs');const {JSDOM}=require('jsdom');
const dom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{runScripts:'dangerously',pretendToBeVisual:true});
const w=dom.window,d=w.document;const errs=[];w.addEventListener('error',e=>errs.push(e.message));
setTimeout(()=>{
  const ti=d.getElementById('teamInput'); ti.value='San Francisco 49ers'; ti.dispatchEvent(new w.Event('input',{bubbles:true})); ti.dispatchEvent(new w.Event('change',{bubbles:true}));
  setTimeout(()=>{
    const hit=[...d.querySelectorAll('#radarDef .radar-hit')].find(h=>h.getAttribute('aria-label').startsWith('Points/Opp'));
    hit.dispatchEvent(new w.Event('click',{bubbles:true}));
    setTimeout(()=>{ const tip=d.querySelector('#radarDef').closest('.radar-card').querySelector('.radar-tip');
      console.log('tip:', tip && tip.textContent.slice(0,200), '| errors', errs); },200);
  },500);
},2500);
