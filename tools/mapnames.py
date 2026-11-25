"""Translate A-MapName via phrase substitution + dictionary."""
import re
D = {
 'A/V Room Without Plants': 'Bitkisiz Görsel-İşitsel Oda', 'Backyard': 'Arka Bahçe', 'Beginning of Underground Passage': 'Yeraltı Geçidinin Başı',
 'Boys Bathroom': 'Erkekler Tuvaleti', 'Casino - 1st Floor': 'Kumarhane - 1. Kat', 'Casino - Basement': 'Kumarhane - Bodrum',
 'Class Trial Courthouse': 'Sınıf Duruşması Salonu', 'Classroom C': 'C Sınıfı', 'Cold Sleep Room': 'Soğuk Uyku Odası', 'Computer Room': 'Bilgisayar Odası',
 'Cyber Courtyard': 'Siber Avlu', 'Dormitory': 'Yurt', 'Empty Room - Left': 'Boş Oda - Sol', 'Empty Room - Middle': 'Boş Oda - Orta',
 'Empty Room - Right': 'Boş Oda - Sağ', 'Escape Deck': 'Kaçış Güvertesi', 'Execution Ground': 'İnfaz Alanı', 'Exisal Hangar': 'Exisal Hangarı',
 "Exisal Hangar's Bathroom": 'Exisal Hangarının Banyosu', 'Game Room': 'Oyun Odası', 'Girls Bathroom': 'Kızlar Tuvaleti', 'Pool': 'Havuz',
 'Scrum Courthouse': 'Arbede Salonu', 'Shower Room': 'Duş Odası', 'Shrine of Judgment': 'Yargı Tapınağı',
 'Under the Floor of the Empty Rooms': 'Boş Odaların Zemininin Altı', 'Ultimate ??? Lab': 'Ultimate ??? Laboratuvarı',
 '6F Hallway': '6. Kat Koridoru', 'Basement Hallway': 'Bodrum Koridoru', 'Casino Area': 'Kumarhane Bölgesi', 'Colonnade Hallway': 'Sütunlu Koridor',
 'Entrance Hall': 'Giriş Holü', 'Front Entrance Hall': 'Ön Giriş Holü', 'Hallway in Front of Lined Pillar': 'Sütun Sırasının Önündeki Koridor',
 'Hallway to Gym': 'Spor Salonu Koridoru', 'Near Backyard': 'Arka Bahçe Yakını', 'Near Classroom': 'Sınıf Yakını', 'Near Dining Hall': 'Yemekhane Yakını',
 'Near School Entrance': 'Okul Girişi Yakını', 'Near the Three Doors': 'Üç Kapının Yakını', 'Outside of School Building': 'Okul Binasının Dışı',
 'Plaza in Front of Large Stairs': 'Büyük Merdivenlerin Önündeki Meydan', 'Relaxation Space': 'Dinlenme Alanı', 'Shrine Entrance': 'Tapınak Girişi',
}
TAL = {'Aikido Master': 'Aikido Ustası', 'Anthropologist': 'Antropolog', 'Artist': 'Sanatçı', 'Assassin': 'Suikastçı', 'Astronaut': 'Astronot',
       'Child Caregiver': 'Çocuk Bakıcısı', 'Cosplayer': 'Cosplayer', 'Detective': 'Dedektif', 'Entomologist': 'Böcekbilimci', 'Inventor': 'Mucit',
       'Magician': 'Sihirbaz', 'Maid': 'Hizmetçi', 'Pianist': 'Piyanist', 'Robot': 'Robot', 'Supreme Leader': 'Yüce Lider', 'Tennis Pro': 'Tenisçi'}
FLOOR = {'1st': '1.', '2nd': '2.', '3rd': '3.', '4th': '4.', '5th': '5.', '6th': '6.'}
def gen(n):
    return n + ("'ın" if n.endswith(('0',)) else "'nın" if n[-1] in 'aeiıoöuü' else "'ın")
