# encoding: utf-8
"""
    Copyright (C) 2015 Tuomas Airaksinen.
    See LICENCE.txt
"""

import os, codecs, optparse
from bs4 import BeautifulSoup, NavigableString, Tag
import jinja2

TAGS_NONE = 0
TAGS_BOOK = 1
TAGS_CHAPTES = 2
TAGS_VERSES = 3

HTMLDIRECTORY = 'OEBPS/Text'

from bible_data import BOOKREFS, CHAPTER_LAST_VERSES, LAST_CHAPTERS

def get_verse_ranges():
    """ get data for CHAPTER_LST_VERSES and LAST_CHAPTERS from ESVS osis file"""
    bs = BeautifulSoup(open('esvs.osis').read(), 'xml')
    print 'reading done'
    verse_nums = {}
    chap_nums = {}
    for v in bs.find_all('verse'):
        ref = Ref(v['osisID'])
        chapref = '%s.%s' % (BOOKREFS[ref.numref[0]], ref.numref[1])
        verse_nums[chapref] = max(ref.numref[2], verse_nums.get(chapref, 0))
        bookref = BOOKREFS[ref.numref[0]]
        chap_nums[bookref] = max(ref.numref[1], chap_nums.get(bookref, 0))
    return chap_nums, verse_nums


class IllegalReference(Exception):
    pass


def verses(a):
    if isinstance(a, Tag):
        a = a['annotateRef']
    return sorted([Ref(i) for i in a.split(' ')])

def singleton(cls):
    instances = {}

    def getinstance(ref_string):
        assert ref_string
        if isinstance(ref_string, (list, tuple)):
            ref_string = '%s.%s.%s' % tuple(ref_string)
        if ref_string not in instances:
            instances[ref_string] = cls(ref_string)
        return instances[ref_string]

    return getinstance


@singleton
class Ref(object):
    def __init__(self, ref_string):
        book, chap, verse = ref_string.split('.')
        bookint = BOOKREFS.index(book)
        chapint = int(chap)
        verseint = int(verse)
        self.numref = (bookint, chapint, verseint)

    @property
    def book(self):
        return BOOKREFS[self.numref[0]]

    @property
    def chapter(self):
        return self.numref[1]

    @property
    def verse(self):
        return self.numref[2]

    def __unicode__(self):
        return u'%s.%s.%s' % (BOOKREFS[self.numref[0]], self.numref[1], self.numref[2])

    def __str__(self):
        return str(unicode(self))

    def __lt__(self, other):
        return self.numref < other.numref

    def __gt__(self, other):
        return self.numref > other.numref

    def __eq__(self, other):
        return self.numref == other.numref

    def __repr__(self):
        return 'Ref("%s")' % str(self)

def parse_studybible_reference(html_id):
    """
        Takes studybibles reference html_id, which is in the following formats:

            'nBBCCCVVV' (only start defined)
            'nBBCCCVVV-BBCCCVVV' (verse range defined)
            'nBBCCCVVV-BBCCCVVV BBCCCVVV-BBCCCVVV BBCCCVVV' (multiple verses/ranges defined)

        Returns OSIS reference.

    """

    if html_id == 'n36002012-outline':  # exception found in ESV Study bible epub!
        return 'Zeph.2.12'

    if html_id[0] not in 'vn':
        raise IllegalReference

    html_id = html_id[1:]  # remove first letter

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
                book = BOOKREFS[int(p[:2]) - 1]
                chap = int(p[2:5])
                ver = int(p[5:])
                osisref = '{}.{}.{}'.format(book, chap, ver)
                refs.append(osisref)

        result.append('-'.join(refs))
    return ' '.join(result)

def first_reference(ref):
    if ' ' in ref:
        ref = ref.split(' ')[0]
    if '-' in ref:
        ref = ref.split('-')[0]
    r = tuple(ref.split('.'))
    return (r[0], int(r[1]), int(r[2]))


