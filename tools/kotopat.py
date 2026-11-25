"""Regex translation of internal labels in A-Kotodama; writes batch + leftovers."""
import re, sys
R = [
    (r'^Ch\. ?(\d) Scene (\d+) \(Investigation\)$', r'\1. Bölüm Sahne \2 (Soruşturma)'),
    (r'^Ch\. ?(\d) Scene (\d+) \(After [Tt]rial\)$', r'\1. Bölüm Sahne \2 (Duruşma Sonrası)'),
    (r'^Ch\. ?(\d) Scene (\d+)$', r'\1. Bölüm Sahne \2'),
    (r'^Ch\. (\d) Spare Frame$', r'\1. Bölüm Yedek Kare'),
    (r'^Demo [Ss]cene (\d+) \(Investigation\)$', r'Demo Sahne \1 (Soruşturma)'),
    (r'^Demo [Ss]cene (\d+) \(After Trial\)$', r'Demo Sahne \1 (Duruşma Sonrası)'),
    (r'^Demo [Ss]cene (\d+)$', r'Demo Sahne \1'),
    (r'^Demo Spare Frame$', r'Demo Yedek Kare'),
    (r'^Non-stop De[bv]ate(.*)$', r'Durmaksızın Tartışma\1'),
    (r'^Monokuma File( \d)?$', r'Monokuma Dosyası\1'),
    (r'^Mind Mine (\d)$', r'Zihin Mayını \1'),
    (r'^Hangman\'s Gambit (\d)$', r'Cellat Kumarı \1'),
    (r'^Flash Anagram (\d)(.*)$', r'Flaş Anagram \1\2'),
    (r'^Excavation Imagination( \d)?$', r'Hayal Kazısı\1'),
    (r'^Brain Drive( \d)?(.*)$', r'Beyin Sürüşü\1\2'),
    (r'^Mass Panic Debate(.*)$', r'Toplu Panik Tartışması\1'),
    (r'^Rebuttal Showdown(.*)$', r'Çürütme Düellosu\1'),
    (r'^Argument Armament(.*)$', r'Argüman Silahlanması\1'),
    (r'^Psyche Taxi(.*)$', r'Psişik Taksi\1'),
    (r'^Debate Scrum(.*)$', r'Tartışma Arbedesi\1'),
    (r'^Closing Argument(.*)$', r'Kapanış Argümanı\1'),
    (r'^Conversation (\d+)$', r'Konuşma \1'),
]
WORDS = [(' Agree ', ' Katılma '), (' Broken ', ' Kırık '), (' broken ', ' kırık '), (' Lie ', ' Yalan '), (' Panic ', ' Panik '),
         ('(Back)', '(Arka)'), ('(Special)', '(Özel)')]
def tr(t):
    for p, s in R:
        if re.match(p, t):
            o = re.sub(p, s, t)
            for a, b in WORDS: o = o.replace(a, b)
            return o
    return None
out = ['@ game_resident_US']; left = []
for l in open(sys.argv[1], encoding='utf-8'):
    l = l.rstrip('\n')
    if l.startswith('## '): out.append(l); continue
    if '\t' not in l: continue
    i, t = l.split('\t', 1)
    o = tr(t)
    if o: out.append(i + '|' + o)
    else: left.append(t)
open('batches/m_koto_auto.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
open('batches/_u3.txt', 'w', encoding='utf-8').write('\n'.join(sorted(set(left))) + '\n')
print(len(out), len(set(left)))
