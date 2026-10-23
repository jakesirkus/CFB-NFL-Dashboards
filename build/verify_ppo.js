const fs=require('fs');const {JSDOM}=require('jsdom');
const dom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{runScripts:'dangerously',pretendToBeVisual:true});
const w=dom.window,d=w.document;const errs=[];w.addEventListener('error',e=>errs.push(e.message));
setTimeout(()=>{
  const ti=d.getElementById('teamInput'); ti.value=process.argv[3]; ti.dispatchEvent(new w.Event('input',{bubbles:true})); ti.dispatchEvent(new w.Event('change',{bubbles:true}));
  setTimeout(()=>{
    const labs=[...d.querySelectorAll('#radarOff .radar-axis-label')].map(x=>x.textContent);
    const dot=[...d.querySelectorAll('#radarOff .radar-dot title')].map(x=>x.textContent).filter(t=>t.startsWith('Points/Opp'));
    const dotD=[...d.querySelectorAll('#radarDef .radar-dot title')].map(x=>x.textContent).filter(t=>t.startsWith('Points/Opp'));
    console.log('radar spokes',labs.length,'| off',dot,'| def',dotD);
    d.getElementById('tabBtnLeaderboard').click();
    setTimeout(()=>{
      const ths=[...d.querySelectorAll('#lbHead th')]; const i=ths.findIndex(t=>t.textContent.startsWith('Pts/Opp (Off)'));
      console.log('lb headers', ths.map(t=>t.textContent).slice(-5));
      ths[i].dispatchEvent(new w.Event('click',{bubbles:true}));
      setTimeout(()=>{ const rows=[...d.querySelectorAll('#lbBody tr')].slice(0,3).map(r=>r.children[0].textContent+' '+r.children[i].textContent);
        console.log('sorted by PPO off:',rows,'| rows',d.querySelectorAll('#lbBody tr').length,'| errors',errs.length,errs.slice(0,2)); },300);
    },300);
  },500);
},2500);