def last_reference(ref):
    if ' ' in ref:
        ref = ref.split(' ')[-1]
    if '-' in ref:
        ref = ref.split('-')[-1]
    r = tuple(ref.split('.'))
    return (r[0], int(r[1]), int(r[2]))

def _expand_ranges(ref):
    """
    Expand ranges:
    Gen.1.1-Gen.1.3 -> Gen1.1 Gen1.2 Gen1.3
    """
    verselist = []
    if ' ' in ref:
        return ' '.join(expand_ranges(i) for i in ref.split(' '))

    firstb, firstc, firstv = first_reference(ref)
    lastb, lastc, lastv = last_reference(ref)

    firstb = BOOKREFS.index(firstb)
    lastb = BOOKREFS.index(lastb)

    if firstb == lastb and firstc == lastc:
        for i in xrange(int(firstv), int(lastv) + 1):
            verselist.append((BOOKREFS[firstb], firstc, i))
    else:
        # rest of first chapter
        book_id = firstb
        book = BOOKREFS[book_id]
        for verse in xrange(firstv, CHAPTER_LAST_VERSES['%s.%s'%(book, firstc)]+1):
            verselist.append((book, firstc, verse))

        if firstc == LAST_CHAPTERS[book]:
            book_id = firstb + 1

        # full chapters
        for book_id1 in xrange(book_id, lastb+1):
            book = BOOKREFS[book_id1]
            if book_id1 == lastb:
                if firstb != lastb:
                    first_chap = 1
                else:
                    first_chap = firstc+1
                last_chap = lastc
            else:
                first_chap = firstc+1
                last_chap = LAST_CHAPTERS[book]

            for chap in xrange(first_chap, last_chap+1):
                if book_id1 == lastb and chap == lastc:
                    last_verse = lastv
                else:
                    last_verse = CHAPTER_LAST_VERSES['%s.%s'%(book, chap)]
                for verse in xrange(1, last_verse+1):
                    verselist.append((book, chap, verse))

    result = ' '.join('%s.%s.%s' % i for i in verselist)
    return result

def expand_ranges(ref):
    """ Make sure that expanded ranges are also sorted propertly"""
    r = _expand_ranges(ref)
    return ' '.join(str(j) for j in sorted([Ref(i) for i in set(r.split(' '))]))

