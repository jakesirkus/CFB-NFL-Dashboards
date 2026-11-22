/* Live NFL box score: turns an ESPN game summary into the same record shape the NFL dashboard's box score uses
   (rec[team] = {meta, overall, production, rushing, explosiveness, situational, drives, defensive, turnovers,
   conversions, opportunities, periods}, rec.driveChart), following build/nfl_full/nfl_box.py / nfl_drives.py.
   EPA comes from a down/distance/yard-line EP model fitted to this season's nflverse EP (see nfl-model.json);
   success = EPA > 0, as in nflverse. Percentiles use the dashboard's own published team-games as the pool.
   Read-only with respect to the dashboards: nothing here touches their files or data. */
(function(root){
'use strict';
const NAME_FIX={};   // ESPN displayName == dashboard name for all 32 teams
let MODEL=null;
function setModel(m){MODEL=m}

/* ---------- EP model (port of build/cfb_full/epmodel.py features) ---------- */
function feat(down,dist,ytg){
  const K=21, w=new Array(4*(K+2)).fill(0);
  dist=Math.min(Math.max(dist,1),30); const y=Math.min(Math.max(ytg,0),100);
  let i=Math.min(Math.floor(y/5),K-2); const f=(y-5*i)/5; const o=(down-1)*(K+2);
  w[o+i]=1-f; w[o+i+1]=f; w[o+K]=Math.log(dist); w[o+K+1]=Math.min(dist,20)/10; return w}
function EP(down,dist,ytg){if(!(down>=1&&down<=4))return 0;const x=feat(down,dist,ytg),W=MODEL.ep.w;let s=0;for(let i=0;i<x.length;i++)s+=x[i]*W[i];return s}

/* ---------- helpers ---------- */
const r1=(x,n=1)=>x==null||!isFinite(x)?null:Math.round(x*10**n)/10**n;
const sdiv=(a,b)=>b?a/b:null;
const sum=(a,f)=>a.reduce((s,x)=>s+(f?f(x):x),0);
const secs=t=>{const m=String(t||'').match(/(\d+):(\d+)/);return m?(+m[1])*60+(+m[2]):null};
const RUNPAT=/\b(up the middle|left end|right end|left tackle|right tackle|left guard|right guard|rushes|runs?\b|direct snap|to the left|to the right)/i;
function lineYards(y){if(y<0)return 1.2*y;y=Math.min(y,11);return y<=4?y:(y<=8?4+0.5*(y-4):6+0.25*(y-8))}
const AUTOFD=/(defensive pass interference|defensive holding|illegal contact|roughing the passer|unnecessary roughness|face ?mask|horse collar|illegal use of hands|personal foul|lowering the head|taunting|unsportsmanlike)/i;
function penOnDefense(r,G){const m=r.text.match(/PENALTY on ([A-Z]{2,3})/);if(!m)return false;const d=G.T[r.def];return !!d&&(m[1]===d.abbr||(m[1]==='WAS'&&d.abbr==='WSH')||(m[1]==='WSH'&&d.abbr==='WAS')||(m[1]==='LA'&&d.abbr==='LAR'))}
const NONPLAY=/^(timeout|official timeout|end period|end of half|end of game|two-minute warning|coin toss|end of regulation)/i;

/* ---------- ESPN summary -> nflverse-like rows ---------- */
function parse(sum_){
  const hc=sum_.header.competitions[0];
  const comp=hc.competitors; const home=comp.find(c=>c.homeAway==='home'), away=comp.find(c=>c.homeAway==='away');
  const T={}; for(const c of comp)T[c.team.id]={id:c.team.id,abbr:c.team.abbreviation,name:c.team.displayName,home:c.homeAway==='home'};
  const other=id=>id===home.team.id?away.team.id:home.team.id;
  const drives=[...(sum_.drives?.previous||[])]; const cur=sum_.drives?.current; if(cur&&!drives.some(d=>d.id===cur.id))drives.push(cur);
  const rows=[];
  drives.forEach((dr,di)=>{
    for(const p of dr.plays||[]){
      const ty=p.type?.text||'', tx=p.text||'';
      if(NONPLAY.test(ty)||/^timeout/i.test(tx))continue;
      const st=p.start||{}, en=p.end||{};
      const kick=/kickoff/i.test(ty)||/\bkicks\b/.test(tx)&&!/field goal/i.test(tx);
      const punt=/punt/i.test(ty)&&!/punt formation\)/i.test(tx)||/\bpunts\b/.test(tx);
      let pos=st.team?.id||dr.team?.id; if(kick)pos=other(st.team?.id||'');
      const noPlay=/no play/i.test(tx)||/\bnullified\b/i.test(tx);
      const r={id:p.id,di,qtr:p.period?.number||0,clock:p.clock?.displayValue||'',qsec:secs(p.clock?.displayValue),type:ty,text:tx,
        pos,def:other(pos),down:st.down>0?st.down:null,ydstogo:st.distance??0,yl:st.yardsToEndzone??null,
        goal:/goal/i.test(st.shortDownDistanceText||st.downDistanceText||'')||(st.down>0&&st.distance>=st.yardsToEndzone),
        endTeam:en.team?.id||null,endDown:en.down||0,endDist:en.distance||0,endYl:en.yardsToEndzone??null,
        hs:p.homeScore,as:p.awayScore,scoring:!!p.scoringPlay,penalty:!!p.isPenalty||/PENALTY/.test(tx),noPlay,kick,punt,
        fg:/field goal/i.test(ty)||/field goal/i.test(tx)&&!/fake/i.test(tx),pat:/extra point/i.test(ty)||/extra point/i.test(tx)&&!(st.down>0),
        stat:p.statYardage??0};
      classify(r); rows.push(r);
      // two-point try written inside the touchdown play (ESPN): give it its own row, like nflverse
      const m=tx.match(/TWO-POINT CONVERSION ATTEMPT\.(.*?)(ATTEMPT (SUCCEEDS|FAILS))/i);
      if(m&&!/^two-point/i.test(ty)){const t2={...r,id:p.id+'_2pt',text:'TWO-POINT CONVERSION ATTEMPT.'+m[1]+m[2],down:null,ydstogo:2,yl:2,goal:true,scoring:/SUCCEEDS/i.test(m[3]),stat:0,penalty:false,noPlay:false};
        classify(t2,true); t2.twoPt=true; t2.twoOk=/SUCCEEDS/i.test(m[3]); t2.td=false; t2.parent=r; rows.push(t2);}
      const x=tx.match(/extra point is (GOOD|No Good|Blocked)|extra point.{0,40}(BLOCKED)/i);
      if(x&&!/^extra point/i.test(ty)&&!r.pat){const pr={...r,id:p.id+'_pat',text:'(extra point) '+x[0],down:null,yl:15,goal:false,scoring:/GOOD/i.test(x[0]),stat:0,penalty:false,noPlay:false,kick:false,punt:false,fg:false};
        classify(pr,false); pr.pat=true; pr.patOk=/GOOD/i.test(x[0]); pr.is_scrim=pr.is_rush=pr.is_db=pr.passAtt=pr.rushAtt=false; pr.td=false; pr.int=pr.fumble=pr.forced=pr.pd=false; pr.parent=r; rows.push(pr);}
    }
  });
  rows.forEach((r,i)=>r.i=i);
  return {rows,drives,T,home:home.team.id,away:away.team.id,hc};
}
function classify(r,two){
  const tx=r.text, ty=r.type;
  r.twoPt=two||/^two-point/i.test(ty)||/^TWO-POINT CONVERSION/i.test(tx)&&!(r.down>0);
  if(r.twoPt&&!two){r.twoOk=/SUCCEEDS|good/i.test(tx)&&!/FAILS/i.test(tx);r.down=null}
  const live=!r.noPlay&&!r.kick&&!r.punt&&!r.fg&&!r.pat&&(r.down>0||r.twoPt);
  r.kneel=live&&/kneels/i.test(tx); r.spike=live&&/spiked/i.test(tx);
  r.scramble=live&&/scrambles/i.test(tx); r.sack=live&&/sacked/i.test(tx);
  r.passAtt=live&&!r.scramble&&(r.sack||r.spike||/\bpass\b/i.test(tx.split(/PENALTY/i)[0]));
  r.is_db=live&&(r.passAtt||r.scramble);
  r.rushAtt=live&&!r.is_db&&(/^(rush|rushing touchdown)$/i.test(ty)||RUNPAT.test(tx.split(/PENALTY/i)[0])||r.kneel||(/fumble/i.test(ty)&&r.down>0));
  r.is_rush=r.rushAtt&&!r.kneel;
  r.is_scrim=r.is_rush||r.is_db;
  // ESPN keeps the original call in the text after a replay reversal; the play type carries the final ruling
  const reversedToInc=/^pass incompletion$/i.test(ty), reversedToSack=/^sack/i.test(ty)&&!/sacked/i.test(tx);
  if(reversedToSack){r.sack=true;r.passAtt=live;r.is_db=live}
  r.int=!r.noPlay&&/INTERCEPTED/i.test(tx)&&(/interception/i.test(ty)||(/fumble/i.test(ty)&&!/sack/i.test(ty))||(/penalty/i.test(ty)))&&!reversedToInc&&!reversedToSack;
  r.comp=r.passAtt&&!r.sack&&!r.spike&&!r.int&&(/^(pass reception|passing touchdown)$/i.test(ty)||(!reversedToInc&&!/incomplete/i.test(tx)&&!/INTERCEPTED/i.test(tx)));
  r.reversedInc=reversedToInc;
  r.fumble=/FUMBLES|MUFFS/i.test(tx)&&!r.noPlay;
  r.forced=/FUMBLES \((?!aborted)[^)]+\)/i.test(tx)&&!r.noPlay;
  r.pd=(r.int||/incomplete[^(]*?\((?!shotgun|no huddle)[^)]+\)/i.test(tx.split(/PENALTY/i)[0])||(r.reversedInc&&/INTERCEPTED/i.test(tx)))&&!r.noPlay;
  r.td=/TOUCHDOWN/i.test(tx)&&!/TOUCHDOWN NULLIFIED/i.test(tx)&&!r.noPlay&&!r.twoPt&&(r.scoring||/touchdown/i.test(ty))&&!(r.reversedInc&&!/touchdown/i.test(ty));
  r.safety=/SAFETY/i.test(tx)&&!r.noPlay&&!/penalty on .*safety/i.test(tx);
}
function finish(G){
  const {rows,T}=G;
  for(const r of rows){
    // who fumbled, and was it lost
    const recTeam=(r.text.match(/RECOVERED by ([A-Z]{2,3})-/)||[])[1];
    r.fumTeam=null;r.fumLost=false;
    if(r.fumble){
      if(r.punt||r.kick){r.fumTeam=r.punt?r.def:r.pos; r.fumLost=r.endTeam!=null&&r.endTeam!==r.fumTeam||(!!recTeam&&recTeam!==T[r.fumTeam]?.abbr&&!/and recovers/i.test(r.text))}
      else if(r.int){r.fumTeam=r.def; r.fumLost=r.endTeam!=null&&r.endTeam===r.pos}   // fumble on the interception return
      else {r.fumTeam=r.pos; r.fumLost=r.endTeam!=null&&r.endTeam!==r.pos}
    }
    r.tdTeam=!r.td?null:r.punt?(r.fumLost?r.pos:r.def):(r.fg&&!r.is_scrim)?r.def:((r.int||r.fumLost)?r.def:r.pos);
    // yards gained, nflverse-style
    let y=r.stat;
    if(r.is_scrim){
      const pre=r.text.split(/PENALTY|FUMBLES/i)[0];
      if(r.int||r.reversedInc)y=0;
      else if(r.fumble&&!r.penalty&&r.yl!=null&&r.endYl!=null){y=r.fumLost?r.yl-(100-r.endYl):r.yl-r.endYl}   // nflverse: yards to the recovery spot
      else if(r.penalty||r.fumble){const m=pre.match(/for (-?\d+) (?:yards?|yds?)/i);y=m?+m[1]:(/no gain|incomplete/i.test(pre)?0:y)}
      else if(/incomplete/i.test(r.text))y=0;
    }
    r.yds=y;
    const prog=(r.yl!=null&&r.endYl!=null)?r.yl-r.endYl:0;
    const auto=r.penalty&&r.endTeam===r.pos&&r.endDown===1&&r.down>0&&AUTOFD.test(r.text)&&penOnDefense(r,G);
    r.conv=(r.td&&r.tdTeam===r.pos)||auto||(!r.td&&r.down>0&&r.endTeam===r.pos&&r.endDown===1&&!r.int&&!r.fumLost&&(r.down>1||prog>=r.ydstogo||(prog>0&&r.endDist!==r.ydstogo-prog)));
  }
  for(const r of rows)if(r.parent){const t=r.parent.tdTeam||r.parent.pos;r.pos=t;r.def=t===G.home?G.away:G.home;}
  // EPA for scrimmage rows
  const M=MODEL.ep;
  rows.forEach((r,i)=>{
    r.epa=null;
    if(r.twoPt){r.epa=r.twoOk?M.twoPt.success:M.twoPt.fail;return}
    if(r.pat){r.epa=r.patOk?0.04:-0.96;return}
    if(!r.pos)return;
    if(!(r.down>0)&&!r.kick)return;
    const e0=r.kick?1.11:EP(r.down,r.ydstogo,r.yl);
    if(r.fg&&!r.is_scrim&&/GOOD/i.test(r.text)&&!/no good/i.test(r.text)&&!r.noPlay){r.epa=3-e0;return}
    if(r.td)r.epa=(r.tdTeam===r.pos?M.td:M.oppTd)-e0;
    else if(r.safety)r.epa=M.safety-e0;
    else{
      let en=null,team=null;
      if(r.endDown>=1&&r.endDown<=4&&r.endYl>0&&r.endYl<100&&r.endTeam){en=EP(r.endDown,r.endDist,r.endYl);team=r.endTeam}
      else{const half=r.qtr<=2?1:r.qtr<=4?2:3;for(let j=i+1;j<rows.length;j++){const n=rows[j];const h=n.qtr<=2?1:n.qtr<=4?2:3;if(h!==half)break;if(n.down>0&&!n.kick){en=EP(n.down,n.ydstogo,n.yl);team=n.pos;break}}}
      r.epa=en==null?-e0:(team===r.pos?en:-en)-e0;
    }
  });
  for(const r of rows){r.succ=r.epa!=null&&r.epa>0;r.expl=(r.is_rush&&r.yds>=10)||(r.is_db&&r.yds>=15);r.explP=r.is_db&&r.yds>=15;r.explR=r.is_rush&&r.yds>=10}
  buildSeries(G); buildDrives(G);
}