def tr(t):
    if t in D: return D[t]
    m = re.fullmatch(r'(<PAD=【ＪＭＰ】> ?|\[JMP\] )(.*)', t)
    if m:
        inner = tr(m[2]); return m[1] + inner if inner else None
    m = re.fullmatch(r'Ultimate (.+) Lab', t)
    if m and m[1] in TAL: return 'Ultimate %s Laboratuvarı' % TAL[m[1]]
    m = re.fullmatch(r"(.+?)'s Room", t)
    if m:
        name = m[1]; last = name.split()[-1]
        suf = "'nın" if last[-1] in 'aeiou' else "'ın"
        if last == 'K1-B0': suf = "'ın"
        return name + suf + ' Odası'
    m = re.fullmatch(r'School Building - (\d)(?:st|nd|rd|th) Floor', t)
    if m: return 'Okul Binası - %s. Kat' % m[1]
    if t == 'School Building - Basement': return 'Okul Binası - Bodrum'
    if t == 'School Building - Spiral Staircase': return 'Okul Binası - Döner Merdiven'
    m = re.fullmatch(r'Main School Building_(\w+)_Move Point (\d)', t)
    if m:
        f = m[1].replace('F', '. Kat') if m[1] != 'Basement' else 'Bodrum'
        return 'Ana Okul Binası_%s_Hareket Noktası %s' % (f, m[2])
    m = re.fullmatch(r'Courtyard_(.+?) Move Point (\d)', t)
    if m:
        side = {'Behind School Building': 'Okul Binasının Arkası', 'Casino Side': 'Kumarhane Tarafı',
                'Cyber Courtyard Side': 'Siber Avlu Tarafı', 'Shrine Side': 'Tapınak Tarafı'}[m[1]]
        return 'Avlu_%s Hareket Noktası %s' % (side, m[2])
    m = re.fullmatch(r'Main School Building ?(?:\\n)?Hallway_(?:\\n)?(.+)_For Ch 6', t)
    if m:
        s = m[1]
        for a, b in FLOOR.items(): s = s.replace(a + ' Floor', b + ' Kat')
        s = s.replace('Entrance Hall Side', 'Giriş Holü Tarafı').replace('Gym Side', 'Spor Salonu Tarafı').replace('Basement', 'Bodrum').replace('Underground Cave', 'Yeraltı Mağarası')
        return 'Ana Okul Binası Koridoru_\\n' + s + '_6. Bölüm İçin'
    if t.startswith('Research Lab_Korekiyo Shinguji_\\n'):
        s = t.split('\\n', 1)[1]
        s = s.replace('Between Documents', 'Belgelerin Arasında').replace('During Seance', 'Seans Sırasında').replace('After Fixing Floor', 'Zemin Onarıldıktan Sonra').replace('After Ritual', 'Ayinden Sonra').replace('Before Ritual', 'Ayinden Önce')
        return 'Araştırma Lab._Korekiyo Shinguji_\\n' + s
    if t == 'Hidden Passage_For Ch 6': return 'Gizli Geçit_6. Bölüm İçin'
    if t == "Junko's Room_After Destruction_for Ch 6": return 'Junko\'nun Odası_Yıkımdan Sonra_6. Bölüm İçin'
    if t == "Junko's Room_for Ch 6": return 'Junko\'nun Odası_6. Bölüm İçin'
    m = re.fullmatch(r'Map Name (\d+)', t)
    if m: return 'Harita Adı ' + m[1]
    return None
out = ['@ game_resident_US']; miss = []
for l in open('batches/_en.txt', encoding='utf-8'):
    l = l.rstrip('\n')
    if l.startswith('## '): out.append(l); continue
    if '\t' not in l: continue
    i, t = l.split('\t', 1)
    o = tr(t)
    if o: out.append(i + '|' + o)
    else: miss.append(t)
open('batches/mapn.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print(len(out), 'miss', miss)
