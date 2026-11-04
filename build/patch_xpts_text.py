"""Expected-score tooltip text: turnovers are no longer part of the model (Nov 2, 2026) and the NFL model has no explosive term.
Idempotent. usage: patch_xpts_text.py cfb|nfl PAGE.html [PAGE.html ...]"""
import sys
LG = sys.argv[1]
OLD = "what each offense should have scored from drives, share of available yards gained, success rate, explosive plays and interceptions + half of fumbles. Field position, return/defensive TDs and red-zone finishing are left out on purpose."
NEW = ("what each offense should have scored from drives, share of available yards gained, success rate" + (" and explosive plays" if LG == 'cfb' else "")
       + ". Turnovers are not counted against the offense (treated as luck). Field position, return/defensive TDs and red-zone finishing are left out on purpose.")
# Nov 3: turnover-neutral drives
OLD2 = "Turnovers are not counted against the offense (treated as luck)."
NEW2 = "Turnovers are not counted against the offense (treated as luck): a drive that ends in an interception or lost fumble counts as at least an average drive."
for p in sys.argv[2:]:
    s = open(p).read(); n = s.count(OLD)
    if n: s = s.replace(OLD, NEW); print(p, 'patched', n)
    if NEW2 not in s:
        n2 = s.count(OLD2); s = s.replace(OLD2, NEW2); print(p, 'turnover-drive note', n2)
    # Nov 3: CFB garbage time
    G_OLD = "counts as at least an average drive."
    G_NEW = "counts as at least an average drive. Garbage time (lopsided score late in the game) is left out."
    if LG == 'cfb' and G_NEW not in s and G_OLD in s:
        print(p, 'garbage-time note', s.count(G_OLD)); s = s.replace(G_OLD, G_NEW)
    # Nov 3 (v3 / option 4): one canonical sentence, replaces whatever earlier version is on the page
    import re
    V3 = ("Box-score expected score: what each offense should have scored from its drives, down-to-down success rate, explosive plays and the share of "
          "available yards gained (each play counts at most 20 yards there, so long touchdowns are rewarded but treated as partly luck). Turnovers are "
          "neither penalized nor rewarded: a drive that ends in a turnover counts what it gained, like a punt. Garbage time is left out. Field position, "
          "return/defensive TDs and red-zone finishing are left out on purpose. Deserved win % = how often a team with this box-score edge wins.")
    s, k = re.subn(r'Box-score expected score: what each offense should have scored from [^"]*?Deserved win % = how often a team with this box-score edge wins\.', V3, s)
    print(p, 'v3 text', k)
    open(p, 'w').write(s)
