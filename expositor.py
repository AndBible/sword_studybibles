"""
    Copyright (C) 2014 Tuomas Airaksinen.
    See LICENCE.txt
"""

import logging
logging.basicConfig(level=logging.INFO)

from study2osis.main import *

from bs4 import BeautifulSoup
osistext = BeautifulSoup(open('expositor2.xml').read(), 'xml')

class options:
    title = 'ESVN'
    commentary_work_id = 'ESVN'
    articles_work_id = 'ESVN'
    commentary_images_path = ''
    articles_images_path = ''
    no_nonadj = False
    tag_level = 0
    metadata = {}
    debug = False


import ipdb

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
    s.expand_all_ranges()
    s.fix_overlapping_ranges()
    s.clean_tags()
    for c in s.osistext.find_all('div', annotateType='commentary'):
        c['type'] = 'section'
        par = s.root_soup.new_tag('div', type='paragraph')
        for i in list(c.children):
            par.append(i.extract())
        c.append(par)
        #c.unwrap()
    s.write_osis_file('expositor_osis.xml')
#result = osistext.prettify()



#import codecs
#with codecs.open('expositor_pretty.xml', 'w', encoding="utf-8") as f:
#    f.write(osistext.prettify())