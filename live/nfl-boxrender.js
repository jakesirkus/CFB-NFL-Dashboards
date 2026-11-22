/* Box-score rendering functions copied VERBATIM from new/nfl/index.html (build*Section, buildDriveChart and helpers)
   so the live box looks identical to the dashboard's. The dashboard itself is not modified.
   Only wrapper added: exposes the functions as window.NFLBoxRender. */
(function(){

  function bn(v,d){ d=d===undefined?1:d; return (v===null||v===undefined||isNaN(v)) ? '—' : Number(v).toFixed(d); }
  function bp(v,d){ d=d===undefined?1:d; return (v===null||v===undefined||isNaN(v)) ? '—' : Number(v).toFixed(d)+'%'; }
  function bi(v){ return (v===null||v===undefined||isNaN(v)) ? '—' : Math.round(v); }
  function bsig(v,d){ d=d===undefined?1:d; if(v===null||v===undefined||isNaN(v)) return '—'; return (v>0?'+':'')+Number(v).toFixed(d); }
  function heatBg(pctVal, colorVar){
    if(pctVal===null||pctVal===undefined) return '';
    var a = Math.round(8 + pctVal*0.55);
    return 'background:color-mix(in srgb, var('+colorVar+') '+a+'%, var(--surface));';
  }
  function bsRow(label, v1, v2, indent){
    return '<tr'+(indent?' class="bs-indent"':'')+'><td>'+label+'</td><td>'+v1+'</td><td>'+v2+'</td></tr>';
  }
  function bsHeatRow(label, o1, o2, colorVar, dec){
    dec = dec===undefined ? 3 : dec;
    var v1 = o1 && o1.value!==null && o1.value!==undefined ? bn(o1.value,dec)+(dec===1?'%':'') : '—';
    var v2 = o2 && o2.value!==null && o2.value!==undefined ? bn(o2.value,dec)+(dec===1?'%':'') : '—';
    var s1 = heatBg(o1?o1.pct:null, colorVar), s2 = heatBg(o2?o2.pct:null, colorVar);
    var p1 = (o1&&o1.pct!==null) ? '<span class="bs-pct">'+Math.round(o1.pct)+'p</span>' : '';
    var p2 = (o2&&o2.pct!==null) ? '<span class="bs-pct">'+Math.round(o2.pct)+'p</span>' : '';
    return '<tr><td>'+label+'</td><td class="bs-heat" style="'+s1+'">'+v1+p1+'</td><td class="bs-heat" style="'+s2+'">'+v2+p2+'</td></tr>';
  }
  function bsTable(title, rowsHtml){
    return '<table class="bs-table"><thead><tr><th></th><th>'+title.t1+'</th><th>'+title.t2+'</th></tr></thead><tbody>'+rowsHtml+'</tbody></table>';
  }

  function buildOverallSection(a, b, heads){
    var OVR = [
      ['epaPlay','EPA/Play', 'off'], ['successRate','Success Rate','off'], ['earlySuccessRate','Early Down Success Rate','off'], ['ypp','Yards/Play*','off'],
      ['passEpaPlay','EPA/Pass (no scrambles)','off'], ['dbEpaPlay','EPA/Dropback (incl. scrambles)','off'], ['rushEpaPlay','EPA/Rush','off'], ['passYpp','Yards/Dropback','off'],
      ['explosiveRate','Explosive Play Rate','off'], ['thirdRate','3rd Down Conversion Rate','off'],
      ['seriesRate','Series Conversion Rate','off'], ['seriesRateAllowed','Series Conv. Rate Allowed','def'],
      ['rzRate','Red Zone Success Rate','off'], ['stuffRate_def','Def Run Stuff Rate','def'], ['havocRate_def','Havoc Rate','def'],
      ['epaPerDrive','EPA/Drive','off'], ['epaPerDriveAllowed','EPA/Drive Allowed','def']
    ];
    var PCT_ROWS = {thirdRate:1, seriesRate:1, seriesRateAllowed:1};
    var rows = OVR.map(function(m){ return bsHeatRow(m[1], a.overall[m[0]], b.overall[m[0]], m[2]==='off'?'--off':'--def', PCT_ROWS[m[0]]?1:undefined); }).join('');
    return '<div class="bs-section"><div class="bs-section-title">Overall</div>'+bsTable(heads, rows)+'</div>';
  }

  function buildProductionSection(a, b, heads){
    var p1=a.production, p2=b.production;
    var rows = bsRow('Scrimmage Plays', bi(p1.scrimPlays), bi(p2.scrimPlays))
      + bsRow('Yards', bi(p1.yards), bi(p2.yards)) + bsRow('Yards/Play*', bn(p1.ypp,2), bn(p2.ypp,2))
      + bsRow('Snaps at/inside opp 5 (left out of Y/P)', bi(p1.yppExcludedPlays), bi(p2.yppExcludedPlays), true)
      + bsRow('EPA', bn(p1.epa,1), bn(p2.epa,1)) + bsRow('EPA/Play', bn(p1.epaPlay,3), bn(p2.epaPlay,3))
      + '<tr><td colspan="3" class="bs-subhead">Dropbacks (passes, sacks &amp; scrambles)</td></tr>'
      + bsRow('Yards', bi(p1.passYds), bi(p2.passYds), true) + bsRow('Yards/Dropback', bn(p1.passYpp,2), bn(p2.passYpp,2), true)
      + bsRow('EPA', bn(p1.dbEpa,1), bn(p2.dbEpa,1), true) + bsRow('EPA/Dropback', bn(p1.dbEpaPlay,3), bn(p2.dbEpaPlay,3), true)
      + bsRow('Scrambles', bi(p1.scrambles), bi(p2.scrambles), true)
      + '<tr><td colspan="3" class="bs-subhead">Passes only (passes &amp; sacks, no scrambles)</td></tr>'
      + bsRow('EPA', bn(p1.passEpa,1), bn(p2.passEpa,1), true) + bsRow('EPA/Pass', bn(p1.passEpaPlay,3), bn(p2.passEpaPlay,3), true)
      + '<tr><td colspan="3" class="bs-subhead">Rushes</td></tr>'
      + bsRow('Yards', bi(p1.rushYds), bi(p2.rushYds), true) + bsRow('Yards/Play', bn(p1.rushYpp,2), bn(p2.rushYpp,2), true)
      + bsRow('EPA', bn(p1.rushEpa,1), bn(p2.rushEpa,1), true) + bsRow('EPA/Play', bn(p1.rushEpaPlay,3), bn(p2.rushEpaPlay,3), true);
    return '<div class="bs-section"><div class="bs-section-title">Production</div>'+bsTable(heads, rows)+'</div>';
  }

  function buildRushingSection(a, b, heads){
    var r1=a.rushing, r2=b.rushing;
    var rows = bsRow('Scrimmage Plays', bi(r1.scrimPlays), bi(r2.scrimPlays))
      + bsRow('Rushes', bi(r1.rushAtt)+' ('+bn(r1.rushShare,0)+'%)', bi(r2.rushAtt)+' ('+bn(r2.rushShare,0)+'%)')
      + bsRow('Power Run Att. (Down≥3, Dist≤2)', bi(r1.powerAtt), bi(r2.powerAtt))
      + bsRow('Successful Power Runs (Rate)', bp(r1.powerRate), bp(r2.powerRate), true)
      + bsRow('Stuffed Runs (Yds≤0)', bi(r1.stuffedRuns)+' ('+bn(r1.stuffRate,0)+'%)', bi(r2.stuffedRuns)+' ('+bn(r2.stuffRate,0)+'%)')
      + bsRow('Stopped Runs (Yds≤2)', bi(r1.stoppedRuns)+' ('+bn(r1.stoppedRate,0)+'%)', bi(r2.stoppedRuns)+' ('+bn(r2.stoppedRate,0)+'%)')
      + bsRow('Opportunity Runs (Yds≥4)', bi(r1.opportunityRuns)+' ('+bn(r1.opportunityRate,0)+'%)', bi(r2.opportunityRuns)+' ('+bn(r2.opportunityRate,0)+'%)')
      + bsRow('Off-Schedule Runs', r1.offSchedRuns==null?'—':bi(r1.offSchedRuns)+' ('+bn(r1.offSchedRate,0)+'%)', r2.offSchedRuns==null?'—':bi(r2.offSchedRuns)+' ('+bn(r2.offSchedRate,0)+'%)')
      + bsRow('OL Line Yards*', bn(r1.lineYardsTotal,1), bn(r2.lineYardsTotal,1))
      + bsRow('Per Carry', bn(r1.lineYardsPerCarry,2), bn(r2.lineYardsPerCarry,2), true)
      + bsRow('Highlight Yards*', bn(r1.highlightYardsTotal,1), bn(r2.highlightYardsTotal,1))
      + bsRow('Per Rush Opportunity', bn(r1.highlightYardsPerOpp,2), bn(r2.highlightYardsPerOpp,2), true);
    return '<div class="bs-section"><div class="bs-section-title">Rushing</div>'+bsTable(heads, rows)+'</div>';
  }

  function bpEsc(x){ return String(x).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function bpCell(e, min, kind){           // count of plays >= min yards (kind: 'pass' = pass+scramble, 'Rush'), with a hover list
    if(!e || !e.bigPlays) return '\u2014';
    var L = e.bigPlays.filter(function(p){ return p.y>=min && (!kind || (kind==='pass' ? p.k!=='Rush' : p.k===kind)); });
    if(!L.length) return '0';
    var items = L.map(function(p){
      return '<div class="bp-item"><div class="bp-h"><b>'+p.y+' yds</b> \u00b7 '+p.k+(p.td?' \u00b7 <span class="bp-td">TD</span>':'')+'<span class="bp-when">Q'+p.q+' '+bpEsc(p.c)+'</span></div><div class="bp-t">'+bpEsc(p.t)+'</div></div>';
    }).join('');
    return '<span class="bp-cnt" tabindex="0">'+L.length+'<span class="bp-pop">'+items+'</span></span>';
  }
  function buildExplosivenessSection(a, b, heads){
    var e1=a.explosiveness, e2=b.explosiveness;
    var rows = bsRow('Total Plays', bi(e1.playsTotal), bi(e2.playsTotal))
      + bsRow('Scrimmage Plays', bi(e1.scrimPlays), bi(e2.scrimPlays))
      + bsRow('Explosive Plays (10+ run / 15+ pass)', bi(e1.explosivePlays), bi(e2.explosivePlays))
      + bsRow('When Passing', bi(e1.explPass), bi(e2.explPass), true)
      + bsRow('When Rushing', bi(e1.explRush), bi(e2.explRush), true)
      + '<tr><td colspan="3" class="bs-subhead">Big Plays <span style="font-weight:400">(hover or tap a count to see the plays)</span></td></tr>'
      + bsRow('20+ Yard Plays', bpCell(e1,20), bpCell(e2,20))
      + bsRow('30+ Yard Plays', bpCell(e1,30), bpCell(e2,30))
      + bsRow('40+ Yard Plays', bpCell(e1,40), bpCell(e2,40))
      + bsRow('When Passing', bpCell(e1,40,'pass'), bpCell(e2,40,'pass'), true)
      + bsRow('When Rushing', bpCell(e1,40,'Rush'), bpCell(e2,40,'Rush'), true)
      + '<tr><td colspan="3" class="bs-subhead">EPA w/o Explosive Plays</td></tr>'
      + bsRow('EPA/Play', bn(e1.nonExplEpaPlay,3), bn(e2.nonExplEpaPlay,3), true)
      + bsRow('When Passing', bn(e1.nonExplPassEpaPlay,3), bn(e2.nonExplPassEpaPlay,3), true)
      + bsRow('When Rushing', bn(e1.nonExplRushEpaPlay,3), bn(e2.nonExplRushEpaPlay,3), true);
    return '<div class="bs-section"><div class="bs-section-title">Explosiveness</div>'+bsTable(heads, rows)+'</div>';
  }

  function buildSituationalSection(a, b, heads){
    var s1=a.situational, s2=b.situational;
    var rows = bsRow('Successful Plays (EPA>0)', bi(s1.successPlays)+' ('+bn(s1.successPlaysRate,0)+'%)', bi(s2.successPlays)+' ('+bn(s2.successPlaysRate,0)+'%)')
      + bsRow('When Passing', bp(s1.successPassRate), bp(s2.successPassRate), true)
      + bsRow('When Rushing', bp(s1.successRushRate), bp(s2.successRushRate), true)
      + bsRow('On Standard Downs', bi(s1.stdDownPlays), bi(s2.stdDownPlays), true)
      + bsRow('On Passing Downs', bi(s1.passDownPlays), bi(s2.passDownPlays), true)
      + '<tr><td colspan="3" class="bs-subhead">Early Downs (1st &amp; 2nd)</td></tr>'
      + bsRow('First Downs Created', bi(s1.earlyDownFirstDowns), bi(s2.earlyDownFirstDowns), true)
      + bsRow('EPA/Play', bn(s1.earlyEpaPlay,3), bn(s2.earlyEpaPlay,3), true)
      + bsRow('Success Rate', bp(s1.earlySuccessRate), bp(s2.earlySuccessRate), true)
      + bsRow('Passes / Rushes', bi(s1.earlyPass)+' / '+bi(s1.earlyRush), bi(s2.earlyPass)+' / '+bi(s2.earlyRush), true)
      + bsRow('Successful Pass / Rush Rate', bp(s1.earlyPassSuccessRate)+' / '+bp(s1.earlyRushSuccessRate), bp(s2.earlyPassSuccessRate)+' / '+bp(s2.earlyRushSuccessRate), true)
      + '<tr><td colspan="3" class="bs-subhead">Late Downs (3rd &amp; 4th)</td></tr>'
      + bsRow('EPA/Play', bn(s1.lateEpaPlay,3), bn(s2.lateEpaPlay,3), true)
      + bsRow('Passes / Rushes', bi(s1.latePass)+' / '+bi(s1.lateRush), bi(s2.latePass)+' / '+bi(s2.lateRush), true)
      + bsRow('Successful Pass / Rush Rate', bp(s1.latePassSuccessRate)+' / '+bp(s1.lateRushSuccessRate), bp(s2.latePassSuccessRate)+' / '+bp(s2.lateRushSuccessRate), true)
      + bsRow('Avg Distance', bn(s1.avgDist3rd,1), bn(s2.avgDist3rd,1), true)
      + '<tr><td colspan="3" class="bs-subhead">"Middle 8" Plays</td></tr>'
      + bsRow('EPA/Play', bn(s1.mid8EpaPlay,3), bn(s2.mid8EpaPlay,3), true)
      + bsRow('Passes / Rushes', bi(s1.mid8Pass)+' / '+bi(s1.mid8Rush), bi(s2.mid8Pass)+' / '+bi(s2.mid8Rush), true)
      + bsRow('Successful Pass / Rush Rate', bp(s1.mid8PassSuccessRate)+' / '+bp(s1.mid8RushSuccessRate), bp(s2.mid8PassSuccessRate)+' / '+bp(s2.mid8RushSuccessRate), true);
    return '<div class="bs-section"><div class="bs-section-title">Situational</div>'+bsTable(heads, rows)+'</div>';
  }

  function convCell(c, a, r){
    if(a===null||a===undefined) return '—';
    if(!a) return '0/0';
    return '<span class="bs-frac">'+c+'/'+a+'</span> ('+bn(r,0)+'%)';
  }
  function buildDownsSection(a, b, heads){
    var c1=a.conversions, c2=b.conversions;
    if(!c1 || !c2) return '';
    var rows = bsRow('3rd Down', convCell(c1.thirdConv,c1.thirdAtt,c1.thirdRate), convCell(c2.thirdConv,c2.thirdAtt,c2.thirdRate))
      + bsRow('4th Down', convCell(c1.fourthConv,c1.fourthAtt,c1.fourthRate), convCell(c2.fourthConv,c2.fourthAtt,c2.fourthRate))
      + '<tr><td colspan="3" class="bs-subhead">Series Conversion</td></tr>'
      + bsRow('Offense', convCell(c1.seriesConv,c1.series,c1.seriesRate), convCell(c2.seriesConv,c2.series,c2.seriesRate), true)
      + bsRow('Defense (allowed)', convCell(c1.seriesConvAllowed,c1.seriesAllowed,c1.seriesRateAllowed), convCell(c2.seriesConvAllowed,c2.seriesAllowed,c2.seriesRateAllowed), true);
    return '<div class="bs-section"><div class="bs-section-title">Downs &amp; Series</div>'+bsTable(heads, rows)+'</div>'
      + '<div class="bs-section-note">3rd/4th downs are counted like the official box score: a snap wiped out by an accepted penalty ("No Play") isn\'t an attempt, and punts, field goals and kneel-downs on 4th down aren\'t "go-for-it" attempts. A series starts with each new 1st down; it counts as converted if it produces another 1st down (including by penalty) or an offensive TD. Series cut off by the end of a half or game are left out. In a quarter/half window, a series belongs to the quarter it started in.</div>';
  }

  function buildDrivesSection(a, b, heads){
    var d1=a.drives, d2=b.drives;
    var rows = bsRow('Total', bi(d1.total), bi(d2.total))
      + bsRow('Avg Starting Field Position', 'Own '+bn(d1.avgStartFP,0), 'Own '+bn(d2.avgStartFP,0))
      + bsRow('Plays/Drive', bn(d1.playsPerDrive,2), bn(d2.playsPerDrive,2))
      + bsRow('Yards/Drive', bn(d1.yardsPerDrive,2), bn(d2.yardsPerDrive,2))
      + bsRow('EPA/Drive', bn(d1.epaPerDrive,2), bn(d2.epaPerDrive,2))
      + bsRow('Available Yards %*', bp(d1.availYardsPct), bp(d2.availYardsPct));
    return '<div class="bs-section"><div class="bs-section-title">Drives</div>'+bsTable(heads, rows)+'</div>';
  }

  function buildDefensiveSection(a, b, heads){
    var d1=a.defensive, d2=b.defensive;
    var rows = bsRow('Scrimmage Plays Faced', bi(d1.scrimPlays), bi(d2.scrimPlays))
      + bsRow('Stop Rate', bp(d1.stopRate), bp(d2.stopRate))
      + bsRow('EPA/Drive Allowed', bn(d1.epaPerDriveAllowed,2), bn(d2.epaPerDriveAllowed,2))
      + bsRow('Havoc Plays Created*', bi(d1.havocPlays)+' ('+bn(d1.havocRate,0)+'%)', bi(d2.havocPlays)+' ('+bn(d2.havocRate,0)+'%)')
      + bsRow('Passing', bi(d1.havocPass), bi(d2.havocPass), true)
      + bsRow('Rushing', bi(d1.havocRush), bi(d2.havocRush), true)
      + bsRow('TFLs (Rushing)*', bi(d1.tflRush), bi(d2.tflRush))
      + bsRow('Sacks Generated', bi(d1.sacks), bi(d2.sacks))
      + bsRow('Passes Defensed*', bi(d1.pbu), bi(d2.pbu))
      + bsRow('Interceptions', bi(d1.ints), bi(d2.ints))
      + bsRow('Fumbles Forced*', bi(d1.ff), bi(d2.ff));
    return '<div class="bs-section"><div class="bs-section-title">Defensive</div>'+bsTable(heads, rows)+'</div>';
  }

  function buildTurnoversSection(a, b, heads){
    var t1=a.turnovers, t2=b.turnovers;
    var rows = bsRow('Turnovers', bi(t1.giveaways), bi(t2.giveaways))
      + bsRow('Fumbles', bi(t1.fumbleEvents), bi(t2.fumbleEvents))
      + bsRow('Fumbles Lost', bi(t1.fumblesLost), bi(t2.fumblesLost))
      + bsRow('Fumbles Recovered (Own)', bi(t1.fumblesOwnRecov), bi(t2.fumblesOwnRecov))
      + bsRow('Interceptions Thrown', bi(t1.ints), bi(t2.ints))
      + bsRow('Turnover Margin', bsig(t1.margin,0), bsig(t2.margin,0));
    return '<div class="bs-section"><div class="bs-section-title">Turnovers</div>'+bsTable(heads, rows)+'</div>';
  }

  function buildOpportunitiesSection(a, b, heads){
    var o1=a.opportunities, o2=b.opportunities;
    if(!o1 && !o2) return '';
    o1 = o1 || {}; o2 = o2 || {};
    var rows = bsRow('Trips Inside Opp 30*', bi(o1.trips), bi(o2.trips))
      + bsRow('Points on Those Trips', bi(o1.points), bi(o2.points))
      + bsRow('Points / Opportunity', bn(o1.ppo,2), bn(o2.ppo,2))
      + bsRow('Touchdowns', bi(o1.tds), bi(o2.tds), true)
      + bsRow('Field Goals', bi(o1.fgs), bi(o2.fgs), true)
      + bsRow('No Points (Busted)', bi(o1.busts), bi(o2.busts), true)
      + '<tr><td colspan="3" class="bs-subhead">Allowed (as defense)</td></tr>'
      + bsRow('Trips Allowed', bi(o1.tripsAllowed), bi(o2.tripsAllowed), true)
      + bsRow('Points Allowed on Those Trips', bi(o1.pointsAllowed), bi(o2.pointsAllowed), true)
      + bsRow('Points Allowed / Opportunity', bn(o1.ppoAllowed,2), bn(o2.ppoAllowed,2), true)
      + bsRow('Stops Inside Own 30 (0 Pts)', bi(o1.stopsInside30), bi(o2.stopsInside30), true);
    return '<div class="bs-section"><div class="bs-section-title">Opportunities</div>'+bsTable(heads, rows)+'</div>'
      + '<div class="bs-section-note">*A "trip" (scoring opportunity) counts only if the offense ran a play with the ball at or inside the opponent 30 -- a touchdown thrown from outside the 30 doesn\'t count as a trip, since the offense never had to convert a short field. In the drive chart below, trips are highlighted and always clickable to the final play.</div>';
  }

  var DC_LABELS = {
    'Touchdown':'TD', 'Field Goal':'FG', 'Missed FG':'MISS FG', 'Blocked FG':'BLK FG',
    'Blocked FG (TD)':'BLK FG (TD)', 'Interception':'INT', 'Interception (Pick-6)':'INT (TD)',
    'Fumble':'FUMB', 'Fumble (Defensive TD)':'FUMB (TD)', 'Punt':'PUNT',
    'Punt (Return TD)':'PUNT (TD)', 'Blocked Punt':'BLK PUNT', 'Blocked Punt (TD)':'BLK PUNT (TD)',
    'Kickoff (Return TD)':'KO (TD)', 'Turnover on Downs':'DOWNS', 'Safety':'SAFETY',
    'Two-Point (Turnover)':'2PT (TD)', 'End of Half':'HALF', 'End of Game':'END',
    'End of Quarter':'END Q', 'Incomplete':'INCOMPLETE',
    'Muffed Punt':'MUFFED PUNT', 'Muffed Kickoff':'MUFFED KICK'
  };
  function escapeHtml(s){
    var d = document.createElement('div'); d.textContent = s==null?'':String(s); return d.innerHTML;
  }
  function dcSpot(spot){
    if(spot===null||spot===undefined) return '—';
    return spot<=50 ? ('Own '+spot) : ('Opp '+(100-spot));
  }
  function dcSlug(s){ return String(s).replace(/[^a-zA-Z0-9]/g,''); }
  var ORDINALS = {1:'1st', 2:'2nd', 3:'3rd', 4:'4th'};
  function ordinal(n){ return ORDINALS[n] || (n+'th'); }
  function yardline100Label(yl){
    // p.yardline100 is nflverse's own "distance to opponent's goal" convention
    // (from the play's own possession team's perspective) -- convert to the
    // same "Own X / Opp Y" spot label used for drive start/end (dcSpot),
    // which instead takes a 0-100 distance-FROM-OWN-goal.
    if(yl===null||yl===undefined) return null;
    return yl>=50 ? ('Own '+(100-yl)) : ('Opp '+yl);
  }
  function playSituationText(p){
    var loc = yardline100Label(p.yardline100);
    var dd = (p.down!=null && p.distance!=null) ? (ordinal(p.down)+' & '+(p.goalToGo?'Goal':p.distance)) : null;
    if(dd && loc) return dd+' at '+loc;
    if(dd) return dd;
    if(loc) return loc;
    return '';
  }
  function buildPlayList(d){
    var plist = d.playList || [];
    if(!plist.length){
      return d.playText ? escapeHtml(d.playText) : 'No play description available for this drive.';
    }
    return plist.map(function(p){
      var cls = 'dc-play' + (p.scoring ? ' dc-play-scoring' : '') + (p.penalty ? ' dc-play-penalty' : '');
      var badges = '';
      if(p.scoring) badges += '<span class="dc-play-scoring-badge">SCORE ●</span>';
      if(p.penalty){
        var pen = (p.penaltyTeam ? escapeHtml(p.penaltyTeam)+' ' : '') + (p.penaltyType ? escapeHtml(p.penaltyType) : 'Penalty') + (p.penaltyYards ? ' ('+p.penaltyYards+' yds)' : '');
        badges += '<span class="dc-play-penalty-badge">PENALTY: '+pen+'</span>';
      }
      var situation = playSituationText(p);
      var situationHtml = situation ? '<div class="dc-play-situation">'+escapeHtml(situation)+'</div>' : '<div class="dc-play-situation">—</div>';
      return '<div class="'+cls+'"><div class="dc-play-q">'+(p.q?('Q'+p.q):'')+'</div>'+situationHtml+'<div class="dc-play-text">'+escapeHtml(p.text)+'</div>'+badges+'</div>';
    }).join('');
  }
  function dcFourthConv(d){              // number of converted 4th downs in a drive (see patch_fourth_ui.py)
    var pl = d.playList || [], n = 0;
    for(var k=0; k<pl.length; k++){
      var p = pl[k]; if(p.down!==4) continue;
      var t = String(p.text||'');
      if(/\bpunts?\b|punt (for|is|blocked)|field goal|\bkneel/i.test(t) && !/punt formation\)/i.test(t)) continue;
      if(/punt formation\)/i.test(t) && /\bpunts\b/i.test(t)) continue;
      if(/neutral zone|offside|encroach|false start|delay of game|illegal (formation|shift|motion)|too many men|12 men/i.test(t) && /no play/i.test(t)) continue;   // pre-snap flags aren't attempts
      var nx = null; for(var j=k+1; j<pl.length; j++){ if(pl[j].down){ nx = pl[j]; break; } }
      var lost = /intercept|fumbles?.{0,80}recovered by (?!.*\bown\b)/i.test(t) && !/no play/i.test(t);
      if(nx){ if(nx.down===1 && !lost) n++; continue; }
      if(p.scoring && /touchdown/i.test(t) && !lost){ n++; continue; }
      var m = t.match(/for (-?\d+) (yards?|yds?)/i), g = m ? +m[1] : (/no gain/i.test(t) ? 0 : null);
      if(g!==null && p.distance && g>=p.distance && !lost && !/no play|incomplete/i.test(t)) n++;
    }
    return n;
  }
  function buildDriveChart(rec){
    var chart = rec.driveChart || [];
    if(!chart.length) return '';
    var teamsInChart = [];
    chart.forEach(function(d){ if(teamsInChart.indexOf(d.team)===-1) teamsInChart.push(d.team); });
    var rowsSorted = chart.slice().sort(function(a,b){ return (a.n||0)-(b.n||0); });
    var body = rowsSorted.map(function(d){
      var rid = 'dc_'+dcSlug(d.team)+'_'+d.n;
      var label = DC_LABELS[d.result] || d.result;
      var rsltCls = 'dc-rslt '+(d.color||'gray')+(d.clickable?' clickable':'');
      var rslt = '<span class="'+rsltCls+'">'+escapeHtml(label)+'</span>';
      var dotCls = teamsInChart.indexOf(d.team)===0 ? 'a' : 'b';
      var scoreHtml;
      if(d.scored && d.teamScore!==null && d.teamScore!==undefined && d.oppScore!==null && d.oppScore!==undefined){
        scoreHtml = '<div class="dc-score" title="'+escapeHtml(d.team)+' '+d.teamScore+' – '+escapeHtml(d.opponent||'Opp')+' '+d.oppScore+'">'+d.teamScore+'–'+d.oppScore+'</div>';
      } else {
        scoreHtml = '<div class="dc-score dc-score-empty">—</div>';
      }
      // Every clickable row (including any "scoring opportunity" -- a trip
      // inside the opponent 30) expands to show its final play on click,
      // whether the row's own result badge or anywhere else on the row is
      // clicked; opportunity rows are also highlighted so they stand out at
      // a glance.
      var rowCls = 'dc-row' + (d.opp30 ? ' dc-opp30' : '');
      var rowAttrs = d.clickable ? ' data-dc-target="'+rid+'" tabindex="0" role="button"' : '';
      var oppBadge = d.opp30 ? '<span class="dc-opp30-badge" title="Scoring opportunity: offense ran a play inside the opponent 30">OPP</span>' : '';
      var nConv4 = dcFourthConv(d); if(nConv4) oppBadge += '<span class="dc-4th-badge" title="Converted '+nConv4+' fourth down'+(nConv4>1?'s':'')+' on this drive">4th ✓'+(nConv4>1?'×'+nConv4:'')+'</span>';
      var row = '<div class="'+rowCls+'"'+rowAttrs+'>'
        + '<div class="dc-team"><span class="dc-team-dot '+dotCls+'"></span>'+escapeHtml(d.team)+oppBadge+'</div>'
        + '<div><div class="dc-spot">'+dcSpot(d.spot1)+'</div><div class="dc-sub">Q'+(d.q1||'—')+' · '+(d.t1||'—')+'</div></div>'
        + '<div class="dc-how">'+escapeHtml(d.how||'—')+'</div>'
        + '<div><div class="dc-spot">'+dcSpot(d.spot2)+'</div><div class="dc-sub">Q'+(d.q2||'—')+' · '+(d.t2||'—')+'</div></div>'
        + '<div>'+rslt+'</div>'
        + '<div class="dc-py">'+d.plays+'/'+d.yards+'</div>'
        + '<div class="dc-top">'+(d.top||'—')+'</div>'
        + scoreHtml
        + '</div>';
      if(d.clickable){
        row += '<div class="dc-detail" id="'+rid+'" hidden>'+buildPlayList(d)+'</div>';
      }
      return row;
    }).join('');
    var legend = teamsInChart.map(function(team, i){
      return '<div class="dc-legend-item"><span class="dc-team-dot '+(i===0?'a':'b')+'"></span>'+escapeHtml(team)+'</div>';
    }).join('');
    return '<div class="bs-drivechart"><div class="bs-drivechart-title">Drive Chart</div>'
      + '<div class="bs-drivechart-note">Drives in chronological order. Rows outlined and tinted with an <span class="dc-opp30-badge" style="margin-left:0;">OPP</span> badge are scoring opportunities (offense ran a play inside the opponent 30). A <span class="dc-4th-badge" style="margin-left:0;">4th ✓</span> badge marks a drive that converted a 4th down. Click anywhere on a row to expand the full play-by-play for that drive, with any play that actually scored (touchdown, made FG, good PAT/2pt, safety) highlighted in green and any play with a penalty flagged in red with the call and yardage. "How" is how the possession started (KO = kickoff, PUNT/INT/FUMB/DOWNS = took over after the opponent\'s possession ended that way). Spot is each team\'s own distance-from-goal (0–100). Score shows this team\'s points – opponent\'s points after each drive that scored.</div>'
      + '<div class="bs-drivechart-legend">' + legend + '</div>'
      + '<div class="dc-list"><div class="dc-row dc-head"><div>Team</div><div>Start</div><div>How</div><div>End</div><div>Result</div><div>Pl-Yds</div><div>TOP</div><div>Score</div></div>'
      + body + '</div></div>';
  }
  
  window.NFLBoxRender = {
    cols: function(a, b, heads){
      return '<div class="bs-cols">'
        + '<div style="display:flex;flex-direction:column;gap:14px;">'+buildOverallSection(a,b,heads)+buildProductionSection(a,b,heads)+buildRushingSection(a,b,heads)+'</div>'
        + '<div style="display:flex;flex-direction:column;gap:14px;">'+buildExplosivenessSection(a,b,heads)+buildSituationalSection(a,b,heads)+buildDownsSection(a,b,heads)+buildOpportunitiesSection(a,b,heads)+'</div>'
        + '<div style="display:flex;flex-direction:column;gap:14px;">'+buildDrivesSection(a,b,heads)+buildDefensiveSection(a,b,heads)+buildTurnoversSection(a,b,heads)+'</div>'
        + '</div>';
    },
    driveChart: buildDriveChart
  };
})();
