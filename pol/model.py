'''
Created on 2010-10-03

@author: Marek Rogalski <mafikpl@gmail.com>

Contains classes representing constructs in polish grammar.
Module written in polish (python).

Elementy które działają jak do teraz:
-generowanie drzewa składni z tekstu w lożbanie
-budowanie struktury opisującej tekst w języku polskim (akapity -> tekst -> zdanie -> podmiot, orzeczenie, dopełnienia)
-tłumaczenie
 - odmiana orzeczenia przez osobę i liczbę podmiotu
 - domyślne podmioty dla orzeczeń bez podmiotu (ktoś, coś)
 - odmiana przyimków zależnie od kontekstu
 - zaimek zwrotny "się" (to trzeba przemyśleć)
 
Ważne błędy do poprawienia:
 -wygodniejsza reprezentacja syntezowanego tekstu (lista segmentów + rozpięte na nich drzewo składni) (DONE)
 -częstsze wykorzystywanie korpusu do wyboru formy słowa (już niepotrzebne)
 -pomijanie bridi-head (TODO)
 -caching zapytań! (TODO)
'''

import poliqarp.persistence as pq

class Kontekst:
    '''Tutaj trzymać informacje o ostatnio wspomnianych rzeczach.'''
    pass

class Tekst:
    def __init__(self):
        self.akapity = []
    def dodaj_akapit(self, akapit):
        self.akapity.append(akapit)
    def translate(self):
        gotowe = ""
        kontekst = Kontekst()
        for akapit in self.akapity:
            gotowe = gotowe + "\t" + akapit.translate(kontekst) + "\n"
        return gotowe
    
class Akapit:
    def __init__(self):
        self.zdania = []
    def dodaj_zdanie(self, zdanie):
        self.zdania.append(zdanie)
    def translate(self, kontekst):
        gotowe = ""
        kontekst.podmiot = None
        for zdanie in self.zdania:
            gotowe = gotowe + zdanie.translate(kontekst) + " "
        return gotowe

class Zdanie:
    def __init__(self):
        self.orzeczenie = None
        self.obiekty = [None] * 5
    def dodaj_orzeczenie(self, orzecznik):
        self.orzeczenie = orzecznik
    def dodaj_obiekt(self, pozycja, obiekt):
        self.obiekty[pozycja] = obiekt
    def translate(self, kontekst):
        słowa = []
        podmiot = self.obiekty[0] or self.orzeczenie.domyślny_podmiot
        podmiot.tagi['case'] = 'nom'
        if podmiot.osoba():
            self.orzeczenie.tagi['person'] = podmiot.osoba()
        else:
            self.orzeczenie.tagi['person'] = 'ter'
            
        if podmiot.liczba():
            self.orzeczenie.tagi['number'] = podmiot.liczba()
            
        if podmiot.osoba() not in ['pri', 'sec']:
            słowa.append(podmiot.translate(kontekst))
            
        kontekst.podmiot = podmiot.tagi['base']
        słowa.append(self.orzeczenie.translate(kontekst))
        for i in range(1,5):
            obiekt = self.obiekty[i]
            if obiekt:
                if self.orzeczenie.dopełnienia[i]:
                    self.orzeczenie.dopełnienia[i].obiekt = obiekt
                    słowa.append(self.orzeczenie.dopełnienia[i].translate(kontekst))
                else:
                    obiekt.tagi['case'] = 'acc'
                    słowa.append(obiekt.translate(kontekst))
        gotowe = ' '.join(słowa).strip()
        gotowe = gotowe[0].capitalize() + gotowe[1:] + '.'
        return gotowe
    
class Segment:
    Z_PODMIOTU = 'z_podmiotu'
    Z_ORZECZENIA = 'z_orzeczenia'
    Z_OBIEKTU = 'z_obiektu'
    def __init__(self, **kwargs):
        self.tagi = kwargs
    def __repr__(self):
        return '[{}]'.format(' & '.join(['{}="{}"'.format(k,v) for k,v in self.tagi.items() if v]))
    def query(self):
        assert not('pos' in self.tagi and self.tagi['pos'] == 'impt' and\
               'person' in self.tagi and self.tagi['person'] != 'sec'),\
               'Zdanie rozkazujące z podmiotem niedrugoosobowym.'
        self.cache = pq.query(str(self)) 
        return self.cache
    def tagset(self):
        return set(self.query()[0].interps[0].tag.split(':'))
    def liczba(self):
        tagset = self.tagset()
        for t in ['sg', 'pl']:
            if t in tagset:
                return t
    def osoba(self):
        tagset = self.tagset()
        for t in ['pri', 'sec', 'ter']:
            if t in tagset:
                return t
    def rodzaj(self):
        tagset = self.tagset()
        for t in ['m1', 'm2', 'm3', 'f', 'n']:
            print(t, tagset)
            if t in tagset:
                return t
    
class Słowo(Segment):
    def __init__(self, base, **kwargs):
        self.tagi = kwargs
        self.tagi['base'] = base
    def translate(self, kontekst):
        if self.tagi['base'] == kontekst.podmiot:
            się = Słowo('się')
            się.tagi['case'] = self.tagi['case']
            #się.tagi['person'] = self.osoba() or 'pri'
            return się.translate(kontekst) 
        segment = self.query()
        if segment: 
            return segment[0].orth.strip().lower()
        else:
            raise Exception('[Nieistniejące słowo: ' + str(self) + ']')
    __repr__ = Segment.__repr__
    
class Rzeczownik(Słowo):
    def __init__(self, base, **kw):
        Słowo.__init__(self, base, **kw)
        self.dopełnienia = []
        self.przymiotniki = []
    def translate(self, kontekst):
        wynik = ''
        if self.przymiotniki:
          wynik = ', '.join(p.translate() for p in self.przymiotniki) + ' '
        wynik += Słowo.translate(self, kontekst)
        if self.dopełnienia:
          wynik += ' ' + ' '.join(d.translate() for d in self.depełnienia)
        return wynik
        
    __repr__ = Słowo.__repr__
    

class Czasownik(Słowo):
    domyślny_podmiot = Słowo('ktoś')
    def __init__(self, base, **kw):
        Słowo.__init__(self, base, **kw)
        self.dopełnienia = [None] * 5
        self.tagi['!pos'] = 'impt'
    def imperatyw(self, wart):
        if wart:
            if '!pos' in self.tagi:
                del self.tagi['!pos']
            self.tagi['pos'] = 'impt'
        else:
            if 'pos' in self.tagi and self.tagi['pos'] == 'impt':
                del self.tagi['pos']
            self.tagi['!pos'] = 'impt'
    __repr__ = Słowo.__repr__
     
class WyrażenieModalne:
    def __init__(self, przyimek=None, obiekt=None, przypadek='nom'):
        self.przyimek = przyimek
        self.obiekt = obiekt
        self.przypadek = przypadek
    def translate(self, kontekst):
        self.obiekt.tagi['case'] = self.przypadek
        if self.przyimek:
            if type(self.przyimek) == str:
                t1 = self.przyimek + ' '
            else:
                t1 = self.przyimek.translate(kontekst) + ' '
        else:
            t1 = ''
        t2 = self.obiekt.translate(kontekst)
        return t1 + t2