class Stydy2Osis(object):
    def fix_bibleref_links(self, input_soup):
        for a in input_soup.find_all('a'):
            if a['href'].startswith('http'):
                continue
            a.name = 'reference'
            url = a['href']
            file, verserange = url.split('#')
            ref = None
            if file.endswith('text.xhtml'):
                ref = parse_studybible_reference(verserange)
                if self.options.bible_work_id != 'None':
                    ref = '%s:%s' % (self.options.bible_work_id, ref)

            elif file.endswith('studynotes.xhtml'):
                try:
                    ref = '%s:%s' % (self.options.work_id, parse_studybible_reference(verserange))
                except IllegalReference:
                    a.replace_with('[%s]' % a.text)
            elif file.endswith('intros.xhtml') or file.endswith('resources.xhtml') or file.endswith('footnotes.xhtml'):
                # link may be removed
                a.replace_with('[%s]' % a.text)
            else:
                raise Exception('Link not handled %s' % file)

            if ref:
                a['osisRef'] = ref
                # Ugly (hopefully temporary) and bible hack to show link content
                # a.insert_before(a.text + ' (')
                # a.insert_after(')')
            del a['href']
            if 'onclick' in a.attrs:
                del a['onclick']

    def fix_studynote_text_tags(self, input_soup):
        for s in input_soup.find_all('small'):
            # remove BOOK - NOTE ON XXX from studynotes
            if 'NOTE ON' in s.text:
                s.extract()
            elif 'online at' in s.text or 'ESV' == s.text:
                s.unwrap()
            elif s.text in ['A.D.', 'B.C.', 'A.M.', 'P.M.']:
                s.replace_with(s.text)
            else:
                raise Exception('still some unhandled small %s', s)

        self.fix_bibleref_links(input_soup)

        # replace bolded strings
        for s in input_soup.find_all('strong'):
            s.name = 'hi'
            s['type'] = 'bold'

        for s in input_soup.find_all('h4'):
            s.name = 'div'
            s['type'] = 'paragraph'

        for i in input_soup.find_all('ol'):
            i.name = 'list'

        for i in input_soup.find_all('li'):
            i.name = 'item'

        # replace italic strings
        for s in input_soup.find_all('i'):
            s.name = 'hi'
            s['type'] = 'italic'

        # replace italic strings
        for s in input_soup.find_all('em'):
            s.name = 'hi'
            s['type'] = 'emphasis'

        # replace smallcaps
        for cls in ['smallcap', 'small-caps', 'divine-name']:
            for s in input_soup.find_all('span', class_=cls):
                s.name = 'hi'
                s['type'] = 'small-caps'

        # find outline-1 ('title' studynote covering verse range)
        # find outline-2 (bigger studynote title, verse range highlighted)
        # find outline-3 (smaller studynote title, verse range not highlighted)
        # find outline-4 (even smaller studynote title, verse range not highlighted)

        for k in ['outline-%s' % i for i in xrange(1, 5)]:
            for s in input_soup.find_all('span', class_=k):
                s.name = 'hi'
                s['type'] = 'bold'
                new_tag = self.root_soup.new_tag('hi', type='underline')
                s.wrap(new_tag)

        # find esv font definitions
        for s in input_soup.find_all('span'):
            cls = s.get('class', None)
            if cls == 'bible-version':
                assert s.text.lower() in ['esv', 'lxx', 'kjv', 'mt', 'nkjv', 'nasb'], s.text
                s.replace_with(s.text.upper())
            elif cls in ['profile-lead', 'facts-lead']:
                s.name = 'hi'
                s['type'] = 'emphasis'
            elif cls in ['good-king', 'mixture-king', 'bad-king', 'normal', None]:
                s.unwrap()
            else:
                raise Exception('span class not known %s', cls)

        for s in input_soup.find_all('hi'):
            if len(s) == 0:
                s.extract()

    def fix_table(self, table_div):
        for n in table_div.find_all('tr'):
            n.name = 'row'
        for n in table_div.find_all('th'):
            n.name = 'cell'
            n['role'] = 'label'
        for n in table_div.find_all('td'):
            n.name = 'cell'
        for p in table_div.find_all('h3'):
            p.name = 'title'

        for p in table_div.find_all('p'):
            p.name = 'div'
            p['type'] = 'paragraph'

    def fix_figure(self, img_div):
        self.fix_table(img_div)
        for img in img_div.find_all('img'):
            img.name = 'figure'
            img['src'] = img['src'].replace('../Images/', 'images/')

    def fix_fact(self, fact_div):
        for n in fact_div.find_all('h2'):
            n.name = 'title'

    def adjust_studynotes(self, body):
        for rootlevel_tag in body.children:
            if rootlevel_tag.name in ['h1', 'hr']:
                continue
            elif rootlevel_tag.name == 'div':
                cls = rootlevel_tag['class']
                if cls == 'object chart':
                    self.fix_table(rootlevel_tag)
                elif cls == 'object map':
                    self.fix_figure(rootlevel_tag)
                elif cls == 'object illustration':
                    self.fix_figure(rootlevel_tag)
                elif cls == 'object diagram':
                    self.fix_figure(rootlevel_tag)
                elif cls == 'fact':
                    self.fix_fact(rootlevel_tag)
                elif cls == 'profile':
                    self.fix_fact(rootlevel_tag)
                elif cls == 'object info':
                    self.fix_table(rootlevel_tag)
                else:
                    raise Exception('Unknown class %s' % cls)
            elif rootlevel_tag.name == 'p':
                if rootlevel_tag['class'] not in ['outline-1', 'outline-3', 'outline-4', 'study-note-continue', 'study-note']:
                    raise Exception('not handled %s' % rootlevel_tag['class'])
            elif isinstance(rootlevel_tag, NavigableString):
                continue
            elif rootlevel_tag.name == 'table':
                rootlevel_tag = rootlevel_tag.wrap(self.root_soup.new_tag('div', type='paragraph'))
                self.fix_table(rootlevel_tag)
            elif rootlevel_tag.name == 'ol':
                rootlevel_tag = rootlevel_tag.wrap(self.root_soup.new_tag('div', type='paragraph'))
            else:
                raise Exception('not handled %s' % rootlevel_tag)

            self.fix_studynote_text_tags(rootlevel_tag)
            rootlevel_tag.name = 'div'
            rootlevel_tag['type'] = 'paragraph'

            if 'id' in rootlevel_tag.attrs:
                try:
                    ref = parse_studybible_reference(rootlevel_tag['id'])
                except IllegalReference:
                    print 'not writing', rootlevel_tag
                    continue

                del rootlevel_tag['id']

                new_div = self.root_soup.new_tag('studynote')
                new_div['type'] = 'section'
                new_div['annotateType'] = 'commentary'
                new_div['annotateRef'] = ref

                rootlevel_tag.wrap(new_div)
            else:
                previous = rootlevel_tag.find_previous('studynote')
                rootlevel_tag.extract()
                previous.append(rootlevel_tag)

    def write_studynotes_into_osis(self, input_html, osistext, tag_level):
        bookdivs = {}
        chapdivs = {}
        bookdiv, chapdiv, verdiv = None, None, None
        for n in input_html.find_all('studynote'):
            n.name = 'div'
            book, chap, ver = first_reference(n['annotateRef'])
            chapref = '%s.%s' % (book, chap)
            verref = '%s.%s.%s' % (book, chap, ver)

            if tag_level >= TAGS_BOOK:
                bookdiv = bookdivs.get(book)
                if bookdiv is None:
                    bookdiv = bookdivs[book] = self.root_soup.find('div', osisID=book)
            if tag_level >= TAGS_CHAPTES:
                chapdiv = chapdivs.get(chapref)
                if chapdiv is None:
                    chapdiv = bookdiv.find('chapter', osisID=chapref)
                    if not chapdiv:
                        chapdiv = self.root_soup.new_tag('chapter', osisID=chapref)
                        bookdiv.append(chapdiv)
                    chapdivs[chapref] = chapdiv
            if tag_level >= TAGS_VERSES:
                verdiv = chapdiv.find('verse', osisID=verref)
                if not verdiv:
                    verdiv = self.root_soup.new_tag('verse', osisID=verref)
                    chapdiv.append(verdiv)

            [osistext, bookdiv, chapdiv, verdiv][tag_level].append(n)

    def add_reference_link(self, comment, link_target_comment):
        def get_final_comment(com):
            if com.replaced_by:
                return get_final_comment(com.replaced_by)
            else:
                return com

        link_target_comment = get_final_comment(link_target_comment)
        if comment != link_target_comment and link_target_comment not in comment.links:
            comment.links.append(link_target_comment)

            links = comment.find('list', cls='reference_links')
            if not links:
                links_div = self.root_soup.new_tag('div', type='paragraph', cls='reference_links')
                comment.append(links_div)
                links = self.root_soup.new_tag('list', cls='reference_links')
                links_div.append(links)

            link_item = self.root_soup.new_tag('item')
            links.append(link_item)

            bold_tag = None
            for i in xrange(4):
                if bold_tag:
                    break
                bold_tag = link_target_comment.find('hi', class_='outline-%s'%i, type='bold')
            if not bold_tag:
                bold_tag = link_target_comment.find('title')

            title_text = ''
            if bold_tag:
                title_text = bold_tag.text.strip('., ')


            ref_text = link_target_comment.find('reference').text.strip('., ')
            title_text.replace(ref_text, '')
            if link_target_comment.find('figure'):
                title_text += ', FIGURE'

            if link_target_comment.find('table'):
                title_text += ', TABLE'

            link_tag = self.root_soup.new_tag('reference', osisRef=self.options.work_id + ':' + str(verses(link_target_comment)[0]), cls='reference_links')
            note_title = 'See also note on %s'%ref_text.strip()
            if title_text:
                note_title += ' (%s)'%title_text.strip()

            link_tag.append(self.root_soup.new_string(note_title))
            link_item.append(link_tag)

    def merge_into_previous_comment(self, comment, prev_comment):
        """ if the verse is the first reference of prev_item, then merge content of this comment
            into it and remove this comment alltogether """
        comment = comment.extract()
        comment['removed'] = 1
        comment.replaced_by = prev_comment

        for tag in comment.children:
            tag['joined_from'] = comment['origRef']
            prev_comment.append(tag)

        new_verses = sorted(set(verses(comment) + verses(prev_comment)))

        for v in new_verses:
            prev_comment2 = self.verse_comment_dict.get(v)
            if not prev_comment2:
                assert 'removed' not in prev_comment.attrs
                self.verse_comment_dict[v] = prev_comment
            elif prev_comment2 in [comment, prev_comment]:
                self.verse_comment_dict[v] = prev_comment
            else:
                # some earlier, merged comment
                assert verses(prev_comment2)[0]<new_verses[0]
                self.verse_comment_dict[v] = prev_comment


        prev_comment['origRef'] += ' + ' + comment['origRef']
        prev_comment['annotateRef'] = ' '.join(str(i) for i in new_verses)

    def fix_overlapping_ranges(self, osistext):
        """
            Each bible verse can refer to only one commentary note.

            To comply with this restriction, we will
                - remove reference from first, verse range comment
                - add manual link from those removed verses to those range comments

        """
        all_comments = osistext.find_all('div', annotateType='commentary')

        # first expand all ranges
        for comment in all_comments:
            comment['origRef'] = comment['annotateRef']
            comment.links = []
            comment.replaced_by = None

            vs = verses(expand_ranges(comment['annotateRef']))

            # make figures and tables linked to some larger range: rest of this chapter as well as whole next chapter
            if comment.find('figure') or comment.find('table'):
                first = vs[0]
                last = Ref('%s.%s.%s'%(v.book, min(v.chapter+1, LAST_CHAPTERS[v.book]), CHAPTER_LAST_VERSES['%s.%s'%(first.book, first.chapter)]))
                vs2 = verses(expand_ranges('%s-%s'%(first, last)))
                vs = sorted(set(vs+vs2))

            comment['annotateRef'] = ' '.join(str(i) for i in vs)
            for v in verses(comment):
                vl = self.verse_comments_all_dict.get(v)
                if not vl:
                    vl = self.verse_comments_all_dict[v] = set()
                vl.add(comment)

        for comment in all_comments:
            if 'removed' in comment.attrs:
                # this comment has been merged earlier
                continue

            comment_verses = verses(comment)
            for v in comment_verses:
                if v in self.verse_comment_dict:
                    prev_comment = self.verse_comment_dict[v]
                    verses_for_prev = verses(prev_comment)

                    if v == verses_for_prev[0] == comment_verses[0]:
                        self.merge_into_previous_comment(comment, prev_comment)
                        break

                    if v in verses_for_prev:
                        verses_for_prev.remove(v)

                    prev_comment['annotateRef'] = ' '.join(str(i) for i in verses_for_prev)
                    self.verse_comment_dict[v] = comment

                else:
                    assert 'removed' not in comment.attrs
                    self.verse_comment_dict[v] = comment

        # Add 'see also' reference links to comments with larger range
        for ref, comment_set in self.verse_comments_all_dict.iteritems():
            main_comment = self.verse_comment_dict[ref]
            for comment in comment_set:
                if comment != main_comment:
                    self.add_reference_link(main_comment, comment)

        # Sort links
        for ref_links_list in osistext.find_all('list', cls='reference_links'):
            items = list(ref_links_list.children)
            items.sort(key=lambda x: Ref(x.reference['osisRef'].split(':')[1]))
            ref_links_list.clear()
            for i in items:
                ref_links_list.append(i)

    def __init__(self, options=None, input_dir=None):
        self.options = options
        self.input_dir = input_dir
        self.verse_comment_dict = {}
        self.verse_comments_all_dict = {} #list of comments that appear on verses

        template = jinja2.Template(open('template.xml').read())
        output_xml = BeautifulSoup(template.render(title=options.title, work_id=options.work_id), 'xml')
        self.root_soup = output_xml

    def process_files(self):
        tag_level = self.options.tag_level
        debug = self.options.debug

        print "TAG_LEVEL: %s, DEBUG: %s INPUT DIR %s" % (tag_level, debug, input_dir)
        files = sorted(
            [os.path.join(input_dir, HTMLDIRECTORY, f) for f in os.listdir(os.path.join(input_dir, HTMLDIRECTORY)) if
             f.endswith('studynotes.xhtml')])
        output_xml = self.root_soup

        osistext = output_xml.find('osisText')
        if tag_level >= TAGS_BOOK:
            ot = output_xml.new_tag('div', type='x-testament')
            matt_ref = BOOKREFS.index('Matt')
            for i in BOOKREFS[:matt_ref]:
                book = output_xml.new_tag('div', type='book', osisID=i)
                ot.append(book)
            nt = output_xml.new_tag('div', type='x-testament')
            for i in BOOKREFS[matt_ref:]:
                book = output_xml.new_tag('div', type='book', osisID=i)
                nt.append(book)
            osistext.append(ot)
            osistext.append(nt)

        if debug:
            files = files[:3] #16:18]
        for fn in files:
            print 'processing', files.index(fn), fn
            try:
                data_in = codecs.open(fn, 'r', encoding='utf-8').read()
            except Exception as e:
                print 'Error in file %s' % fn
                raise e

            input_html = BeautifulSoup(data_in, 'xml')

            body = input_html.find('body')
            self.adjust_studynotes(body)
            self.write_studynotes_into_osis(body, osistext, tag_level)

        print 'Fixing overlapping ranges'
        self.fix_overlapping_ranges(osistext)

        print 'Writing OSIS files'

        out2 = codecs.open('%s_pretty.xml' % input_dir, 'w', encoding='utf-8')
        out2.write(output_xml.prettify())
        out2.close()

        if not debug:
            out = codecs.open('%s.xml' % input_dir, 'w', encoding='utf-8')
            out.write(unicode(output_xml))
            out.close()


if __name__ == '__main__':
    parser = optparse.OptionParser(usage='Usage. %prog [options] input_dir')
    parser.add_option('--debug', action='store_true', dest='debug', default=False,
                      help='Debug mode')
    parser.add_option('--tag_level', dest='tag_level', default=0, type=int,
                      help='Tag level: 0: none, 1: book divs, 2: chapter divs, 3: verse divs')
    parser.add_option('--title', dest='title', default='ESV Study Bible Notes',
                      help='OSIS title')
    parser.add_option('--work_id', dest='work_id', default='ESVN',
                      help='OSIS work_id')
    parser.add_option('--bible_work_id', dest='bible_work_id', default='ESVS',
                      help='Bible work_id (verses are linked there). "None" -> no work_id specification')

    options, args = parser.parse_args()
    if len(args) == 1:
        input_dir = args[0]
        o = Stydy2Osis(options, input_dir)
        o.process_files()
    else:
        parser.print_help()
