"""
    Copyright (C) 2014 Tuomas Airaksinen.
    See LICENCE.txt
"""

import logging
from bs4 import NavigableString

logger = logging.getLogger('html2osis')

from .bible_data import BOOKREFS, TAGS_BOOK, TAGS_CHAPTES, TAGS_VERSES
from .bibleref import IllegalReference, first_reference


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

class HTML2OsisMixin(object):
    """
        HTML to OSIS fixes
    """
    def _fix_bibleref_links(self, input_soup):
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
                logger.error('Link not handled %s', file)

            if ref:
                a['osisRef'] = ref
                # Ugly (hopefully temporary) and bible hack to show link content
                # a.insert_before(a.text + ' (')
                # a.insert_after(')')
            del a['href']
            if 'onclick' in a.attrs:
                del a['onclick']

    def _fix_studynote_text_tags(self, input_soup):
        for s in input_soup.find_all('small'):
            # remove BOOK - NOTE ON XXX from studynotes
            if 'NOTE ON' in s.text:
                s.extract()
            elif 'online at' in s.text or 'ESV' == s.text:
                s.unwrap()
            elif s.text in ['A.D.', 'B.C.', 'A.M.', 'P.M.']:
                s.replace_with(s.text)
            else:
                logger.error('still some unhandled small %s', s)

        self._fix_bibleref_links(input_soup)

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
                s.unwrap()
                logger.error('span class not known %s', cls)

        for s in input_soup.find_all('hi'):
            if len(s) == 0:
                s.extract()

    def _fix_table(self, table_div):
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

    def _fix_figure(self, img_div):
        self._fix_table(img_div)
        for img in img_div.find_all('img'):
            img.name = 'figure'
            img['src'] = img['src'].replace('../Images/', 'images/')
            self.images.append(img['src'].split('/')[-1])

    def fix_fact(self, fact_div):
        for n in fact_div.find_all('h2'):
            n.name = 'title'

    def _adjust_studynotes(self, body):
        for rootlevel_tag in body.children:
            if rootlevel_tag.name in ['h1', 'hr']:
                continue
            elif rootlevel_tag.name == 'div':
                cls = rootlevel_tag['class']
                if cls == 'object chart':
                    self._fix_table(rootlevel_tag)
                elif cls == 'object map':
                    self._fix_figure(rootlevel_tag)
                elif cls == 'object illustration':
                    self._fix_figure(rootlevel_tag)
                elif cls == 'object diagram':
                    self._fix_figure(rootlevel_tag)
                elif cls == 'fact':
                    self.fix_fact(rootlevel_tag)
                elif cls == 'profile':
                    self.fix_fact(rootlevel_tag)
                elif cls == 'object info':
                    self._fix_table(rootlevel_tag)
                else:
                    logger.error('Unknown div class %s', cls)
            elif rootlevel_tag.name == 'p':
                if rootlevel_tag['class'] not in ['outline-1', 'outline-3', 'outline-4', 'study-note-continue', 'study-note']:
                    logger.error('not handled %s', rootlevel_tag['class'])
            elif isinstance(rootlevel_tag, NavigableString):
                continue
            elif rootlevel_tag.name == 'table':
                rootlevel_tag = rootlevel_tag.wrap(self.root_soup.new_tag('div', type='paragraph'))
                self._fix_table(rootlevel_tag)
            elif rootlevel_tag.name == 'ol':
                rootlevel_tag = rootlevel_tag.wrap(self.root_soup.new_tag('div', type='paragraph'))
            else:
                logger.error('Not handled %s', rootlevel_tag)

            self._fix_studynote_text_tags(rootlevel_tag)
            rootlevel_tag.name = 'div'
            rootlevel_tag['type'] = 'paragraph'

            if 'id' in rootlevel_tag.attrs:
                try:
                    ref = parse_studybible_reference(rootlevel_tag['id'])
                except IllegalReference:
                    logger.error('NOT writing %s', rootlevel_tag)
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

    def _write_studynotes_into_osis(self, input_html):
        tag_level = self.options.tag_level
        osistext = self.osistext
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

