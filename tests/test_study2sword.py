# encoding:utf-8
"""
    Copyright (C) 2015 Tuomas Airaksinen.
    See LICENCE.txt
"""
from study2osis.html2osis import parse_studybible_reference, HTML2OsisMixin
from study2osis.overlapping import find_subranges

from study2osis.main import Commentary, Articles
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
    commentary_work_id = 'ESVN'
    articles_work_id = 'ESVN'
    commentary_images_path = ''
    articles_images_path = ''
    no_nonadj = False
    tag_level = 0
    metadata = {}

def test_overlapping_1():
    osistext = BeautifulSoup("""
        <osisText>
        <div annotateRef="Gen.1.1-Gen.1.4" annotateType="commentary"><reference>blah1</reference></div>
        <div annotateRef="Gen.1.2-Gen.1.4" annotateType="commentary"><reference>blah2</reference></div>
        <div annotateRef="Gen.1.3" annotateType="commentary"><reference>blah3</reference></div>
        </osisText>
    """, 'xml')

    s = Commentary(options)
    s.root_soup = osistext
    s.osistext = osistext.find('osisText')
    s.expand_all_ranges()
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

    s = Commentary(options)
    s.root_soup = osistext
    s.osistext = osistext.find('osisText')
    s.expand_all_ranges()
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

    s = Commentary(options)
    s.root_soup = osistext
    s.osistext = osistext.find('osisText')
    s.expand_all_ranges()
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

    s = Commentary(options)
    s.root_soup = osistext
    s.osistext = osistext.find('osisText')
    s.expand_all_ranges()
    s.fix_overlapping_ranges()
    result = osistext.prettify()
    print result
    assert link_refs(osistext, 'Gen.1.1') == set()
    assert link_refs(osistext, 'Gen.1.2') == {Ref('Gen.1.1')}
    assert link_refs(osistext, 'Gen.1.3') == {Ref('Gen.1.1')}
    assert link_refs(osistext, 'Gen.1.4 Gen.1.5 Gen.1.6') == {Ref('Gen.1.1')}
    #assert link_refs(osistext, 'Gen.1.5') == set()
    #assert link_refs(osistext, 'Gen.1.6') == set()


def test_genbook():
    osistext = BeautifulSoup("""
        <body>
        <h1>h1 title</h1>
        <h2>h2 section</h2>
        <h3>h3 subsection</h3>
        <p>paragraph</p>

        </body>
    """, 'xml')

    s = Articles(options, None)
    #s.root_soup = s.osistext = osistext
    s._process_html_body(osistext.find('body'))
    result = unicode(s.root_soup) #.prettify()
    print repr(result)
    assert result == u'<?xml version="1.0" encoding="utf-8"?>\n<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.bibletechnologies.net/2003/OSIS/namespace http://www.bibletechnologies.net/osisCore.2.1.1.xsd">\n<osisText osisIDWork="ESVN" osisRefWork="book" xml:lang="en">\n<header>\n<work osisWork="ESVN">\n<title/>\n<creator role="aut"/>\n<identifier type="OSIS">ESVN</identifier>\n<refSystem>Bible.NRSV</refSystem>\n</work>\n</header>\n<div osisID="Book introductions" type="book"/><div osisID="Articles" type="book"/><div osisID="Uncategorized resources" type="book"/></osisText>\n</osis>'

def test_genbook2():
    osistext = BeautifulSoup("""
        <body>
        <h1>h1 title</h1>
            <h2>h2 section</h2>
                <h3>h3 subsection</h3>
                    <p>paragraph</p>
                <h3>h3 another</h3>
                    <p>another para</p>
            <h2>h2 another</h2>
                <p>under h2 another</p>
        </body>
    """, 'xml')

    s = Articles(options, None)
    #s.root_soup = s.osistext = osistext
    s._process_html_body(osistext.find('body'))
    result = unicode(s.root_soup) #.prettify()
    print repr(result)
    assert result == u'<?xml version="1.0" encoding="utf-8"?>\n<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.bibletechnologies.net/2003/OSIS/namespace http://www.bibletechnologies.net/osisCore.2.1.1.xsd">\n<osisText osisIDWork="ESVN" osisRefWork="book" xml:lang="en">\n<header>\n<work osisWork="ESVN">\n<title/>\n<creator role="aut"/>\n<identifier type="OSIS">ESVN</identifier>\n<refSystem>Bible.NRSV</refSystem>\n</work>\n</header>\n<div osisID="Book introductions" type="book"/><div osisID="Articles" type="book"/><div osisID="Uncategorized resources" type="book"/></osisText>\n</osis>'

