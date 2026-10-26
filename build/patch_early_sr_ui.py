"""Add the early-down success rate rows to a dashboard page template (CFB or NFL; same box-score code).
 - Overall section: 'Early Down Success Rate' right under 'Success Rate' (heat-shaded like the rest)
 - Early Downs (1st & 2nd) section: 'Success Rate' right under 'EPA/Play'
Idempotent. usage: patch_early_sr_ui.py PAGE.html [PAGE.html ...]"""
import sys
A_OLD = "['successRate','Success Rate','off'], "
A_NEW = "['successRate','Success Rate','off'], ['earlySuccessRate','Early Down Success Rate','off'], "
B_OLD = "      + bsRow('EPA/Play', bn(s1.earlyEpaPlay,3), bn(s2.earlyEpaPlay,3), true)\n"
B_NEW = B_OLD + "      + bsRow('Success Rate', bp(s1.earlySuccessRate), bp(s2.earlySuccessRate), true)\n"
for p in sys.argv[1:]:
    s = open(p).read()
    if 'earlySuccessRate' in s.split('<script id="dashboard-data"')[0] + s.split('</script>', 1)[-1][:0] or "'earlySuccessRate','Early Down" in s:
        print(p, 'already patched'); continue
    assert s.count(A_OLD) == 1, (p, 'overall anchor', s.count(A_OLD))
    assert s.count(B_OLD) == 1, (p, 'early-downs anchor', s.count(B_OLD))
    s = s.replace(A_OLD, A_NEW).replace(B_OLD, B_NEW)
    open(p, 'w').write(s); print(p, 'patched')
