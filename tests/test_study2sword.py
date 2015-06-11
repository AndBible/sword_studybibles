"""
    Copyright (C) 2015 Tuomas Airaksinen.
    See LICENCE.txt
"""
from study2osis.overlapping import find_subranges

from study2osis.study2osis import Study2Osis, parse_studybible_reference
from study2osis.bibleref import Ref, expand_ranges, first_reference, last_reference, xrefrange, refrange
from bs4 import BeautifulSoup

def com_text(osistext, ref):
    com = osistext.find_all('div', annotateRef=str(ref))
    assert len(com) == 1
    com = com[0]
    return com.text

def link_refs(osistext, ref):
    com = osistext.find_all('div', annotateRef=str(ref))
    assert len(com) == 1
    com = com[0]
    link = com.find('list', cls='reference_links')
    if link:
        return set([Ref(i['osisRef'][5:]) for i in link.find_all('reference')])
    else:
        return set()

class options:
    title = 'ESVN'
    work_id = 'ESVN'
    no_nonadj = False
    tag_level = 0

def test_overlapping_1():
    osistext = BeautifulSoup("""
        <osisText>
        <div annotateRef="Gen.1.1-Gen.1.4" annotateType="commentary"><reference>blah1</reference></div>
        <div annotateRef="Gen.1.2-Gen.1.4" annotateType="commentary"><reference>blah2</reference></div>
        <div annotateRef="Gen.1.3" annotateType="commentary"><reference>blah3</reference></div>
        </osisText>
    """, 'xml')

    s = Study2Osis(options)
    s.root_soup = s.osistext = osistext
    s.fix_overlapping_ranges()
    result = osistext.prettify()
    print result
    assert link_refs(osistext, 'Gen.1.1') == set()
    assert link_refs(osistext, 'Gen.1.2') == {Ref('Gen.1.1')}
    assert link_refs(osistext, 'Gen.1.3') == {Ref('Gen.1.1'), Ref('Gen.1.2')}
    assert link_refs(osistext, 'Gen.1.4') == {Ref('Gen.1.1'), Ref('Gen.1.2')}

def test_merge_comments():
    osistext = BeautifulSoup("""
        <osisText>
        <div annotateRef="Gen.1.1-Gen.1.4" annotateType="commentary"><reference>blah1</reference></div>
        <div annotateRef="Gen.1.2-Gen.1.4" annotateType="commentary"><reference>blah2</reference></div>
        <div annotateRef="Gen.1.2" annotateType="commentary"><reference>blah3</reference></div>
        <div annotateRef="Gen.1.3" annotateType="commentary"><reference>blah4</reference></div>
        </osisText>
    """, 'xml')

    s = Study2Osis(options)
    s.root_soup = s.osistext = osistext
    s.fix_overlapping_ranges()
    result = osistext.prettify()
    print result
    assert link_refs(osistext, 'Gen.1.1') == set()
    assert link_refs(osistext, 'Gen.1.2') == {Ref('Gen.1.1')}
    assert link_refs(osistext, 'Gen.1.4') == {Ref('Gen.1.1'), Ref('Gen.1.2')}


def test_commentless_verse_within_rangecomment():
    osistext = BeautifulSoup("""
        <osisText>
        <div annotateRef="Gen.1.1-Gen.1.4" annotateType="commentary"><reference>blah1</reference></div>
        <div annotateRef="Gen.1.2" annotateType="commentary"><reference>blah2</reference></div>

        <div annotateRef="Gen.1.4" annotateType="commentary"><reference>blah4</reference></div>
        </osisText>
    """, 'xml')
    # here, we want to create empty comment in verse 3 and add link there (instead of linking to verse 1).

    s = Study2Osis(options)
    s.root_soup = s.osistext = osistext
    s.fix_overlapping_ranges()
    result = osistext.prettify()
    print result
    assert link_refs(osistext, 'Gen.1.1') == set()
    assert link_refs(osistext, 'Gen.1.2') == {Ref('Gen.1.1')}
    assert link_refs(osistext, 'Gen.1.3') == {Ref('Gen.1.1')}
    assert link_refs(osistext, 'Gen.1.4') == {Ref('Gen.1.1')}

def test_adjacent_verses():
    osistext = BeautifulSoup("""
        <osisText>
        <div annotateRef="Gen.1.1-Gen.1.4" annotateType="commentary"><reference>blah1</reference></div>
        <div annotateRef="Gen.1.2" annotateType="commentary"><reference>blah2</reference></div>

        <div annotateRef="Gen.1.4-Gen.1.6" annotateType="commentary"><reference>blah4</reference></div>
        </osisText>
    """, 'xml')

    s = Study2Osis(options)
    s.root_soup = s.osistext = osistext
    s.fix_overlapping_ranges()
    result = osistext.prettify()
    print result
    assert link_refs(osistext, 'Gen.1.1') == set()
    assert link_refs(osistext, 'Gen.1.2') == {Ref('Gen.1.1')}
    assert link_refs(osistext, 'Gen.1.3') == {Ref('Gen.1.1')}
    assert link_refs(osistext, 'Gen.1.4 Gen.1.5 Gen.1.6') == {Ref('Gen.1.1')}
    #assert link_refs(osistext, 'Gen.1.5') == set()
    #assert link_refs(osistext, 'Gen.1.6') == set()

    #print result
