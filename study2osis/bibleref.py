"""
    Copyright (C) 2015 Tuomas Airaksinen.
    See LICENCE.txt
"""
from functools import wraps

from bs4 import Tag

from .bible_data import BOOKREFS, CHAPTER_LAST_VERSES, LAST_CHAPTERS


class IllegalReference(Exception):
    pass


def cached_refs(cls):
    instances = {}

    @wraps(cls)
    def getinstance(*args):
        assert args
        if len(args) == 1:
            ref_string, = args
        else:
            ref_string = args

        if isinstance(ref_string, (list, tuple)):
            ref_string = '%s.%s.%s' % tuple(ref_string)
        if isinstance(ref_string, Ref.orig_cls):
            return ref_string
        assert isinstance(ref_string, (str, unicode))
        if ':' in ref_string:
            ref_string = ref_string.split(':')[1]
        if ref_string not in instances:
            instances[ref_string] = cls(ref_string)
        return instances[ref_string]

    getinstance.orig_cls = cls
    return getinstance




@cached_refs
class Ref(object):
    class LastVerse(Exception):
        pass

    def __init__(self, *args):
        ref_string, = args
        book, chap, verse = ref_string.split('.')
        bookint = BOOKREFS.index(book)
        chapint = int(chap)
        verseint = int(verse)
        self.numref = (bookint, chapint, verseint)

    @property
    def book(self):
        return BOOKREFS[self.numref[0]]

    @property
    def book_int(self):
        return self.numref[0]

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

    def __gt__(self, other):
        return self.numref > other.numref

    def __ge__(self, other):
        return self.numref > other.numref or self.numref == other.numref

    def __eq__(self, other):
        return self.numref == other.numref

    def __repr__(self):
        return 'Ref("%s")' % str(self)

    def next(self):
        if self.verse < CHAPTER_LAST_VERSES['%s.%s' % (self.book, self.chapter)]:
            return Ref('%s.%s.%s' % (self.book, self.chapter, self.verse + 1))
        elif self.chapter < LAST_CHAPTERS[self.book]:
            return Ref('%s.%s.%s' % (self.book, self.chapter + 1, 1))
        elif self.book != 'Rev':
            return Ref('%s.%s.%s' % (BOOKREFS[self.book_int + 1], 1, 1))
        else:
            raise self.LastVerse

    def iter(self):
        n = self
        while True:
            yield n
            try:
                n = n.next()
            except self.LastVerse:
                break


def verses(a):
    if isinstance(a, Tag):
        a = a['annotateRef']
    return sorted([Ref(i) for i in a.split(' ')])


def xrefrange(start, stop):
    start = Ref(start)
    stop = Ref(stop)
    if stop < start:
        return
    for i in start.iter():
        if i > stop:
            return
        yield i


def refrange(start, stop):
    return list(xrefrange(start, stop))


def references_to_string(vs, sort=True):
    if sort:
        return ' '.join(str(i) for i in sorted(vs))
    else:
        return ' '.join(str(i) for i in vs)


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
        for verse in xrange(firstv, CHAPTER_LAST_VERSES['%s.%s' % (book, firstc)] + 1):
            verselist.append((book, firstc, verse))

        if firstc == LAST_CHAPTERS[book]:
            book_id = firstb + 1

        # full chapters
        for book_id1 in xrange(book_id, lastb + 1):
            book = BOOKREFS[book_id1]
            if book_id1 == lastb:
                if firstb != lastb:
                    first_chap = 1
                else:
                    first_chap = firstc + 1
                last_chap = lastc
            else:
                first_chap = firstc + 1
                last_chap = LAST_CHAPTERS[book]

            for chap in xrange(first_chap, last_chap + 1):
                if book_id1 == lastb and chap == lastc:
                    last_verse = lastv
                else:
                    last_verse = CHAPTER_LAST_VERSES['%s.%s' % (book, chap)]
                for verse in xrange(1, last_verse + 1):
                    verselist.append((book, chap, verse))

    result = ' '.join('%s.%s.%s' % i for i in verselist)
    return result


def expand_ranges(ref, verses=False):
    """ Make sure that expanded ranges are also sorted propertly"""
    r = _expand_ranges(ref)
    if verses:
        return sorted([Ref(i) for i in set(r.split(' '))])
    else:
        return ' '.join(str(j) for j in sorted([Ref(i) for i in set(r.split(' '))]))
