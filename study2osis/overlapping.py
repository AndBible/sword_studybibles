"""
    Copyright (C) 2015 Tuomas Airaksinen.
    See LICENCE.txt
"""
from copy import copy
import logging

logger = logging.getLogger('study2osis')

from .bible_data import LAST_CHAPTERS, CHAPTER_LAST_VERSES
from .bibleref import verses, references_to_string, expand_ranges, Ref

def find_subranges(orig_verses, actual_verses):
    ranges = []
    r = []
    for ov in orig_verses:
        if ov not in actual_verses:
            if r:
                ranges.append(r)
                r = []
            continue
        r.append(ov)
    if r:
        ranges.append(r)
    return ranges

class FixOverlappingVersesMixin(object):
    """
    Provides fix_overlapping_ranges() function and it's helpers to Study2Osis class
    """

    def fix_overlapping_ranges(self):
        """
            Each bible verse can refer to only one commentary note.

            To comply with this restriction, we will
                - remove reference from first, verse range comment
                - add manual link from those removed verses to those range comments

        """
        logger.info('Fixing overlapping ranges')
        logger.info('... expand all ranges')
        self._expand_all_ranges()
        logger.info('... process overlapping verses')
        self._process_overlapping_verses()
        if not self.options.no_nonadj:
            logger.info('... create empty comments for nonadjacent ranges (optional step)')
            self._create_empty_comments_for_nonadjancent_ranges()
        logger.info('... add reference links to strings')
        self._add_reference_links_to_comments()
        logger.info('... sort links')
        self._sort_links()

    def _add_reference_link(self, comment, link_target_comment):
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
            if len(title_text) > 35:
                title_text = title_text[:35].rsplit(' ', 1)[0]+'...'
            if link_target_comment.find('figure'):
                title_text += ', FIGURE'

            if link_target_comment.find('table'):
                title_text += ', TABLE'

            link_tag = self.root_soup.new_tag('reference', osisRef=self.options.work_id + ':' +
                                              str(verses(link_target_comment)[0]), cls='reference_links')
            note_title = 'Cf. %s'%ref_text.strip()
            if title_text:
                note_title += ' (%s)'%title_text.strip()

            link_tag.append(self.root_soup.new_string(note_title))
            link_item.append(link_tag)

    def _merge_into_previous_comment(self, comment, prev_comment):
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
            existing_comment = self.verse_comment_dict.get(v)
            if not existing_comment:
                assert 'removed' not in prev_comment.attrs
                self.verse_comment_dict[v] = prev_comment
            elif existing_comment == prev_comment:
                pass
            elif existing_comment == comment:
                self.verse_comment_dict[v] = prev_comment
            else:
                # some earlier, merged comment
                assert verses(existing_comment)[0]<new_verses[0]
                verses_for_existing = verses(existing_comment)
                verses_for_existing.remove(v)
                existing_comment['annotateRef'] = references_to_string(verses_for_existing)
                self.verse_comment_dict[v] = prev_comment


        prev_comment['origRef'] += ' ' + comment['origRef']
        prev_comment['annotateRef'] = ' '.join(str(i) for i in new_verses)


    def _expand_all_ranges(self):
        all_comments = self.osistext.find_all('div', annotateType='commentary')

        # first expand all ranges
        for comment in all_comments:
            comment['origRef'] = comment['annotateRef']
            comment.links = []
            comment.replaced_by = None

            vs = verses(expand_ranges(comment['annotateRef']))

            # make figures and tables linked to some larger range: rest of this chapter as well as whole next chapter
            if comment.find('figure') or comment.find('table'):
                first = vs[0]
                last = Ref('%s.%s.%s'%(v.book, min(v.chapter+1, LAST_CHAPTERS[v.book]),
                                      CHAPTER_LAST_VERSES['%s.%s'%(first.book, first.chapter)]))
                vs2 = verses(expand_ranges('%s-%s'%(first, last)))
                vs = sorted(set(vs+vs2))

            comment['annotateRef'] = ' '.join(str(i) for i in vs)
            for v in verses(comment):
                vl = self.verse_comments_all_dict.get(v)
                if not vl:
                    vl = self.verse_comments_all_dict[v] = set()
                vl.add(comment)

    def _process_overlapping_verses(self):
        all_comments = self.osistext.find_all('div', annotateType='commentary')
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
                        self._merge_into_previous_comment(comment, prev_comment)
                        break

                    if v in verses_for_prev:
                        verses_for_prev.remove(v)

                    prev_comment['annotateRef'] = ' '.join(str(i) for i in verses_for_prev)
                    self.verse_comment_dict[v] = comment

                else:
                    assert 'removed' not in comment.attrs
                    self.verse_comment_dict[v] = comment


    def _create_empty_comments_for_nonadjancent_ranges(self):
        """
            In this step, we create empty comments for those verses that belong to larger
            verse range but for which there are also individual comments before
            this verse (i.e. verse range is not continuous).
            Empty comment is needed for adding links to that.
                    Step is optional -- if we leave this step, then those verses will be linked
            to the original verse in its range
        """
        all_comments = self.osistext.find_all('div', annotateType='commentary')
        for comment in all_comments:
            orig_verses = verses(expand_ranges(comment['origRef']))
            actual_verses = verses(comment)
            new_actual_verses = set(copy(actual_verses))

            for rng in find_subranges(orig_verses, actual_verses)[1:]:
                empty_comment = self._create_empty_comment(rng)
                for v in rng:
                    assert self.verse_comment_dict[v] == comment
                    self.verse_comment_dict[v] = empty_comment
                new_actual_verses -= set(rng)
                comment.insert_after(empty_comment)
            comment['annotateRef'] = references_to_string(new_actual_verses)


    def _add_reference_links_to_comments(self):
        # Add 'see also' reference links to comments with larger range
        for ref, comment_set in self.verse_comments_all_dict.iteritems():
            main_comment = self.verse_comment_dict[ref]
            for comment in comment_set:
                if comment != main_comment:
                    self._add_reference_link(main_comment, comment)

    def _sort_links(self):
        # Sort links
        for ref_links_list in self.osistext.find_all('list', cls='reference_links'):
            items = list(ref_links_list.children)
            items.sort(key=lambda x: Ref(x.reference['osisRef'].split(':')[1]))
            ref_links_list.clear()
            for i in items:
                ref_links_list.append(i)

    def _create_empty_comment(self, verse):
        if isinstance(verse, (list, set)):
            verse = references_to_string(verse)
        verse = str(verse)

        comment = self.root_soup.new_tag('div', annotateType='commentary', type='section', annotateRef=verse, new_empty='1')
        comment.links = []
        comment['origRef'] = comment['annotateRef']
        comment.replaced_by = None
        return comment