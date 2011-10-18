'''
Created on 2010-10-03

@author: Marek Rogalski <mafikpl@gmail.com>
'''

import pol.model as m
import sys

DEBUG = {'-pass', '-join', '+'}

def debug(code, format, *args):
    if ('+' + code) in DEBUG:
        print(format.format(*args))
        

def empty(nav):
    if len(nav.children) == 1:
        debug("pass", "{} is implicitly passing {}", nav, nav.children[0])
    else:
        debug("join", "{} is implicitly joining {}", nav, nav.children)
    return nav

def visible(nav):
    return nav

vocative = visible
terminal = visible
selbri = visible

def sumti(nav):
    #i = nav.sumti_1[0].sumti_2[0].sumti_3[0].sumti_4[0].sumti_5[0].sumti_6[0].KOhA[0]
    #print(i,':',dir(i))
    #sys.exit(1)
    text = nav.text()
    if text == 'mi':
        nav.object = m.Słowo('ja')
    elif text == 'mi\'o':
        nav.object = m.Słowo('my') # ja i ty
    elif text == 'mi\'a':
        nav.object = m.Słowo('my') # ja i inni niż ty
    elif text == 'ma\'a':
        nav.object = m.Słowo('my') # my wszyscy
    elif text == 'do\'o':
        nav.object = m.Słowo('wy')
    elif text == 'do':
        nav.object = m.Słowo('ty')
    elif text == 'ko':
        nav.object = m.Słowo('ty')
        nav.imperatyw = True # przenieść sprawdzanie imperatywu na poziom zdania
    elif text == 'ti':
        nav.object = m.Rzeczownik('to')
    elif text == 'ta':
        nav.object = m.Słowo('ten')
    elif text == 'tu':
        nav.object = m.Rzeczownik('tamto')
    elif text == 'da':
        nav.object = m.Rzeczownik('coś')
    elif text == 'zo\'e':
        pass #nav.object = m.Elipsa()
    elif text.startswith('le'):
        raise Exception('Sumti z "le" na początku na chwilę obecną nie są obsługiwane i zostały wyłączone. Skorzystaj z przełącznika --help-supported')
        i = nav.sumti_1[0].sumti_2[0].sumti_3[0].sumti_4[0].sumti_5[0].sumti_6[0]
        print(i,':',dir(i))
        sys.exit(1)
        pośredni_nawigator = nav[0]
        le = pośredni_nawigator[0]
        selbri = pośredni_nawigator[1]
        text = selbri.text()
        if text == 'pipno':
          nav.object = m.Rzeczownik('pianino')
        elif text.startswith('nu'): # TODO: elegantsze zapytanie do nawigatora zamiast startswith
          nav.object = m.Rzeczownik('czynność')
          #selbri.object
          # TODO: w elegantszy sposób przerobić zdanie na rzeczownik "Poszedłem do kina" -> "Moje przeszłe pójście do kina"
          #if 'przymiotniki' not in vars(nav.object): # bo obecnie po prostu dodaję listę z przymiotnikami... :/
            #nav.object.przymiotniki = []
        else:
          raise Exception('Nietypowe sumti-tail: {} {}'.format(le, selbri))
        nav.object.przymiotniki.append(m.Słowo('ten|ta|to'))
    else:
        raise Exception('Nietypowe sumti: {}'.format(text))
    return nav

# TODO: słownik ze skojarzeniami

