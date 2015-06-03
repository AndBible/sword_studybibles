import os, codecs, optparse
from bs4 import BeautifulSoup
import jinja2

TAGS_NONE = 0
TAGS_BOOK = 1
TAGS_CHAPTES = 2
TAGS_VERSES = 3

HTMLDIRECTORY='OEBPS/Text'

bookrefs = ['Gen', 'Exod', 'Lev', 'Num', 'Deut', 'Josh', 'Judg', 'Ruth', '1Sam', '2Sam', '1Kgs', '2Kgs', '1Chr',
            '2Chr', 'Ezra', 'Neh', 'Esth', 'Job', 'Ps', 'Prov', 'Eccl', 'Song', 'Isa', 'Jer', 'Lam', 'Ezek', 'Dan',
            'Hos', 'Joel', 'Amos', 'Obad', 'Jonah', 'Mic', 'Nah', 'Hab', 'Zeph', 'Hag', 'Zech', 'Mal', 'Matt', 'Mark',
            'Luke', 'John', 'Acts', 'Rom', '1Cor', '2Cor', 'Gal', 'Eph', 'Phil', 'Col', '1Thess', '2Thess', '1Tim',
            '2Tim', 'Titus', 'Phlm', 'Heb', 'Jas', '1Pet', '2Pet', '1John', '2John', '3John', 'Jude', 'Rev']

class IllegalReference(Exception):
    pass

def parse_studybible_reference(html_id):
    """
        Takes studybibles reference html_id, which is in the following formats:

            'nBBCCCVVV' (only start defined)
            'nBBCCCVVV-BBCCCVVV' (verse range defined)
            'nBBCCCVVV-BBCCCVVV BBCCCVVV-BBCCCVVV BBCCCVVV' (multiple verses/ranges defined)

        Returns OSIS reference.

    """

    if html_id == 'n36002012-outline': # exception found in ESV Study bible epub!
        return 'Zeph.2.12'

    if html_id[0] not in 'vn':
        raise IllegalReference

    html_id = html_id[1:] # remove first letter

    if '.' in html_id:
        individual_refs = html_id.split('.')
    else:
        individual_refs = [html_id]

    result = []
    for iref in individual_refs:
        if '-' in iref:
            range_refs = iref.split('-')
        else:
            range_refs = [iref]

        refs = []
        for p in range_refs:
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

assert parse_studybible_reference('n66002001-66003022.66002001-66003022') == 'Rev.2.1-Rev.3.22 Rev.2.1-Rev.3.22'
assert parse_studybible_reference('n66002001a-66003022b') == 'Rev.2.1-Rev.3.22'
assert parse_studybible_reference('n66002001-66003022') == 'Rev.2.1-Rev.3.22'
assert parse_studybible_reference('n66001013') == 'Rev.1.13'
assert parse_studybible_reference('n02023001-02023003.02023006-02023008') == 'Exod.23.1-Exod.23.3 Exod.23.6-Exod.23.8'

def first_reference(ref):
    if ' ' in ref:
        ref = ref.split(' ')[0]
    if '-' in ref:
        ref = ref.split('-')[0]
    return ref.split('.')

def handle_tags(input_soup, root_soup):
    for s in input_soup.find_all('small'):
        # remove BOOK - NOTE ON XXX from studynotes
        if 'NOTE ON' in s.text or 'online at' in s.text:
            s.extract()
        elif s.text in ['A.D.', 'B.C.', 'A.M.', 'P.M.']:
            s.replace_with(s.text)
        else:
            print 'not removing', s

    # adjust crossreferences
    for a in input_soup.find_all('a'):
        a.name = 'reference'
        url = a['href']
        file, verserange = url.split('#')
        ref = None
        if file.endswith('text.xhtml'):
            ref = parse_studybible_reference(verserange)
        elif file.endswith('studynotes.xhtml'):
            try:
                ref = parse_studybible_reference(verserange)
            except IllegalReference:
                a.replace_with('[%s]' % a.text)
        elif file.endswith('intros.xhtml') or file.endswith('resources.xhtml') or file.endswith('footnotes.xhtml'):
            # link may be removed
            a.replace_with('[%s]' % a.text)
        else:
            raise Exception('Link not handled %s'%file)

        if ref:
            a['osisRef'] = ref
        del a['href']
        if 'onclick' in a.attrs:
            del a['onclick']

    # replace bolded strings
    for s in input_soup.find_all('strong'):
        s.name = 'hi'
        s['type'] = 'bold'
        if 'class' in s.attrs:
            del s['class']

    # replace smallcaps
    for cls in ['smallcap', 'small-caps', 'divine-name']:
        for s in input_soup.find_all('span', class_=cls):
            s.name = 'hi'
            s['type'] = 'small-caps'
            del s['class']

    # find outline-1 ('title' studynote covering verse range)
    # find outline-2 (bigger studynote title, verse range highlighted)
    # find outline-3 (smaller studynote title, verse range not highlighted)
    # find outline-4 (even smaller studynote title, verse range not highlighted)

    for k in ['outline-%s'%i for i in xrange(1,5)]:
        for s in input_soup.find_all('span', class_=k):
            s.name = 'hi'
            s['type'] = 'bold'
            del s['class']
            new_tag = root_soup.new_tag('hi', type='underline')
            s.wrap(new_tag)

    # find esv font definitions
    for s in input_soup.find_all('span', class_='bible-version'):
        assert s.text.lower() in ['esv', 'lxx', 'kjv', 'mt', 'nkjv', 'nasb'], s.text
        s.replace_with(s.text.upper())

    result = input_soup.find_all('span')
    if result:
        print 'still some spans: ', result

    for class_ in ['normal', 'image', 'era', 'caption', 'image-separator', 'chart-footnote']:
        for s in input_soup.find_all('p', class_=class_):
            s.extract()

    for s in input_soup.find_all('hi'):
        if len(s) == 0:
            s.extract()

