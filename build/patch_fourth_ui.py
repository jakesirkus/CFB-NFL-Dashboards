"""Drive chart: '4th ✓' badge on any drive with a converted 4th down (user request, Nov 8 2026). Computed in the page from each drive's
playList, so it covers every week of CFB and NFL with no data rebuild.  A 4th-down snap counts as converted when it is not a punt /
field goal / kneel and (a) the drive's next snap is a 1st down, or (b) it scored a touchdown, or (c) the parsed gain reached the
distance with no interception / lost fumble (drive's last play, e.g. end of half). Failed 4th downs already show as Downs.
Idempotent.  usage: patch_fourth_ui.py PAGE.html [PAGE.html ...]"""
import sys
A_ROW = "      var oppBadge = d.opp30 ? '<span class=\"dc-opp30-badge\" title=\"Scoring opportunity: offense ran a play inside the opponent 30\">OPP</span>' : '';"
N_ROW = A_ROW + "\n      var nConv4 = dcFourthConv(d); if(nConv4) oppBadge += '<span class=\"dc-4th-badge\" title=\"Converted '+nConv4+' fourth down'+(nConv4>1?'s':'')+' on this drive\">4th ✓'+(nConv4>1?'×'+nConv4:'')+'</span>';"
A_FN = "  function buildDriveChart("
FN = r'''  function dcFourthConv(d){              // number of converted 4th downs in a drive (see patch_fourth_ui.py)
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
'''
CSS = "\n  .dc-row{ grid-template-columns:minmax(150px,230px) 64px 48px 64px 76px 54px 48px 56px; min-width:560px; }\n  .dc-team{ flex-wrap:wrap; white-space:normal; row-gap:2px; overflow:visible; }\n  .dc-team .dc-opp30-badge, .dc-team .dc-4th-badge{ margin-left:0; }\n  .dc-4th-badge{ display:inline-block; font-size:8px; font-weight:700; letter-spacing:0.03em; color:var(--good); border:1px solid var(--good); border-radius:4px; padding:1px 4px; margin-left:5px; vertical-align:middle; white-space:nowrap; }\n"
A_NOTE = "Rows outlined and tinted with an <span class=\"dc-opp30-badge\" style=\"margin-left:0;\">OPP</span> badge are scoring opportunities (offense ran a play inside the opponent 30)."
N_NOTE = A_NOTE + " A <span class=\"dc-4th-badge\" style=\"margin-left:0;\">4th ✓</span> badge marks a drive that converted a 4th down."
for p in sys.argv[1:]:
    s = open(p).read()
    if 'function dcFourthConv(' in s: print(p, 'already patched'); continue
    for a, nm in ((A_ROW, 'row'), (A_FN, 'fn'), (A_NOTE, 'note')): assert s.count(a) == 1, (p, nm, s.count(a))
    s = s.replace(A_ROW, N_ROW).replace(A_FN, FN + A_FN).replace(A_NOTE, N_NOTE)
    i = s.index('</style>', s.index('.dc-opp30-badge{')); s = s[:i] + CSS + s[i:]
    open(p, 'w').write(s); print(p, 'patched')
