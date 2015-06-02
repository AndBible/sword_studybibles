import os, codecs
from bs4 import BeautifulSoup, Tag

DEBUG = False
#DEBUG = True
if 'DEBUG' in os.environ:
    DEBUG = True

HTMLDIRECTORY='esv/OEBPS/Text'

bookrefs = ['Gen', 'Exod', 'Lev', 'Num', 'Deut', 'Josh', 'Judg', 'Ruth', '1Sam', '2Sam', '1Kgs', '2Kgs', '1Chr',
            '2Chr', 'Ezra', 'Neh', 'Esth', 'Job', 'Ps', 'Prov', 'Eccl', 'Song', 'Isa', 'Jer', 'Lam', 'Ezek', 'Dan',
            'Hos', 'Joel', 'Amos', 'Obad', 'Jonah', 'Mic', 'Nah', 'Hab', 'Zeph', 'Hag', 'Zech', 'Mal', 'Matt', 'Mark',
            'Luke', 'John', 'Acts', 'Rom', '1Cor', '2Cor', 'Gal', 'Eph', 'Phil', 'Col', '1Thess', '2Thess', '1Tim',
            '2Tim', 'Titus', 'Phlm', 'Heb', 'Jas', '1Pet', '2Pet', '1John', '2John', '3John', 'Jude', 'Rev']

class IllegalReference(Exception):
    pass

def parse_studyref(ref):
    """
        Takes studyref of formats:

            'nBBCCCVVV' (only start defined)
            'nBBCCCVVV-BBCCCVVV' (verse range defined)

        Returns tuple start,stop where stop is None if not range.

    """

    if ref == 'n36002012-outline':
        return 'Zeph.2.12'

    if ref[0] not in 'vn':
        raise IllegalReference

    ref = ref[1:] # remove first letter

    if '.' in ref:
        rfs = ref.split('.')
    else:
        rfs = [ref]

    result = []
    for ref in rfs:
        if '-' in ref:
            rfss = ref.split('-')
        else:
            rfss = [ref]

        refs = []
        for p in rfss:
            if len(p) == 9 and p[-1] in 'abc':
                p = p[:-1]

            if len(p) != 8:
                raise IllegalReference
            if p:
                book = bookrefs[int(p[:2])-1]
                chap = int(p[2:5])
                ver = int(p[5:])
                osisref = '{}.{}.{}'.format(book, chap, ver)
                refs.append(osisref)

        result.append('-'.join(refs))
    return ' '.join(result)

def firstref(ref):
    if ' ' in ref:
        ref = ref.split(' ')[0]
    if '-' in ref:
        ref = ref.split('-')[0]
    return ref.split('.')