/* ---------- series (sets of downs) ---------- */
function buildSeries(G){
  const S=[];let cur=null;
  const rows=G.rows;
  rows.forEach((r,i)=>{
    if(!(r.down>0)||r.kick)return;
    if(!cur||cur.team!==r.pos||cur.closed||cur.di!==r.di){cur={team:r.pos,di:r.di,rows:[],closed:false,succ:false,res:null,q:null};S.push(cur)}
    cur.rows.push(r); if(cur.q==null)cur.q=r.qtr;
    if(r.td&&r.tdTeam===r.pos){cur.succ=true;cur.res='Touchdown';cur.closed=true}
    else if(r.conv){cur.succ=true;cur.res='First down';cur.closed=true}
  });
  for(const s of S){
    if(s.res)continue;
    const last=s.rows[s.rows.length-1];
    if(last.kneel)s.res='QB kneel';
    else if(last.punt)s.res='Punt';
    else if(last.fg)s.res='Field goal';
    else if(last.int||last.fumLost)s.res=last.td?'Opp touchdown':'Turnover';
    else if(last.safety)s.res='Safety';
    else{const nx=rows[last.i+1];const endHalf=!nx||((last.qtr===2||last.qtr>=4)&&nx.qtr!==last.qtr)||(nx&&nx.kick&&!(last.down===4&&last.endTeam!==last.pos));
      s.res=last.down===4&&last.endTeam&&last.endTeam!==last.pos?'Turnover on downs':(endHalf&&!(last.down===4)?'End of half':'Turnover on downs')}
    if(s.q==null)s.q=s.rows[0].qtr;
  }
  G.series=S;
}