def test_colspan():
    osistext = BeautifulSoup("""<body><table><tr><td colspan="3">test</td></tr></table></body>""", 'xml')
    result = BeautifulSoup("""<body><table><tr><td>test</td><td add="1"/><td add="1"/></table></body>""", 'xml')

    s = Articles(options, None)
    s.fix_table_colspan(osistext.find('body'))
    assert unicode(osistext) == unicode(result)

import pytest
@pytest.mark.parametrize('osistext,result',[
                    (
                    """<body><table><tr><td rowspan="2">test</td><td/></tr><tr><td/></tr><tr><td/></tr></table></body>""",
                    """<body><table><tr><td>test</td><td/></tr><tr><td add="1"/><td/></tr><tr><td/></tr></table></body>"""
                     ),
                    (
                    """<body><table><tr><td/><td rowspan="2">test</td><td/></tr><tr><td/><td/></tr><tr><td/><td/></tr></table></body>""",
                    """<body><table><tr><td/><td>test</td><td/></tr><tr><td/><td add="1"/><td/></tr><tr><td/><td/></tr></table></body>"""
                     ),
                    (
                    """<body><table><tr><td/><td rowspan="3">test</td><td/></tr><tr><td/><td/></tr><tr><td/><td/></tr></table></body>""",
                    """<body><table><tr><td/><td>test</td><td/></tr><tr><td/><td add="1"/><td/></tr><tr><td/><td add="1"/><td/></tr></table></body>"""
                     ),
                    (
                    """<body><table><tr><td/> <td rowspan="3">test</td><td/>asdf</tr><tr><td/><td/></tr><tr><td/><td/></tr></table></body>""",
                    """<body><table><tr><td/> <td>test</td><td/>asdf</tr><tr><td/><td add="1"/><td/></tr><tr><td/><td add="1"/><td/></tr></table></body>"""
                     ),

                    ])
def test_rowspan(osistext, result):
    osistext_ = BeautifulSoup(osistext, 'xml')
    result__ = BeautifulSoup(result, 'xml')

    s = Articles(options, None)
    s.fix_table_rowspan(osistext_.find('body'))
    assert unicode(osistext_) == unicode(result__)

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
    assert Ref('SOMEBOOK:Gen.1.1') == Ref('Gen.1.1')
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
    assert Ref('Rev', 1, 1) == Ref('Rev.1.1')

def test_guess_range_end():
    h = HTML2OsisMixin()
    g = h._guess_range_end
    c = lambda x: BeautifulSoup('<a>%s</a>'%x, 'xml').a
    assert g(Ref('Gen.1.1'), c('1:1-3')) == Ref('Gen', 1, 3)
    assert g(Ref('Isa.11.1'), c('Isa. 11:1-10')) == Ref('Isa.11.10')
    assert g(Ref('Isa.11.1'), c('Isa. 11:1-12:10')) == Ref('Isa.12.10')
    assert g(Ref('Isa.11.1'), c('11:1-12:10')) == Ref('Isa.12.10')
    assert g(Ref('Isa.11.1'), c('Isa 11:1-10')) == Ref('Isa.11.10')
    assert g(Ref('Isa.11.1'), c('Isa 11:1-12:10')) == Ref('Isa.12.10')
    assert g(Ref('1Cor.3.16'), c('1 Cor. 3:16–17')) == Ref('1Cor.3.17')
    assert g(Ref('1Cor.3.16'), c('vv. 16-17')) == Ref('1Cor.3.17')

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

