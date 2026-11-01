"""Box score Explosiveness section: 'Big Plays' block (data from add_bigplays.py).
Rows: 20+ / 30+ / 40+ yard plays (40+ split into passing / rushing). Hover (or tap) a count to see those plays:
quarter, clock, yards, pass/rush/scramble, TD, and the play text. Splits (quarters/halves) show that split's plays.
Idempotent. usage: patch_bigplays_ui.py PAGE.html [PAGE.html ...]"""
import sys
ANCHOR = "      + bsRow('When Rushing', bi(e1.explRush), bi(e2.explRush), true)\n"
ROWS = """      + '<tr><td colspan="3" class="bs-subhead">Big Plays <span style="font-weight:400">(hover or tap a count to see the plays)</span></td></tr>'
      + bsRow('20+ Yard Plays', bpCell(e1,20), bpCell(e2,20))
      + bsRow('30+ Yard Plays', bpCell(e1,30), bpCell(e2,30))
      + bsRow('40+ Yard Plays', bpCell(e1,40), bpCell(e2,40))
      + bsRow('When Passing', bpCell(e1,40,'pass'), bpCell(e2,40,'pass'), true)
      + bsRow('When Rushing', bpCell(e1,40,'Rush'), bpCell(e2,40,'Rush'), true)
"""
JS_ANCHOR = "  function buildExplosivenessSection(a, b, heads){"
JS = """  function bpEsc(x){ return String(x).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function bpCell(e, min, kind){           // count of plays >= min yards (kind: 'pass' = pass+scramble, 'Rush'), with a hover list
    if(!e || !e.bigPlays) return '\\u2014';
    var L = e.bigPlays.filter(function(p){ return p.y>=min && (!kind || (kind==='pass' ? p.k!=='Rush' : p.k===kind)); });
    if(!L.length) return '0';
    var items = L.map(function(p){
      return '<div class="bp-item"><div class="bp-h"><b>'+p.y+' yds</b> \\u00b7 '+p.k+(p.td?' \\u00b7 <span class="bp-td">TD</span>':'')+'<span class="bp-when">Q'+p.q+' '+bpEsc(p.c)+'</span></div><div class="bp-t">'+bpEsc(p.t)+'</div></div>';
    }).join('');
    return '<span class="bp-cnt" tabindex="0">'+L.length+'<span class="bp-pop">'+items+'</span></span>';
  }
"""
CSS = """
  span.bp-cnt{ position:relative; cursor:help; border-bottom:1px dotted var(--ink-muted); outline:none; }
  span.bp-pop{ display:none; position:absolute; right:0; top:calc(100% + 4px); z-index:60; width:min(320px, 72vw); max-height:320px; overflow-y:auto;
    text-align:left; font-weight:400; white-space:normal; background:var(--surface); color:var(--ink); border:1px solid var(--line);
    border-radius:8px; box-shadow:0 6px 20px rgba(0,0,0,.18); padding:6px 8px; font-size:11px; line-height:1.35; }
  span.bp-cnt:hover span.bp-pop, span.bp-cnt:focus span.bp-pop{ display:block; }
  .bp-item{ padding:5px 0; border-top:1px solid var(--line); } .bp-item:first-child{ border-top:0; }
  .bp-h{ display:flex; gap:4px; align-items:baseline; } .bp-when{ margin-left:auto; color:var(--ink-muted); font-variant-numeric:tabular-nums; }
  .bp-td{ color:var(--off); font-weight:700; } .bp-t{ color:var(--ink-2); margin-top:2px; }
"""
for p in sys.argv[1:]:
    s = open(p).read()
    if 'function bpCell(' in s: print(p, 'already patched'); continue
    assert s.count(ANCHOR) == 1, (p, 'explosiveness rows anchor'); assert s.count(JS_ANCHOR) == 1, (p, 'section fn anchor')
    s = s.replace(ANCHOR, ANCHOR + ROWS).replace(JS_ANCHOR, JS + JS_ANCHOR)
    i = s.index('</style>', s.index('.bs-section-title{')); s = s[:i] + CSS + s[i:]      # the main stylesheet
    open(p, 'w').write(s); print(p, 'patched')
