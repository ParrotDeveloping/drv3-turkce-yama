"""Auto-translate report-card stat lines (B-TechouTsushinbo): units -> metric, dates -> Turkish.
Writes batches/m_tsu_auto.txt and leaves the rest in batches/_en2.txt."""
import re
mon = dict(January='Ocak', February='Şubat', March='Mart', April='Nisan', May='Mayıs', June='Haziran', July='Temmuz',
           August='Ağustos', September='Eylül', October='Ekim', November='Kasım', December='Aralık')
out = ['@ game_resident_US']; manual = []; cur = ''
for l in open('batches/_en.txt', encoding='utf-8-sig'):
    l = l.rstrip('\n')
    if l.startswith('## '):
        cur = l; out.append(l); manual.append(l); continue
    if '\t' not in l: continue
    i, t = l.split('\t', 1)
    if cur != '## B-TechouTsushinbo':
        manual.append(l); continue
    m = re.fullmatch(r"(\d)'(?:(\d+)\")?", t)
    if m: out.append(i + '|%d cm' % round((int(m[1]) * 12 + int(m[2] or 0)) * 2.54)); continue
    m = re.fullmatch(r'(\d+) lbs\.', t)
    if m: out.append(i + '|%d kg' % round(int(m[1]) * 0.4536)); continue
    m = re.fullmatch(r'(\d+)"', t)
    if m: out.append(i + '|%d cm' % round(int(m[1]) * 2.54)); continue
    m = re.fullmatch(r'(\w+) (\d+)', t)
    if m and m[1] in mon: out.append(i + '|%s %s' % (m[2], mon[m[1]])); continue
    if re.fullmatch(r'(A|B|O|AB|\?\?\?)', t) or int(i) % 10 < 3:
        out.append(i + '|' + t); continue
    manual.append(l)
open('batches/m_tsu_auto.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
open('batches/_en2.txt', 'w', encoding='utf-8').write('\n'.join(manual) + '\n')
print(len(out), len(manual))
