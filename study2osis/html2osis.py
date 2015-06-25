# encoding: utf-8
"""
    Copyright (C) 2014 Tuomas Airaksinen.
    See LICENCE.txt
"""

import logging
import re

from bs4 import NavigableString

logger = logging.getLogger('html2osis')

from .bible_data import BOOKREFS
from .bibleref import IllegalReference, first_reference, Ref


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

    def _guess_range_end(self, ref, link_tag):
        """
            This is not an easy task to implement robustly such that all cases are
            handled, but at least certain clear cases can be easily done.
        """
        tag_content = link_tag.text.strip().replace(u'–', '-')

        m = re.match(r'^(\d+)[a-e]$', tag_content) # '1', (must be verse)
        if m:
            return None

        m = re.match(r'^(\d+)$', tag_content) # '1', can mean either chapter or verse
        if m:
            return None

        m = re.match(r'^(Chapter|ch\.) (\d+)$', tag_content) # 'Chapter 1', 'ch. 1'
        if m:
            startchap, = (int(i) for i in m.groups()[1:])
            assert startchap == ref.chapter
            assert ref.verse == 1
            return None


        m = re.match(r'^(Chapters|chs\.) (\d+)-(\d+)$', tag_content) # 'chs. 1-2'
        if m:
            startchap, endchap = (int(i) for i in m.groups()[1:])
            assert startchap == ref.chapter
            assert ref.verse == 1
            return None

        m = re.match(r'^(\d+)-(\d+)$', tag_content) # '1-3', can mean either chapter or verse
        if m:
            return None

        m = re.match(r'^(v\.|Verse) (\d+)[a-e]?$', tag_content) # 'v. 1'
        if m:
            startver, = (int(i) for i in m.groups()[1:])
            assert startver == ref.verse
            return None

        m = re.match(r'^(\d+):(\d+)[a-e]?$', tag_content) # '1:1'
        if m:
            startchap, startver = (int(i) for i in  m.groups())
            assert startchap == ref.chapter
            assert startver == ref.verse
            return None

        m = re.match(r'^vv\.? (\d+)[a-e]?$', tag_content) # 'vv. 1'
        if m:
            startver, = (int(i) for i in  m.groups())
            assert startver == ref.verse
            return None

        m = re.match(r'^vv\.? (\d+)[a-e]?-(\d+)[a-e]?$', tag_content) # 'vv. 1-3'
        if m:
            startver, endver = (int(i) for i in  m.groups())
            assert startver == ref.verse
            return Ref(ref.book, ref.chapter, endver)

        m = re.match(r'^(\d+):(\d+)[a-e]?-(\d+)[a-e]?$', tag_content) # '1:1-3'
        if m:
            startchap, startver, endver = (int(i) for i in  m.groups())
            assert startchap == ref.chapter
            assert startver == ref.verse
            return Ref(ref.book, ref.chapter, endver)

        m = re.match(r'^(\d+):(\d+)[a-e]?-(\d+):(\d+)[a-e]?$', tag_content) # '11:1-12:10'
        if m:
            startchap, startver, endchap, endver = (int(i) for i in  m.groups())
            assert startchap == ref.chapter
            assert startver == ref.verse
            return Ref(ref.book, endchap, endver)


        m = re.match(r'^[\w \.]+ (\d+):(\d+)[a-e]?-(\d+)[a-e]?$', tag_content) # 'Isa. 11:1-10'
        if m:
            startchap, startver, endver = (int(i) for i in  m.groups())
            assert startchap == ref.chapter
            assert startver == ref.verse
            return Ref(ref.book, ref.chapter, endver)

        m = re.match(r'^[\w \.]+ (\d+):(\d+)[a-e]?-(\d+):(\d+)[a-e]?$', tag_content) # 'Isa. 11:1-12:10'
        if m:
            startchap, startver, endchap, endver = (int(i) for i in  m.groups())
            assert startchap == ref.chapter
            assert startver == ref.verse
            return Ref(ref.book, endchap, endver)

