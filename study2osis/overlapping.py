"""
    Copyright (C) 2015 Tuomas Airaksinen.
    See LICENCE.txt
"""
from copy import copy
import logging
import re

logger = logging.getLogger('study2osis')

from .bible_data import LAST_CHAPTERS, CHAPTER_LAST_VERSES
from .bibleref import verses, references_to_string, expand_ranges, Ref

LINK_MAX_LENGTH = 38


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


def sort_tag_content(soup, key, *args, **kwargs):
    new_contents = [i.extract() for i in soup.find_all(*args, **kwargs)] # 'item', recursive=False)]
    new_contents.sort(key=key)
    for i in new_contents:
        soup.append(i)


class FixOverlappingVersesMixin(object):
    """
    SWORD does not support overlapping verse ranges at all in commentary modules. This means
    that there cannot be two comments that are designated for one verse.

    However, in study bibles there are often comments that are designated for a larger passage,
    as well as then smaller notes for individual verses.

    My approach is to create comment of a larger verse range in the first verse of its range
    (and if there is another verse, merge these comments) and then create links from subsecuent
    verses to this verse. Approach seems to work pretty well with most SWORD applications.

    This class provides fix_overlapping_ranges() function and it's helper functions.
    """

    def fix_overlapping_ranges(self):
        """
            Each bible verse can refer to only one commentary note.

            To comply with this restriction, we will
                - remove reference from first, verse range comment
                - add manual link from those removed verses to those range comments

        """
        logger.info('Fixing overlapping ranges')
        logger.info('... process overlapping verses')
        self._process_overlapping_verses()
        if not self.options.no_nonadj:
            logger.info('... create empty comments for nonadjacent ranges (optional step)')
            self._create_empty_comments_for_nonadjancent_ranges()
        logger.info('... add reference links to strings')
        self._add_reference_links_to_comments()
        logger.info('... sort links')
        self._sort_links()

    def create_new_reference_links_list(self, target):
        links = self.root_soup.new_tag('list', cls='reference_links')
        title = self.root_soup.new_tag('title')
        title.string = 'See also'
        links.append(title)
        target.append(links)
        return links

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
                links = self.create_new_reference_links_list(comment)

            link_item = self.root_soup.new_tag('item', comment_link='1')
            links.append(link_item)
            is_fig = False
            is_tab = False

            # trying to keep lenght pretty short so that mobile phones would show only one line/link
            length = LINK_MAX_LENGTH
            if link_target_comment.find('figure'):
                length -= 3
                is_fig = True

            if link_target_comment.find('table'):
                length -= 3
                is_tab = True

            title_text = link_target_comment.text[:length].rsplit(' ', 1)[0] + '...'

            if is_fig:
                title_text += ' [F]'

            if is_tab:
                title_text += ' [T]'

            link_tag = self.root_soup.new_tag('reference', osisRef=self.work_id + ':' +
                                                                   str(verses(link_target_comment)[0]),
                                              cls='reference_links')

            link_tag.append(self.root_soup.new_string(title_text))
            link_item.append(link_tag)

    def _merge_into_previous_comment(self, comment, prev_comment):
        """ if the verse is the first reference of prev_item, then merge content of this comment
            into it and remove this comment alltogether """
        comment = comment.extract()
        comment['removed'] = 1
        comment.replaced_by = prev_comment

        for tag in list(comment.children):
            tag['joined_from'] = comment['origRef']
            prev_comment.append(tag.extract())

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
                assert verses(existing_comment)[0] < new_verses[0]
                verses_for_existing = verses(existing_comment)
                verses_for_existing.remove(v)
                existing_comment['annotateRef'] = references_to_string(verses_for_existing, sort=False)
                assert existing_comment['annotateRef']
                self.verse_comment_dict[v] = prev_comment

        prev_comment['origRef'] += ' ' + comment['origRef']
        prev_comment['annotateRef'] = ' '.join(str(i) for i in new_verses)
        assert prev_comment['annotateRef']

    def expand_all_ranges(self):
        all_comments = self.osistext.find_all('div', annotateType='commentary', recursive=False)

        # first expand all ranges
        for comment in all_comments:
            comment['origRef'] = comment['annotateRef']
            comment.links = []
            comment.replaced_by = None

            vs = expand_ranges(comment['annotateRef'], verses=True)
            comment['firstRef'] = str(vs[0])
            self.verse_comments_firstref_dict[vs[0]] = comment

            # make figures and tables linked to some larger range: rest of this chapter as well as whole next chapter
            if comment.find(re.compile('(figure|table)')):
                first = vs[0]
                chap = min(first.chapter + 1, LAST_CHAPTERS[first.book])
                ver = CHAPTER_LAST_VERSES['%s.%s' % (first.book, chap)]
                last = Ref('%s.%s.%s' % (first.book, chap, ver))
                vs2 = expand_ranges('%s-%s' % (first, last), verses=True)
                vs = sorted(set(vs + vs2))

            comment.orig_expanded = vs
            comment['annotateRef'] = ' '.join(str(i) for i in vs)
            assert comment['annotateRef']
            for v in vs:
                vl = self.verse_comments_all_dict.get(v)
                if not vl:
                    vl = self.verse_comments_all_dict[v] = set()
                vl.add(comment)

    def _process_overlapping_verses(self):
        all_comments = self.osistext.find_all('div', annotateType='commentary', recursive=False)
        for comment in all_comments:
            if 'removed' in comment.attrs:
                # this comment has been merged earlier
                continue

            comment_verses = verses(comment)
            for v in copy(comment_verses):
                prev_comment = self.verse_comment_dict.get(v)
                if prev_comment:
                    verses_for_prev = verses(prev_comment)
                    if v == verses_for_prev[0] == comment_verses[0]:
                        self._merge_into_previous_comment(comment, prev_comment)
                        break

                    if v in verses_for_prev:
                        verses_for_prev.remove(v)

                    prev_comment['annotateRef'] = ' '.join(str(i) for i in verses_for_prev)
                    assert prev_comment['annotateRef']
                    self.verse_comment_dict[v] = comment

                else:
                    assert 'removed' not in comment.attrs
                    self.verse_comment_dict[v] = comment

            comment['annotateRef'] = ' '.join(str(i) for i in comment_verses)

    def _create_empty_comments_for_nonadjancent_ranges(self):
        """
            In this step, we create empty comments for those verses that belong to larger
            verse range but for which there are also individual comments before
            this verse (i.e. verse range is not continuous).
            Empty comment is needed for adding links to that.
                    Step is optional -- if we leave this step, then those verses will be linked
            to the original verse in its range
        """
        all_comments = self.osistext.find_all('div', annotateType='commentary', recursive=False)
        for comment in all_comments:
            orig_verses = comment.orig_expanded
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
            assert comment['annotateRef']

    def _add_reference_links_to_comments(self):
        # Add 'see also' reference links to comments with larger range
        for ref, comment_set in self.verse_comments_all_dict.items():
            main_comment = self.verse_comment_dict[ref]
            for comment in comment_set:
                if comment != main_comment:
                    self._add_reference_link(main_comment, comment)

    def _sort_links(self):
        # Sort links
        for ref_links_list in self.osistext.find_all('list', cls='reference_links'):
            ref_links_list.parent.append(ref_links_list.extract()) # make sure this list is last
            sort_tag_content(ref_links_list, lambda x: Ref(x.reference['osisRef']), 'item', comment_link=True)

    def _create_empty_comment(self, verses):
        if isinstance(verses, (list, set)):
            verses = references_to_string(verses)
        verses = str(verses)

        comment = self.root_soup.new_tag('div', annotateType='commentary', type='section', annotateRef=verses,
                                         new_empty='1')
        comment.links = []
        comment['origRef'] = comment['annotateRef']
        comment.orig_expanded = expand_ranges(verses, verses=True)
        comment['origFile'] = self.current_filename
        comment.replaced_by = None
        return comment