def adjust_studynotes(input_html):
    for n in input_html.find_all('p'):

        if not n['class'] in ['outline-1', 'outline-3', 'outline-4', 'study-note-continue', 'study-note']:
            # not writing any charts, images, facts ('normal' in global)...
            if n['class'] in ['normal', 'image', 'era', 'caption', 'image-separator', 'chart-footnote']:
                pass
            else:
                print 'not writing', n
            continue

        handle_tags(n, input_html)

        if 'id' in n.attrs:
            try:
                ref = parse_studybible_reference(n['id'])
            except IllegalReference:
                print 'not writing', n
                continue

            del n['id']
            if 'class' in n.attrs:
                del n['class']

            new_div = input_html.new_tag('studynote')
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

def write_studynotes_into_osis(input_html, output_xml, osistext, tag_level):
    bookdivs = {}
    chapdivs = {}
    bookdiv, chapdiv, verdiv = None, None, None
    for n in input_html.find_all('studynote'):
        n.name = 'div'
        book, chap, ver = first_reference(n['annotateRef'])
        chapref = '%s.%s'%(book, chap)
        verref = '%s.%s.%s'%(book, chap, ver)

        if tag_level >= TAGS_BOOK:
            bookdiv = bookdivs.get(book)
            if bookdiv is None:
                bookdiv = bookdivs[book] = output_xml.find('div', osisID=book)
        if tag_level >= TAGS_CHAPTES:
            chapdiv = chapdivs.get(chapref)
            if chapdiv is None:
                chapdiv = bookdiv.find('chapter', osisID=chapref)
                if not chapdiv:
                    chapdiv = output_xml.new_tag('chapter', osisID=chapref)
                    bookdiv.append(chapdiv)
                chapdivs[chapref] = chapdiv
        if tag_level >= TAGS_VERSES:
            verdiv = chapdiv.find('verse', osisID=verref)
            if not verdiv:
                verdiv = output_xml.new_tag('verse', osisID=verref)
                chapdiv.append(verdiv)

        [osistext, bookdiv, chapdiv, verdiv][tag_level].append(n)
    return output_xml

def process_files(options,  input_dir):
    tag_level = options.tag_level
    debug = options.debug

    print "TAG_LEVEL: %s, DEBUG: %s" %(tag_level, debug)
    files = sorted([os.path.join(input_dir, HTMLDIRECTORY, f) for f in os.listdir(os.path.join(input_dir, HTMLDIRECTORY)) if f.endswith('studynotes.xhtml')])

    template = jinja2.Template(open('template.xml').read())
    output_xml = BeautifulSoup(template.render(title=options.title, work_id=options.work_id), 'xml')
    osistext = output_xml.find('osisText')
    if tag_level >= TAGS_BOOK:
        ot = output_xml.new_tag('div', type='x-testament')
        matt_ref = bookrefs.index('Matt')
        for i in bookrefs[:matt_ref]:
            book = output_xml.new_tag('div', type='book', osisID=i)
            ot.append(book)
        nt = output_xml.new_tag('div', type='x-testament')
        for i in bookrefs[matt_ref:]:
            book = output_xml.new_tag('div', type='book', osisID=i)
            nt.append(book)
        osistext.append(ot)
        osistext.append(nt)

    if debug:
        files = files[:3]
    for fn in files:
        print 'processing', files.index(fn), fn
        try:
            data_in = codecs.open(fn, 'r', encoding='utf-8').read()
        except Exception as e:
            print 'Error in file %s' % fn
            raise e

        input_html = BeautifulSoup(data_in, 'xml')

        #result = soup.find_all('div')
        #if result:
        #    print 'some divs!', result

        adjust_studynotes(input_html)
        write_studynotes_into_osis(input_html, output_xml, osistext, tag_level)

    out = codecs.open('%s.xml'%input_dir, 'w', encoding='utf-8')

    if debug:
        out.write(output_xml.prettify())
    else:
        out.write(unicode(output_xml))

        out2 = codecs.open('%s_pretty.xml'%input_dir, 'w', encoding='utf-8')
        out2.write(output_xml.prettify())
        out2.close()

    out.close()

parser = optparse.OptionParser(usage='Usage. %prog [options] input_dir')
parser.add_option('--debug', action='store_true', dest='debug', default=False,
                   help='Debug mode')
parser.add_option('--tag_level', dest='tag_level', default=0, type=int,
                   help='Tag level: 0: none, 1: book divs, 2: chapter divs, 3: verse divs')
parser.add_option('--title', dest='title', default='ESV Study Bible Notes',
                   help='OSIS title')
parser.add_option('--work_id', dest='work_id', default='ESB',
                   help='OSIS work_id')

options, args = parser.parse_args()
if len(args) == 1:
    input_dir = args[0]
    process_files(options, input_dir)
else:
    parser.print_help()
