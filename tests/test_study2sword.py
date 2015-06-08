"""
    Copyright (C) 2014 Tuomas Airaksinen.
    See LICENCE.txt
"""

from study2sword.study2sword import *
from bs4 import BeautifulSoup

def test_overlapping_1():
    class options:
        title = 'ESVN'
        work_id = 'ESVN'

    osistext = BeautifulSoup("""
        <osisText>
        <div annotateRef="Gen.1.1-Gen.1.4" annotateType="commentary"><reference>blah1</reference></div>
        <div annotateRef="Gen.1.2-Gen.1.4" annotateType="commentary"><reference>blah2</reference></div>
        <div annotateRef="Gen.1.3" annotateType="commentary"><reference>blah3</reference></div>
        </osisText>
    """, 'xml')

    s = Stydy2Osis(options)
    s.root_soup = osistext
    s.fix_overlapping_ranges(osistext)
    result = osistext.prettify()
    print result
    com1, com2, com3 = osistext.find_all('div', annotateType='commentary')
    assert com1['annotateRef'] == "Gen.1.1"
    assert com2['annotateRef'] == "Gen.1.2 Gen.1.4"
    assert com3['annotateRef'] == "Gen.1.3"

    link1, link2, link3 = [i.find('list', cls='reference_links') for i in [com1,com2,com3]]
    assert not link1
    assert 'blah1' in link2.text
    assert 'blah3' not in link2.text
    assert 'blah1' in link3.text
    assert 'blah2' in link3.text

def test_merge_comments():
    class options:
        title = 'ESVN'
        work_id = 'ESVN'

    osistext = BeautifulSoup("""
        <osisText>
        <div annotateRef="Gen.1.1-Gen.1.4" annotateType="commentary"><reference>blah1</reference></div>
        <div annotateRef="Gen.1.2-Gen.1.4" annotateType="commentary"><reference>blah2</reference></div>
        <div annotateRef="Gen.1.2" annotateType="commentary"><reference>blah3</reference></div>
        <div annotateRef="Gen.1.3" annotateType="commentary"><reference>blah4</reference></div>
        </osisText>
    """, 'xml')

    s = Stydy2Osis(options)
    s.root_soup = osistext
    s.fix_overlapping_ranges(osistext)
    result = osistext.prettify()
    print result
    com1, com2, com3 = osistext.find_all('div', annotateType='commentary')
    assert com1['annotateRef'] == "Gen.1.1"
    assert com2['annotateRef'] == "Gen.1.2 Gen.1.4" #merged comments 2 % 3
    assert com3['annotateRef'] == "Gen.1.3"

    link1, link2, link3 = [i.find('list', cls='reference_links') for i in [com1,com2,com3]]
    assert not link1
    assert 'blah1' in link2.text
    assert 'blah3' not in link2.text
    assert 'blah1' in link3.text
    assert 'blah2' in link3.text

    #print result