#        m = re.match(r'^(Philem|2 John|Jude) (\d+)$', tag_content) # 'Jude 1 (jude 1:1)
#        if m:
#            startver, = (int(i) for i in m.groups()[1:])
#            assert startver == ref.verse
#            return None
#
#        m = re.match(r'^[\w \.]+ (\d+):(\d+)[a-e]?$', tag_content) # 'Matt 1:1'
#        if m:
#            startchap, startver = (int(i) for i in  m.groups())
#            assert startchap == ref.chapter
#            assert startver == ref.verse
#            return None
#
#        m = re.match(r'^([\w \.]+) (\d+)-(\d+)$', tag_content) # 'Matt. 1-2
#        if m:
#            startchap, endchap = (int(i) for i in m.groups()[1:])
#            assert startchap == ref.chapter
#            assert ref.verse == 1
#            return None
#
#        m = re.match(r'^([\w \.]+) (\d+)$', tag_content) # 'Matt. 1
#        if m:
#            startchap, = (int(i) for i in m.groups()[1:])
#            assert startchap == ref.chapter
#            assert ref.verse == 1
#            return None

        # There are many other (not so common) cases too. Let's handle these more common ones only.
        return None

    def _try_to_get_range(self, ref, linktag):
        endref = None
        try:
            endref = self._guess_range_end(ref, linktag)
        except AssertionError as e:
            logger.warning('Conflicting information in _guess_range_end(%s, %s): %s', ref, linktag.text, e)

        if endref:
            return '%s-%s'%(ref, endref)
        else:
            return '%s'%ref

    def _fix_bibleref_links(self, input_soup):
        for a in input_soup.find_all('a'):
            if a['href'].startswith('http'):
                continue
            a.name = 'reference'
            url = a['href']
            if '#' in url:
                filename, verserange = url.split('#')
            else:
                filename = url
                verserange = ''
            ref = None
            if filename.endswith('text.xhtml'):
                ref = parse_studybible_reference(verserange)
                ref = self._try_to_get_range(Ref(ref), a)
                if self.options.bible_work_id != 'None':
                    ref = '%s:%s' % (self.options.bible_work_id, ref)

            elif filename.endswith('studynotes.xhtml'):
                try:
                    ref = '%s:%s' % (self.work_id, parse_studybible_reference(verserange))
                except IllegalReference:
                    a['postpone'] = '1'
                    a['origRef'] = a['href']
            elif any([filename.endswith(i) for i in ['footnotes.xhtml', 'main.xhtml', 'preferences.xhtml']]):
                logger.warning('Link not handled %s, %s', filename, a.text)
                a.replace_with('[%s]' % a.text)
            elif any([filename.endswith(i) for i in ['intros.xhtml', 'resources.xhtml']]):
                a['postpone'] = '1'
                a['origRef'] = a['href']
            else:
                logger.error('Link not handled %s, %s', filename, a.text)
                a.replace_with('[%s]' % a.text)

            if ref:
                a['osisRef'] = ref
                # Ugly (hopefully temporary) and bible hack to show link content
                # a.insert_before(a.text + ' (')
                # a.insert_after(')')
            del a['href']
            if 'onclick' in a.attrs:
                del a['onclick']

    def _fix_text_tags(self, input_soup):

        self._fix_bibleref_links(input_soup)

        for s in input_soup.find_all():
            if s.name == 'small':
                # remove BOOK - NOTE ON XXX from studynotes
                if 'NOTE ON' in s.text:
                    s.extract()
                elif 'online at' in s.text or 'ESV' == s.text:
                    s['unwrap'] = '1'
                elif s.text in ['A.D.', 'B.C.', 'A.M.', 'P.M.', 'KJV']:
                    s.replace_with(s.text)
                else:
                    s.replace_with(s.text)
                    logger.error('still some unhandled small %s', s)


            # replace bolded strings
            elif s.name == 'strong':
                s.name = 'hi'
                s['type'] = 'bold'

            elif s.name == 'sup':
                s.name = 'hi'
                s['type'] = 'super'

            elif s.name in ['h4', 'h5']:
                logger.warning('h4 or h5 tag used: %s', s)
                s.name = 'title'
            # s.name = 'div'
            #    s['type'] = 'paragraph'

            elif s.name in ['ol', 'ul']:
                s.name = 'list'

            elif s.name == 'br':
                s.name = 'lb'

            # some tags that can be completely unwrapped
            elif s.name in ['blockquote', 'hr', 'colgroup', 'col']:
                s['unwrap'] = '1'

            elif s.name == 'li':
                s.name = 'item'

            elif s.name == 'p':
                if s.attrs.get('class', '') == 'glossary-word':
                    s.name = 'title'
                    s.find_next_sibling('p', class_='glossary-entry').insert(0, s.extract())

            # replace italic strings
            elif s.name in ['i', 'cite']:
                s.name = 'hi'
                s['type'] = 'italic'

            # replace emphasized strings
            elif s.name == 'em':
                s.name = 'hi'
                s['type'] = 'bold'

            # replace smallcaps
            elif s.name == 'span':
                cls = s.attrs.get('class')
                if cls in ['smallcap', 'small-caps', 'divine-name']:
                    s.name = 'hi'
                    s['type'] = 'small-caps'

                # find outline-1 ('title' studynote covering verse range)
                # find outline-2 (bigger studynote title, verse range highlighted)
                # find outline-3 (smaller studynote title, verse range not highlighted)
                # find outline-4 (even smaller studynote title, verse range not highlighted)

                elif cls in ['outline-%s' % i for i in xrange(1, 5)]:
                    s.name = 'hi'
                    s['type'] = 'bold'
                    new_tag = self.root_soup.new_tag('hi', type='underline')
                    s.wrap(new_tag)

                # find esv font definitions
                elif cls == 'bible-version':
                    assert s.text.lower() in ['esv', 'lxx', 'kjv', 'mt', 'nkjv', 'nasb'], s.text
                    s.replace_with(s.text.upper())
                elif cls in ['h3-inline', 'initial', 'profile-lead', 'facts-lead']:
                    s.name = 'hi'
                    s['type'] = 'bold'
                elif cls in ['good-king', 'mixture-king', 'bad-king', 'normal', 'smaller',
                             'hebrew', 'paleo-hebrew-unicode', 'major-prophet', 'minor-prophet',
                             'footnote', 'crossref', 'contributor-country', 'time', None]:
                    s['unwrap'] = '1'
                elif cls in ['underline']:
                    s.name = 'hi'
                    s['type'] = 'underline'
                else:
                    logger.warning('Span class not known %s, in %s', cls, s)
                    s['unwrap'] = '1'

        # find all hi's without content and remove them
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
            p['origFile'] = self.current_filename

        for p in table_div.find_all('p'):
            p.name = 'div'
            p['type'] = 'paragraph'

    def _fix_figure_and_table(self, img_div):
        self._fix_table(img_div)
        for img in img_div.find_all('img'):
            img.name = 'figure'
            img['src'] = img['src'].replace('../Images/', self.images_path)
            self.images.append(img['src'].split('/')[-1])

    def _fix_fact(self, fact_div):
        for n in fact_div.find_all('h2'):
            n.name = 'title'
            n['origFile'] = self.current_filename

    def _all_fixes(self, soup):
        self._fix_text_tags(soup)
        self._fix_figure_and_table(soup)

    def _adjust_studynotes(self):
        for rootlevel_tag in self.osistext.find_all(recursive=False, origFile=True):
            self.current_filename = rootlevel_tag['origFile']
            move_to_first_verse = False
            if rootlevel_tag.name in ['h1', 'hr']:
                rootlevel_tag['wrap'] = '1'
            elif rootlevel_tag.name == 'header':
                continue
            elif isinstance(rootlevel_tag, NavigableString):
                assert str(rootlevel_tag).strip() == ''
                rootlevel_tag.extract()
                continue
            elif rootlevel_tag.name == 'div':
                cls = rootlevel_tag['class']
                if cls.startswith('object '):
                    type = cls.split(' ')[1]
                    if type not in ['chart', 'map', 'illustration', 'diagram', 'info']:
                        logger.error('Unknown object type')
                    self._fix_figure_and_table(rootlevel_tag)
                    move_to_first_verse = True
                elif cls == 'fact':
                    self._fix_fact(rootlevel_tag)
                elif cls == 'profile':
                    self._fix_fact(rootlevel_tag)
                else:
                    logger.error('Unknown div class %s', cls)
            elif rootlevel_tag.name == 'p':
                if rootlevel_tag['class'] not in ['outline-1', 'outline-3', 'outline-4', 'study-note-continue',
                                                  'study-note']:
                    logger.error('not handled %s', rootlevel_tag['class'])
            elif rootlevel_tag.name == 'table':
                rootlevel_tag = rootlevel_tag.wrap(self.root_soup.new_tag('div', type='paragraph'))
                self._fix_table(rootlevel_tag)
            elif rootlevel_tag.name == 'ol':
                rootlevel_tag = rootlevel_tag.wrap(self.root_soup.new_tag('div', type='paragraph'))
            else:
                logger.error('Not handled %s', rootlevel_tag)

            self._fix_text_tags(rootlevel_tag)
            rootlevel_tag.name = 'div'
            rootlevel_tag['type'] = 'paragraph'

            if 'id' in rootlevel_tag.attrs:
                try:
                    ref = parse_studybible_reference(rootlevel_tag['id'])
                except IllegalReference:
                    # let's silence this single warning about 'Studynotes for *' titles, one per bible book
                    if rootlevel_tag['id'].endswith('-studynotes') and rootlevel_tag.attrs.get('wrap') and len(list(rootlevel_tag.find_all())) == 0:
                        pass
                    else:
                        logger.warning('NOT writing %s', rootlevel_tag)
                    rootlevel_tag.extract()
                    continue

                del rootlevel_tag['id']

                new_div = self.root_soup.new_tag('div')
                new_div['type'] = 'section'
                new_div['annotateType'] = 'commentary'
                new_div['annotateRef'] = ref

                rootlevel_tag.wrap(new_div)
            else:
                if move_to_first_verse:
                    now = previous = rootlevel_tag.find_previous_sibling('div', annotateType='commentary')
                    r = Ref(first_reference(previous['annotateRef']))
                    chapter = r.chapter
                    # find earliest studynote that is in this same chapter and add figure / table there
                    while r.chapter == chapter:
                        now = previous
                        previous = previous.find_previous_sibling('div', annotateType='commentary')
                        r = Ref(first_reference(previous['annotateRef']))
                    previous = now
                #
                else:
                    previous = rootlevel_tag.find_previous_sibling('div', annotateType='commentary')
                #                previous = rootlevel_tag.find_previous_sibling('div', annotateType='commentary')
                rootlevel_tag.extract()
                previous.append(rootlevel_tag)

    def _write_studynotes_into_osis(self, input_html):
        for n in input_html.find_all('studynote', recursive=False):
            n.name = 'div'
            n['origFile'] = self.current_filename
            self.osistext.append(n)