class StudyBibleParse(object):
    """
    Tags to handle:

        - p contains verse range in id
        - strong - used for bolding words
        - small - content can be ignored ('NOTE ON ...')
        - a -> <reference osisRef="...">ref</reference>
        - span: outline titles etc. with class="outline-*")

    In the first phase, handle only data within <p>, writing content as is
    """

    def __init__(self):
        files = sorted([os.path.join(HTMLDIRECTORY, f) for f in os.listdir(HTMLDIRECTORY) if f.endswith('studynotes.xhtml')])

        bigsoup = BeautifulSoup(open('template.xml').read(), 'xml')
        osistext = bigsoup.find('osisText')
        #ot = bigsoup.new_tag('div', type='x-testament')
        #matt_ref = bookrefs.index('Matt')
        #for i in bookrefs[:matt_ref]:
        #    book = bigsoup.new_tag('div', type='book', osisID=i)
        #    ot.append(book)
        #nt = bigsoup.new_tag('div', type='x-testament')
        #for i in bookrefs[matt_ref:]:
        #    book = bigsoup.new_tag('div', type='book', osisID=i)
        #    nt.append(book)
        #osistext.append(ot)
        #osistext.append(nt)
        if DEBUG:
            files = files[:3]
        for fn in files:
            print 'processing', files.index(fn), fn
            try:
                data_in = codecs.open(fn, 'r', encoding='utf-8').read()
            except Exception as e:
                print 'Error in file %s' % fn
                raise e

            #bparse.feed(data_in)
            soup = BeautifulSoup(data_in, 'xml')

            # remove GENESIS - NOTE ON XXX from notes
            for s in soup.find_all('small'):
                s.extract()

            # adjust crossreferences
            for a in soup.find_all('a'):
                a.name = 'reference'
                url = a['href']
                file, verserange = url.split('#')
                ref = None
                if file.endswith('text.xhtml'):
                    ref = parse_studyref(verserange)
                elif file.endswith('studynotes.xhtml'):
                    try:
                        ref = parse_studyref(verserange)
                    except IllegalReference:
                        a.replace_with('EXTERNAL %s' % a.text)
                elif file.endswith('intros.xhtml') or file.endswith('resources.xhtml'):
                    # link may be removed
                    a.replace_with('EXTERNAL %s' % a.text)
                else:
                    raise Exception('not handled')

                if ref:
                    a['osisRef'] = ref
                del a['href']

            # replace bolded strings
            for s in soup.find_all('strong'):
                s.name = 'hi'
                s['type'] = 'bold'

            # replace smallcaps
            for s in soup.find_all('span', class_='smallcap'):
                s.name = 'hi'
                s['type'] = 'small-caps'
                del s['class']

            # find outline-2 (bigger studynote title, verse range highlighted)
            for s in soup.find_all('span', class_='outline-2'):
                s.name = 'hi'
                s['type'] = 'emphasis'
                del s['class']

            # find outline-3 (smaller studynote title, verse range not highlighted)
            for s in soup.find_all('span', class_='outline-3'):
                s.name = 'hi'
                s['type'] = 'emphasis'
                del s['class']

            # find outline-4 (even smaller studynote title, verse range not highlighted)
            for s in soup.find_all('span', class_='outline-4'):
                s.name = 'hi'
                s['type'] = 'emphasis'
                del s['class']

            # find outline-1 ('title' studynote covering verse range)
            for s in soup.find_all('span', class_='outline-1'):
                s.name = 'hi'
                s['type'] = 'emphasis'
                del s['class']

            # find esv font definitions
            for s in soup.find_all('span', class_='bible-version'):
                assert s.text.lower() in ['esv', 'lxx', 'kjv', 'mt'], s.text
                s.replace_with(s.text.upper())

            result = soup.find_all('span')
            if result:
                print 'still some spans: ', result

            for class_ in ['normal', 'image', 'era', 'caption', 'image-separator', 'chart-footnote']:
                for s in soup.find_all('p', class_=class_):
                    s.extract()

            for s in soup.find_all('hi'):
                if len(s) == 0:
                    s.extract()


            #result = soup.find_all('div')
            #if result:
            #    print 'some divs!', result

            # adjust studynotes
            for n in soup.find_all('p'):
                if not n['class'] in ['outline-1', 'outline-3', 'outline-4', 'study-note-continue', 'study-note']:
                    print 'not writing', n
                    continue

                if 'id' in n.attrs:
                    try:
                        ref = parse_studyref(n['id'])
                    except IllegalReference:
                        print 'not writing', n
                        continue

                    del n['id']
                    if 'class' in n.attrs:
                        del n['class']

                    new_div = soup.new_tag('studynote')
                    new_div['type'] = 'section'
                    new_div['annotateType'] = 'commentary'
                    new_div['annotateRef'] = ref

                    n.wrap(new_div)
                else:
                    previous = n.find_previous('studynote')
                    n.extract()
                    if 'class' in n.attrs:
                        del n['class']
                    previous.append(n)

            # write studynotes into OSIS file
            bookdivs = {}
            chapdivs = {}
            for n in soup.find_all('studynote'):
                n.name = 'div'
                #book, chap, ver = firstref(n['annotateRef'])
                #chapref = '%s.%s'%(book, chap)
                #verref = '%s.%s.%s'%(book, chap, ver)
                #chapdiv = chapdivs.get(chapref)
                #if chapdiv is None:
                #    bookdiv = bookdivs.get(book)
                #    if bookdiv is None:
                #        bookdiv = bookdivs[book] = bigsoup.find('div', osisID=book)
                #    chapdiv = bookdiv.find('chapter', osisID=chapref)
                #    if not chapdiv:
                #        chapdiv = bigsoup.new_tag('chapter', osisID=chapref)
                #        bookdiv.append(chapdiv)
                #    chapdivs[chapref] = chapdiv
                #verdiv = chapdiv.find('verse', osisID=verref)
                #if not verdiv:
                #    verdiv = bigsoup.new_tag('verse', osisID=verref)
                #    chapdiv.append(verdiv)
                #verdiv.append(n)
                #chapdiv.append(n)
                osistext.append(n)


        out = self.out = codecs.open('out.osis', 'w', encoding='utf-8')

        if DEBUG:
            out.write(bigsoup.prettify())
        else:
            out.write(unicode(bigsoup))

            out2 = codecs.open('pretty.xml', 'w', encoding='utf-8')
            out2.write(bigsoup.prettify())
            out2.close()

        out.close()


assert parse_studyref('n66002001-66003022.66002001-66003022') == 'Rev.2.1-Rev.3.22 Rev.2.1-Rev.3.22'
assert parse_studyref('n66002001a-66003022b') == 'Rev.2.1-Rev.3.22'
assert parse_studyref('n66002001-66003022') == 'Rev.2.1-Rev.3.22'
assert parse_studyref('n66001013') == 'Rev.1.13'
assert parse_studyref('n02023001-02023003.02023006-02023008') == 'Exod.23.1-Exod.23.3 Exod.23.6-Exod.23.8'
StudyBibleParse()