/* ---------- drives (port of nfl_drives.build_drives, from ESPN drives) ---------- */
const COLOR={'Punt (Return TD)':'blue','Touchdown':'blue','Field Goal':'blue','Interception (Pick-6)':'blue','Fumble (Defensive TD)':'blue','Punt':'gray','End of Game':'gray','End of Half':'gray'};
const RES={'TD':'Touchdown','TOUCHDOWN':'Touchdown','FG':'Field Goal','FIELD GOAL':'Field Goal','PUNT':'Punt','INT':'Interception','INTERCEPTION':'Interception','FUMBLE':'Fumble','FUMBLE LOST':'Fumble','DOWNS':'Turnover on Downs','MISSED FG':'Missed FG','FG MISSED':'Missed FG','END OF HALF':'End of Half','END OF GAME':'End of Game','SAFETY':'Safety','BLOCKED FG':'Blocked FG','BLOCKED PUNT':'Blocked Punt','INT TD':'Interception (Pick-6)','FUMBLE TD':'Fumble (Defensive TD)','PUNT TD':'Punt (Return TD)','BLOCKED FG, DOWNS':'Blocked FG','MISSED FG TD':'Missed FG','BLOCKED PUNT TD':'Blocked Punt','BLOCKED FG TD':'Blocked FG'};
function penInfo(tx,G){const m=tx.match(/PENALTY on ([A-Z]{2,3})-?[^,]*,\s*([^,]+?),\s*(\d+) yards?/i);if(!m)return{};const t=Object.values(G.T).find(x=>x.abbr===m[1]||(m[1]==='WAS'&&x.abbr==='WSH')||(m[1]==='WSH'&&x.abbr==='WAS'));return{penaltyTeam:t?t.abbr:m[1],penaltyType:m[2].trim(),penaltyYards:+m[3]}}
function buildDrives(G){
  const {rows,T}=G; const out=[]; let ph=0,pa=0,prevRes=null;
  G.drives.forEach((dr,di)=>{
    const pr=rows.filter(r=>r.di===di); if(!pr.length)return;
    const scrimRows=pr.filter(r=>r.is_scrim&&!r.twoPt);
    const team=(scrimRows[0]||pr.find(r=>r.down>0)||pr[0]).pos; const opp=team===G.home?G.away:G.home;
    const isHome=team===G.home;
    const hs=Math.max(ph,...pr.map(r=>r.hs??0)), as=Math.max(pa,...pr.map(r=>r.as??0));
    const first=pr.find(r=>r.pos===team&&r.down>0);
    const lastSnap=[...pr].reverse().find(r=>r.down>0||r.twoPt)||pr[pr.length-1];
    const dres=String(dr.displayResult||dr.result||'').toUpperCase();
    let res=RES[dres]||(dr.displayResult||'')||(dr===G.drives[G.drives.length-1]?'In Progress':'');
    if(res==='Interception'&&pr.some(r=>r.int&&r.td))res='Interception (Pick-6)';
    if(res==='Fumble'&&pr.some(r=>r.fumLost&&r.td))res='Fumble (Defensive TD)';
    if(res==='Punt'&&pr.some(r=>r.punt&&r.td&&r.tdTeam!==team))res='Punt (Return TD)';
    const fdr=res==='Touchdown'?'Touchdown':res==='Field Goal'?'Field goal':/Pick-6|Defensive TD|Return TD/.test(res)||pr.some(r=>r.td&&r.tdTeam&&r.tdTeam!==team)?'Opp touchdown':res==='Safety'?'Safety':res;
    const how=prevRes==null?'KO':/Punt/.test(prevRes)&&!/Return TD/.test(prevRes)?'PUNT':/Interception/.test(prevRes)&&!/Pick-6/.test(prevRes)?'INT':/^Fumble$/.test(prevRes)?'FUMB':/Downs|Missed FG|Blocked/.test(prevRes)?'DOWNS':'KO';
    const lastRow=[...pr].reverse().find(r=>!/^timeout/i.test(r.text))||pr[pr.length-1];
    const spot1=first&&first.yl!=null?100-first.yl:null;
    const endYl=lastSnap.pos===team?(lastSnap.yl):null;
    const d={n:di+1,team:T[team].name,opponent:T[opp].name,how,q1:pr[0].qtr,t1:pr[0].clock,spot1,
      q2:lastRow.qtr,t2:lastRow.clock,spot2:endYl!=null?100-endYl:null,plays:scrimRows.length,yards:sum(scrimRows,r=>r.yds),
      top:dr.timeElapsed?.displayValue||null,result:res,color:COLOR[res]||'red',clickable:true,
      opp30:pr.some(r=>r.is_scrim&&!r.twoPt&&r.yl!=null&&r.yl<=30&&r.pos===team),playText:lastRow.text,
      playList:pr.map(r=>{const e={q:r.qtr,text:r.text,scoring:r.scoring,penalty:r.penalty,down:r.down,distance:r.down?r.ydstogo:0,goalToGo:r.goal,yardline100:r.yl};if(r.penalty)Object.assign(e,penInfo(r.text,G));return e}),
      teamScore:isHome?hs:as,oppScore:isHome?as:hs,scored:pr.some(r=>r.scoring)};
    d._rz=pr.some(r=>r.is_scrim&&!r.twoPt&&r.pos===team&&r.yl!=null&&r.yl<=20);
    d._rztd=pr.some(r=>r.is_scrim&&!r.twoPt&&r.pos===team&&r.yl<=20&&r.td&&r.tdTeam===team);
    d._epa=sum(scrimRows.filter(r=>r.epa!=null),r=>r.epa); d._scrim=scrimRows.length; d._fdr=fdr; d._tm=team; d._di=di;
    d._pts=isHome?hs-ph:as-pa; ph=hs; pa=as; prevRes=res;
    out.push(d);
  });
  G.dchart=out;
}