def test_expand_ranges():
    assert expand_ranges("Gen.2.4-Gen.2.6") == "Gen.2.4 Gen.2.5 Gen.2.6"
    assert expand_ranges("Gen.1.30-Gen.2.1") == "Gen.1.30 Gen.1.31 Gen.2.1"
    assert expand_ranges("Gen.50.25-Exod.1.2") == "Gen.50.25 Gen.50.26 Exod.1.1 Exod.1.2"
    assert expand_ranges("Gen.50.1-Gen.50.26") + ' ' + expand_ranges("Exod.1.1-Exod.2.5") == expand_ranges('Gen.50.1-Exod.2.5')
    assert '1Chr.1.1' not in expand_ranges('1Chr.10.1-2Chr.9.31')
    assert expand_ranges("Gen.2.4-Gen.2.6 Gen.1.30-Gen.2.1") == "Gen.1.30 Gen.1.31 Gen.2.1 Gen.2.4 Gen.2.5 Gen.2.6"

def test_first_last_reference():
    assert first_reference('Gen.1.1-Gen.1.5') == ('Gen', 1, 1)
    assert last_reference('Gen.1.1-Gen.1.5') == ('Gen', 1, 5)
    assert first_reference('Gen.1.1-Gen.1.5 Gen.2.1') == ('Gen', 1, 1)
    assert last_reference('Gen.1.1-Gen.1.5 Gen.2.1') == ('Gen', 2, 1)
    assert first_reference('Gen.1.1-Gen.1.5 Gen.2.1-Gen.2.2') == ('Gen', 1, 1)
    assert last_reference('Gen.1.1-Gen.1.5 Gen.2.1-Gen.2.2') == ('Gen', 2, 2)

def test_parse_studybible_reference():
    assert parse_studybible_reference('n66002001-66003022.66002001-66003022') == 'Rev.2.1-Rev.3.22 Rev.2.1-Rev.3.22'
    assert parse_studybible_reference('n66002001a-66003022b') == 'Rev.2.1-Rev.3.22'
    assert parse_studybible_reference('n66002001-66003022') == 'Rev.2.1-Rev.3.22'
    assert parse_studybible_reference('n66001013') == 'Rev.1.13'
    assert parse_studybible_reference('n02023001-02023003.02023006-02023008') == 'Exod.23.1-Exod.23.3 Exod.23.6-Exod.23.8'

def test_ref():
    assert Ref('Rev.1.1') > Ref('Jude.1.1')
    assert Ref('Rev.1.2') > Ref('Rev.1.1')
    assert Ref('Rev.2.1') > Ref('Rev.1.1')
    assert Ref('Gen.1.1') < Ref('Jude.1.1')
    assert '%s' % Ref('Gen.1.1') == 'Gen.1.1'
    assert '%s' % Ref('Jude.1.1') == 'Jude.1.1'
    assert Ref('Gen.1.1') == Ref('Gen.1.1')
    assert Ref('Gen.1.1') in [Ref('Gen.1.1')]
    assert Ref('Gen.1.1') in {Ref('Gen.1.1'): 1}
    assert sorted([Ref('Gen.1.1'), Ref('Gen.2.1')]) == [Ref("Gen.1.1"), Ref("Gen.2.1")]
    assert sorted([Ref('Gen.1.1'), Ref('Exod.2.1')]) == [Ref("Gen.1.1"), Ref("Exod.2.1")]
    assert sorted([Ref('Rev.1.1'), Ref('Exod.2.1')]) == [Ref("Exod.2.1"), Ref("Rev.1.1")]
    assert Ref('Gen.1.1').next() == Ref('Gen.1.2')
    assert Ref('Gen.1.31').next() == Ref('Gen.2.1')
    assert Ref('Gen.50.25').next() == Ref('Gen.50.26')
    assert Ref('Gen.50.26').next() == Ref('Exod.1.1')
    assert list(xrefrange(Ref('Gen.1.1'), 'Gen.1.4')) == [Ref("Gen.1.1"), Ref("Gen.1.2"), Ref("Gen.1.3"), Ref("Gen.1.4")]

def test_find_subranges():
    orig_range = refrange('Gen.1.1', 'Gen.1.8')
    act_range = refrange('Gen.1.1', 'Gen.1.3') + refrange('Gen.1.6', 'Gen.1.8')
    subranges = find_subranges(orig_range, act_range)
    assert subranges == [refrange('Gen.1.1', 'Gen.1.3'),  refrange('Gen.1.6', 'Gen.1.8')]

    orig_range = refrange('Gen.1.1', 'Gen.1.8')
    act_range = refrange('Gen.1.1', 'Gen.1.8')
    subranges = find_subranges(orig_range, act_range)
    assert subranges == [act_range]

    orig_range = refrange('Gen.1.1', 'Gen.1.8')
    act_range = refrange('Gen.1.1', 'Gen.1.4') + refrange('Gen.1.6', 'Gen.1.8')
    subranges = find_subranges(orig_range, act_range)
    assert subranges == [refrange('Gen.1.1', 'Gen.1.4'),  refrange('Gen.1.6', 'Gen.1.8')]

