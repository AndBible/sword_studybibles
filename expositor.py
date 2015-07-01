"""
    Copyright (C) 2015 Tuomas Airaksinen.
    See LICENCE.txt
"""

import logging
from bs4 import NavigableString

logging.basicConfig(level=logging.INFO)

import ipdb

from study2osis.main import *

osistext = BeautifulSoup(open('emet/make.xml').read(), 'xml')
print 'read done'

class options:
    title = 'EXP'
    commentary_work_id = 'EXP'
    commentary_images_path = ''
    articles_images_path = ''
    no_nonadj = False
    tag_level = 0
    metadata = {}
    debug = False

with ipdb.launch_ipdb_on_exception():
    s = Commentary(options)
    s.root_soup = osistext
    s.osistext = osistext.find('osisText')
    for c in s.osistext.find_all('div', type='x-testament'):
        c.unwrap()
    for c in s.osistext.find_all('div', type='book'):
        c.unwrap()
    for c in s.osistext.find_all('chapter'):
        c.unwrap()
    print 'unwraps done'
    # move strings and other content that remain outside comment div tags into preceding comment
    for i in s.osistext.find_all('div', recursive=False):
        while i.next_sibling and (isinstance(i.next_sibling, NavigableString) or i.next_sibling.name != 'div'):
            i.append(i.next_sibling.extract())

    print 'string fix done'
    s.expand_all_ranges()
    print 'expands done'
    sort_tag_content(s.osistext, lambda x: (x.expanded_verses[0], -len(x.expanded_verses)), 'div')
    print 'sorting done'
    s.fix_overlapping_ranges()
    print 'fixing overlapping done'
    s.clean_tags()
    print 'clean tags done'

    ## add all content of comments into a paragraph
    for c in s.osistext.find_all('div', annotateType='commentary'):
        c['type'] = 'section'
        par = s.root_soup.new_tag('div', type='paragraph')
        for i in list(c.children):
            par.append(i.extract())
        c.append(par)

    s.write_osis_file('expositor_osis.xml')
    print 'osis file ready'
    import codecs
    with codecs.open('expositor_pretty.xml', 'w', encoding="utf-8") as f:
        f.write(osistext.prettify())
    print 'prettified osis file ready'