/* ---------- team box (port of nfl_box.team_box) ---------- */
function teamBox(G,rowsIn,T_,O_,drives,period,ps){
  const o=rowsIn.filter(r=>r.pos===T_), d=rowsIn.filter(r=>r.pos===O_);
  const os=o.filter(r=>r.is_scrim), orush=o.filter(r=>r.is_rush), opa=o.filter(r=>r.passAtt);
  let odb=o.filter(r=>r.is_db||r.spike);
  const ds=d.filter(r=>r.is_scrim), drush=d.filter(r=>r.is_rush), ddb=d.filter(r=>r.is_db||r.spike);
  const ep=x=>sum(x,r=>r.epa||0), yd=x=>sum(x,r=>r.yds);
  const n=os.length, yards=yd(os), epa=ep(os);
  const exm=r=>r.goal&&r.yl!=null&&r.yl<=5; let inn=os.filter(r=>!exm(r)); const ex=os.filter(exm);
  if(period){inn=os;odb=os.filter(r=>r.passAtt)}
  const prod={scrimPlays:n,yards,ypp:r1(sdiv(yd(inn),inn.length),3),yppExcludedPlays:ex.length,epa:r1(epa,1),epaPlay:r1(sdiv(epa,n),3),
    passYds:yd(odb),passYpp:r1(sdiv(yd(odb),odb.length),3),dbEpa:r1(ep(odb),1),dbEpaPlay:r1(sdiv(ep(odb),odb.length),3),scrambles:os.filter(r=>r.scramble).length,
    passEpa:r1(ep(opa),1),passEpaPlay:r1(sdiv(ep(opa),opa.length),3),rushYds:yd(orush),rushYpp:r1(sdiv(yd(orush),orush.length),3),rushEpa:r1(ep(orush),1),rushEpaPlay:r1(sdiv(ep(orush),orush.length),3)};
  const ra=orush.length; const power=orush.filter(r=>r.ydstogo<=2&&(r.down===3||r.down===4)); const pconv=power.filter(r=>r.conv).length;
  const oppRuns=orush.filter(r=>r.yds>=4); const ly=sum(orush,r=>lineYards(r.yds)); const hy=sum(oppRuns,r=>r.yds-lineYards(r.yds));
  const offs=orush.filter(r=>r.down>0&&!r.twoPt&&!r.conv&&(r.down===1?r.yds<4:r.yds<3)).length;
  const rush={scrimPlays:n,rushAtt:ra,rushShare:sdiv(100*ra,n),powerAtt:power.length,powerRate:r1(sdiv(100*pconv,power.length)),
    stuffedRuns:orush.filter(r=>r.yds<=0).length,stuffRate:r1(sdiv(100*orush.filter(r=>r.yds<=0).length,ra)),stoppedRuns:orush.filter(r=>r.yds<=2).length,stoppedRate:r1(sdiv(100*orush.filter(r=>r.yds<=2).length,ra)),
    opportunityRuns:oppRuns.length,opportunityRate:r1(sdiv(100*oppRuns.length,ra)),lineYardsTotal:r1(ly,1),lineYardsPerCarry:r1(sdiv(ly,ra),3),
    highlightYardsTotal:r1(hy,1),highlightYardsPerOpp:r1(sdiv(hy,oppRuns.length),3),offSchedAtt:ra,offSchedRuns:offs,offSchedRate:r1(sdiv(100*offs,ra))};
  const ne=os.filter(r=>!r.expl);
  const allPlays=o.filter(r=>!/^timeout/i.test(r.text));
  const expl={playsTotal:allPlays.length,scrimPlays:n,explosivePlays:os.filter(r=>r.expl).length,explPass:os.filter(r=>r.explP).length,explRush:os.filter(r=>r.explR).length,
    nonExplEpaPlay:r1(sdiv(ep(ne),ne.length),3),nonExplPassEpaPlay:r1(sdiv(ep(ne.filter(r=>r.passAtt)),ne.filter(r=>r.passAtt).length),3),nonExplRushEpaPlay:r1(sdiv(ep(ne.filter(r=>r.is_rush)),ne.filter(r=>r.is_rush).length),3),
    bigPlays:os.filter(r=>r.yds>=20).map(r=>({q:r.qtr,c:r.clock,y:r.yds,k:r.is_rush?'Rush':'Pass',td:!!(r.td&&r.tdTeam===r.pos),t:r.text}))};
  const e=os.filter(r=>r.down===1||r.down===2), l=os.filter(r=>r.down===3||r.down===4);
  const win=x=>x.filter(r=>(r.qtr===2&&r.qsec<=240)||(r.qtr===3&&r.qsec>=660));
  const m8=win(os), m8all=win(allPlays);
  const sr=x=>r1(sdiv(100*x.filter(r=>r.succ).length,x.length));
  const P=x=>x.filter(r=>r.passAtt), R=x=>x.filter(r=>r.is_rush);
  const pdn=r=>!(r.down>0)||(r.down===2&&r.ydstogo>=9)||((r.down===3||r.down===4)&&r.ydstogo>=5);
  const ePass=P(e).length,eRush=R(e).length,ePSR=sr(P(e)),eRSR=sr(R(e));
  const earlySR=(ePass+eRush)?((ePSR||0)*ePass+(eRSR||0)*eRush)/(ePass+eRush):null;
  const sit={successPlays:o.filter(r=>r.succ).length,successPlaysRate:sr(os),successPassRate:sr(P(os)),successRushRate:sr(R(os)),
    stdDownPlays:os.filter(r=>!pdn(r)).length,passDownPlays:os.filter(pdn).length,earlyDownFirstDowns:e.filter(r=>r.conv).length,
    earlyEpa:r1(ep(e)),earlyEpaPlay:r1(sdiv(ep(e),e.length),3),earlyPass:ePass,earlyRush:eRush,earlyPassSuccessRate:ePSR,earlyRushSuccessRate:eRSR,
    lateEpa:r1(ep(l)),lateEpaPlay:r1(sdiv(ep(l),l.length),3),latePass:P(l).length,lateRush:R(l).length,latePassSuccessRate:sr(P(l)),lateRushSuccessRate:sr(R(l)),
    avgDist3rd:os.some(r=>r.down===3)?r1(sdiv(sum(os.filter(r=>r.down===3),r=>r.ydstogo),os.filter(r=>r.down===3).length)):null,
    mid8Epa:r1(ep(m8all)),mid8EpaPlay:r1(sdiv(ep(m8all),m8all.length),3),mid8Pass:P(m8).length,mid8Rush:R(m8).length,mid8PassSuccessRate:sr(P(m8)),mid8RushSuccessRate:sr(R(m8)),
    earlySuccessRate:r1(earlySR)};
  const tdr=drives.filter(x=>x._tm===T_&&x._scrim>0), odr=drives.filter(x=>x._tm===O_&&x._scrim>0);
  const av=tdr.filter(x=>x.spot1!=null&&(period?x.spot1>9:100-x.spot1>5));
  let depa=sum(tdr,x=>x._epa), depaO=sum(odr,x=>x._epa); if(period){depa=epa;depaO=ep(ds)}
  const wsp=tdr.filter(x=>x.spot1!=null);
  const drv={total:tdr.length,avgStartFP:r1(sdiv(sum(wsp,x=>x.spot1),wsp.length)),playsPerDrive:sdiv(n,tdr.length),yardsPerDrive:sdiv(yards,tdr.length),
    availYardsPct:r1(sdiv(100*sum(av,x=>x.yards/(100-x.spot1)),av.length)),epaPerDrive:r1(sdiv(depa,tdr.length),2)};
  const POINTS=new Set(['Touchdown','Field goal','Opp touchdown','Safety']);
  const stops=odr.filter(x=>!POINTS.has(x._fdr));
  const hpm=r=>r.passAtt&&(r.sack||r.int||r.pd||r.forced), hrm=r=>r.is_rush&&(r.yds<=0||r.forced);
  const hp=ds.filter(hpm).length, hr=ds.filter(hrm).length;
  const ffo=d.filter(r=>r.forced&&!(r.is_scrim&&(hpm(r)||hrm(r)))).length, ffs=ds.filter(r=>r.forced&&!(hpm(r)||hrm(r))).length;
  const dfn={scrimPlays:ds.length,stopRate:r1(sdiv(100*stops.length,odr.length)),havocPlays:hp+hr+ffo,havocRate:r1(sdiv(100*(hp+hr+ffs),ds.length)),
    havocPass:hp,havocRush:hr,tflRush:drush.filter(r=>r.yds<0).length,sacks:ddb.filter(r=>r.sack).length,pbu:d.filter(r=>r.pd).length,ints:d.filter(r=>r.int).length,ff:d.filter(r=>r.forced).length,
    epaPerDriveAllowed:r1(sdiv(depaO,odr.length),2)};
  const gi=rowsIn.filter(r=>r.int&&r.pos===T_).length, gf=rowsIn.filter(r=>r.fumLost&&r.fumTeam===T_).length;
  const ti=rowsIn.filter(r=>r.int&&r.pos===O_).length, tf=rowsIn.filter(r=>r.fumLost&&r.fumTeam===O_).length;
  const fev=rowsIn.filter(r=>r.fumble&&r.fumTeam===T_).length;
  const tov={giveaways:gi+gf,takeaways:ti+tf,fumbleEvents:fev,fumblesLost:gf,fumblesOwnRecov:fev-gf,ints:gi,margin:(ti+tf)-(gi+gf)};
  const t3=os.filter(r=>r.down===3), t4=os.filter(r=>r.down===4); const c3=t3.filter(r=>r.conv).length, c4=t4.filter(r=>r.conv).length;
  const ser=t=>G.series.filter(s=>s.team===t&&!['QB kneel','End of half'].includes(s.res)&&!(s.res==='Opp touchdown'&&!s.rows.some(r=>r.is_scrim))&&(!ps||ps.includes(s.q)));
  const so=ser(T_), sd=ser(O_); const sc=so.filter(s=>s.succ).length, scd=sd.filter(s=>s.succ).length;
  const conv={thirdConv:c3,thirdAtt:t3.length,thirdRate:r1(sdiv(100*c3,t3.length)),fourthConv:c4,fourthAtt:t4.length,fourthRate:r1(sdiv(100*c4,t4.length)),
    seriesConv:sc,series:so.length,seriesRate:r1(sdiv(100*sc,so.length)),seriesConvAllowed:scd,seriesAllowed:sd.length,seriesRateAllowed:r1(sdiv(100*scd,sd.length))};
  const opps=dd=>{const tr=dd.filter(x=>x.opp30);const pts=sum(tr,x=>x._pts);return[tr,pts,tr.filter(x=>x.result==='Touchdown').length,tr.filter(x=>x.result==='Field Goal').length]};
  const [tr,pts,tds,fgs]=opps(tdr),[tra,ptsa,tdsa,fgsa]=opps(odr);
  const oppd={trips:tr.length,points:pts,ppo:r1(sdiv(pts,tr.length),2),tds,fgs,busts:tr.filter(x=>x._pts===0).length,
    tripsAllowed:tra.length,pointsAllowed:ptsa,ppoAllowed:r1(sdiv(ptsa,tra.length),2),tdsAllowed:tdsa,fgsAllowed:fgsa,stopsInside30:tra.filter(x=>x._pts===0).length};
  const rz=tdr.filter(x=>x._rz); let rzv=sdiv(100*rz.filter(x=>x._rztd).length,rz.length);
  if(period){const rzr=rowsIn.filter(r=>r.is_scrim&&!r.twoPt&&r.yl!=null&&r.yl<=20);const dis=new Set(rzr.map(r=>r.di));
    const dset=G.dchart.filter(x=>x._tm===T_&&dis.has(x._di));const tdd=new Set(rowsIn.filter(r=>r.is_scrim&&!r.twoPt&&r.yl<=20&&r.td).map(r=>r.di));
    rzv=sdiv(100*dset.filter(x=>tdd.has(x._di)).length,dset.length)}
  const ov={epaPlay:prod.epaPlay,successRate:sdiv(100*os.filter(r=>r.succ).length,n),earlySuccessRate:earlySR,ypp:prod.ypp,passEpaPlay:prod.passEpaPlay,dbEpaPlay:prod.dbEpaPlay,
    rushEpaPlay:prod.rushEpaPlay,passYpp:prod.passYpp,explosiveRate:sdiv(100*os.filter(r=>r.expl).length,n),thirdRate:sdiv(100*c3,t3.length),
    seriesRate:sdiv(100*sc,so.length),seriesRateAllowed:sdiv(100*scd,sd.length),rzRate:rzv,
    stuffRate_def:sdiv(100*drush.filter(r=>r.yds<=0).length,drush.length),havocRate_def:sdiv(100*(hp+hr+ffs),ds.length),
    epaPerDrive:sdiv(depa,tdr.length),epaPerDriveAllowed:sdiv(depaO,odr.length)};
  const overall={};for(const k in ov)overall[k]={value:r1(ov[k],3),_raw:ov[k]};
  return {overall,production:prod,rushing:rush,explosiveness:expl,situational:sit,drives:drv,defensive:dfn,turnovers:tov,conversions:conv,opportunities:oppd};
}
function addPct(bx,split){const P=MODEL.pools[split]||{};for(const k in bx.overall){const v=bx.overall[k];const raw=v._raw;delete v._raw;const arr=P[k];
  if(raw==null||!arr||!arr.length){v.pct=null;continue}let lo=0,hi=arr.length;const x=raw+1e-9;while(lo<hi){const m=(lo+hi)>>1;if(arr[m]<=x)lo=m+1;else hi=m}v.pct=r1(100*lo/arr.length,1)}}