def sentence(nav):
    zdanie = m.Zdanie()
    imperatyw = False
    position = 0
    for i in nav.descendants_once('sumti'):
        text = i.text()
        if i.object: zdanie.dodaj_obiekt(position, i.object)
        if 'imperatyw' in vars(i): imperatyw = True
        position += 1
        
    # przetworzyć terms w bridi_head
    # przetworzyć selbri w bridi_tail
    # przetworzyć terms w bridi_tail
    selbri = nav.bridi_tail[0].bridi_tail_1[0].bridi_tail_2[0].bridi_tail_3[0].selbri[0]
    text = selbri.text()
    if text == 'cusku': # TODO: obiekt dopasowujący selbri
        orzeczenie = m.Czasownik('mówić')
        co = m.WyrażenieModalne(None, przypadek='acc')
        komu = m.WyrażenieModalne(None, przypadek='dat')
        przez = m.WyrażenieModalne(m.Słowo('przez'), przypadek='gen')
        orzeczenie.dopełnienia[1] = co
        orzeczenie.dopełnienia[2] = komu
        orzeczenie.dopełnienia[3] = przez
    elif text == 'zvati':
        orzeczenie = m.Czasownik('być', pos='fin')
        w = m.WyrażenieModalne(m.Słowo('w'), przypadek='loc')
        orzeczenie.dopełnienia[1] = w
    elif text == 'gunka':
        orzeczenie = m.Czasownik('pracować', pos='verb')
        nad = m.WyrażenieModalne(m.Słowo('nad'), przypadek='inst')
        cel = m.WyrażenieModalne('w celu osiągnięcia', przypadek='gen')
        orzeczenie.dopełnienia[1] = nad
        orzeczenie.dopełnienia[2] = cel
    elif text == 'klama':
        orzeczenie = m.Czasownik('iść')
        do = m.WyrażenieModalne(m.Słowo('do'), przypadek='gen')
        przez = m.WyrażenieModalne(m.Słowo('przez'), przypadek='acc')
        z = m.WyrażenieModalne(m.Słowo('z'), przypadek='gen')
        używając = m.WyrażenieModalne(m.Słowo('używać', pos='pcon'), przypadek='gen')
        orzeczenie.dopełnienia[1] = do
        orzeczenie.dopełnienia[2] = z
        orzeczenie.dopełnienia[3] = przez
        orzeczenie.dopełnienia[4] = używając
    elif text == 'tcidu':
        orzeczenie = m.Czasownik('czytać')
        co = m.WyrażenieModalne(None, przypadek='acc')
        czego = m.WyrażenieModalne(m.Słowo('z'), przypadek='gen')
        orzeczenie.dopełnienia[1] = co
        orzeczenie.dopełnienia[2] = czego
    elif text == 'bevri':
        orzeczenie = m.Czasownik('nosić')
        co = m.WyrażenieModalne(None, przypadek='acc')
        do = m.WyrażenieModalne(m.Słowo('do'), przypadek='gen')
        z = m.WyrażenieModalne(m.Słowo('z'), przypadek='gen')
        przez = m.WyrażenieModalne(m.Słowo('przez'), przypadek='acc')
        orzeczenie.dopełnienia[1] = co
        orzeczenie.dopełnienia[2] = do
        orzeczenie.dopełnienia[3] = z
        orzeczenie.dopełnienia[4] = przez
    elif text == 'tavla':
        orzeczenie = m.Czasownik('mówić')
        do = m.WyrażenieModalne(m.Słowo('do'), przypadek='gen')
        o = m.WyrażenieModalne(m.Słowo('o'), przypadek='loc')
        w_języku = m.WyrażenieModalne('w języku', przypadek='gen') # dodać rzeczownik "język", a to co było w obiekcie przerobić na przymiotnik
        orzeczenie.dopełnienia[1] = do
        orzeczenie.dopełnienia[2] = o
        orzeczenie.dopełnienia[3] = w_języku
    elif text == 'nelci':
        orzeczenie = m.Czasownik('lubić')
        co = m.WyrażenieModalne(None, przypadek='acc')
        orzeczenie.dopełnienia[1] = co
    elif text == 'djica':
        orzeczenie = m.Czasownik('chcieć')
        co = m.WyrażenieModalne(None, przypadek='acc')
        do = m.WyrażenieModalne(m.Słowo('do'), przypadek='gen')
        orzeczenie.dopełnienia[1] = co
        orzeczenie.dopełnienia[2] = do
    elif text == 'djuno':
        orzeczenie = m.Czasownik('wiedzieć')
        że = m.WyrażenieModalne(None, przypadek='nom')
        o = m.WyrażenieModalne(m.Słowo('o'), przypadek='loc')
        według = m.WyrażenieModalne(m.Słowo('według'), przypadek='gen')
        orzeczenie.dopełnienia[1] = że
        orzeczenie.dopełnienia[2] = o
        orzeczenie.dopełnienia[3] = według
    elif text == 'pilno':
        orzeczenie = m.Czasownik('używać')
        co = m.WyrażenieModalne(None, przypadek='gen')
        do = m.WyrażenieModalne(m.Słowo('do'), przypadek='gen')
        orzeczenie.dopełnienia[1] = co
        orzeczenie.dopełnienia[2] = do
    elif text == 'cliva':
        orzeczenie = m.Czasownik('opuszczać')
        co = m.WyrażenieModalne(None, przypadek='acc')
        drogą = m.WyrażenieModalne('drogą przez', przypadek='acc') # TODO /przymiotnik/ drogą
        orzeczenie.dopełnienia[1] = co
        orzeczenie.dopełnienia[2] = drogą
    elif text == 'prenu':
        orzeczenie = m.Czasownik('być', pos='fin')
        kim = m.WyrażenieModalne(None, przypadek='inst')
        orzeczenie.dopełnienia[1] = kim
        zdanie.dodaj_obiekt(1, m.Słowo('osoba'))
    elif text == 'jimpe':
        orzeczenie = m.Czasownik('rozumieć')
        orzeczenie.dopełnienia[1] = m.WyrażenieModalne(None, przypadek='acc') # TODO: du'u, lenu
        orzeczenie.dopełnienia[2] = m.WyrażenieModalne(m.Słowo('o'), przypadek='loc')
    elif text == 'cmene':
        o = zdanie.obiekty # domyślny szyk: imię, nazwany, nazywające
        orzeczenie = m.Czasownik('nazywać')
        orzeczenie.dopełnienia[1] = m.WyrażenieModalne(None, przypadek='acc')
        orzeczenie.dopełnienia[2] = m.WyrażenieModalne(',', przypadek='nom')
        if o[2]:
            o[0], o[1], o[2] = o[2], o[1], o[0] # nowy szyk: ktoś nazywa kogoś "jakoś"
            o[1] = o[1] or m.Rzeczownik('ktoś')
        elif o[1]: # TODO: cytaty
            o[0], o[1], o[2] = o[1], o[1], o[0] # TODO: nowy szyk: ktoś jest nazywany "jakoś"
        else: # podano tylko nazwę -> x jest nazwą
            orzeczenie = m.Czasownik('być', pos='fin')
            orzeczenie.dopełnienia[1] = m.WyrażenieModalne(None, przypadek='inst')
            zdanie.dodaj_obiekt(1, m.Słowo('nazwa')) # TODO: liczba mnoga i pojedyńcza podana po ukośnikach
        
    else:
        raise Exception('Unhandled selbri: {}. Sentence was: {}.'.format(text, nav.text()))
    orzeczenie.imperatyw(imperatyw)
    zdanie.dodaj_orzeczenie(orzeczenie)
    nav.object = zdanie
    return nav

def paragraph(nav):
    akapit = m.Akapit()
    for sentence in nav.descendants_once('sentence'):
        akapit.dodaj_zdanie(sentence.object)
    nav.object = akapit
    return nav

def text(nav):
    tekst = m.Tekst()
    for akapit in nav.descendants_once('paragraph'):
        tekst.dodaj_akapit(akapit.object)
    nav.object = tekst
    return nav