const SPLITS={q1:[1],q2:[2],q3:[3],q4:[4],h1:[1,2],h2:[3,4],thru3:[1,2,3]};

/* ---------- public: summary -> dashboard-style record ---------- */
function build(summary){
  if(!MODEL)throw new Error('model not loaded');
  const G=parse(summary); finish(G);
  const H=G.home,A=G.away, rec={};
  const hs=+(G.hc.competitors.find(c=>c.homeAway==='home').score||0), as=+(G.hc.competitors.find(c=>c.homeAway==='away').score||0);
  for(const [t,o] of [[H,A],[A,H]]){
    const full=teamBox(G,G.rows,t,o,G.dchart,false,null); addPct(full,'full');
    const ts=t===H?hs:as, os=t===H?as:hs;
    const bx={meta:{opp:G.T[o].name,week:summary.header?.week??null,home:t===H,result:ts>os?'W':ts<os?'L':'T',ts,os}, ...full, periods:{}};
    for(const [k,ps] of Object.entries(SPLITS)){
      const rows=G.rows.filter(r=>ps.includes(r.qtr)); if(!rows.some(r=>r.is_scrim))continue;
      const ds=G.dchart.filter(x=>ps.includes(x.q1));
      const b=teamBox(G,rows,t,o,ds,true,ps); addPct(b,k);
      if(b.opportunities.trips===0&&b.opportunities.tripsAllowed===0)b.opportunities=null;
      bx.periods[k]=b;
    }
    rec[G.T[t].name]=bx;
  }
  rec.driveChart=G.dchart.map(x=>{const y={};for(const k in x)if(k[0]!=='_')y[k]=x[k];return y});
  rec._rows=G.rows; rec._home=G.T[H].name; rec._away=G.T[A].name;
  return rec;
}
root.NFLLiveBox={setModel,build,EP:(a,b,c)=>EP(a,b,c)};
})(typeof window!=='undefined'?window:globalThis);
