"""
    Copyright (C) 2015 Tuomas Airaksinen.
    See LICENCE.txt
"""
import os

from bs4 import BeautifulSoup
import jinja2
import logging
from .html2osis import HTML2OsisMixin

logger = logging.getLogger('study2osis')

from .overlapping import FixOverlappingVersesMixin
from .bible_data import BOOKREFS, TAGS_BOOK
from .io import IOMixin


COMMENTARY_TEMPLATE_XML = os.path.join(__file__.rsplit(os.path.sep,1)[0], 'template.xml')
GENBOOK_TEMPLATE_XML = os.path.join(__file__.rsplit(os.path.sep,1)[0], 'genbook_template.xml')

def dict_to_options(opts):
    class Options:
        @classmethod
        def setdefault(self, k, v):
            self.__dict__.setdefault(k, v)

    default_options = dict(
        debug=False,
        sword=True,
        tag_level=0,
        title='',
        work_id='',
        bible_work_id='ESVS',
        no_nonadj=False,
    )
    for key, value in default_options.iteritems():
        opts.setdefault(key, value)

    Options.__dict__ = opts

    return Options


class Study2Osis(FixOverlappingVersesMixin, IOMixin, HTML2OsisMixin):
    """
    Study bible commentary text to SWORD module conversion class

    """
    def __init__(self, options):
        if isinstance(options, dict):
            options = dict_to_options(options)
        self.options = options

        self.verse_comment_dict = {}
        self.verse_comments_all_dict = {} #list of comments that appear on verses
        self.images = []

        template = jinja2.Template(open(COMMENTARY_TEMPLATE_XML).read())
        output_xml = BeautifulSoup(template.render(title=options.title, work_id=options.work_id), 'xml')
        self.root_soup = output_xml

        self.osistext = osistext = output_xml.find('osisText')
        if self.options.tag_level >= TAGS_BOOK:
            ot = output_xml.new_tag('div', type='x-testament')
            matt_ref = BOOKREFS.index('Matt')
            for i in BOOKREFS[:matt_ref]:
                book = output_xml.new_tag('div', type='book', osisID=i)
                ot.append(book)
            nt = output_xml.new_tag('div', type='x-testament')
            for i in BOOKREFS[matt_ref:]:
                book = output_xml.new_tag('div', type='book', osisID=i)
                nt.append(book)
            osistext.append(ot)
            osistext.append(nt)

class Articles2Osis(HTML2OsisMixin):
    """
        Nothing really functional here.

        Started to get articles into SWORD genbook, but postponing this project for a while now.
    """
    def __init__(self, options):
        if isinstance(options, dict):
            options = dict_to_options(options)
        self.options = options

        self.images = []

        template = jinja2.Template(open(GENBOOK_TEMPLATE_XML).read())
        output_xml = BeautifulSoup(template.render(title=options.title, author='-', work_id=options.work_id), 'xml')
        self.root_soup = output_xml

        self.osistext = output_xml.find('osisText')

    def process_article(self, soup):
        pass

    def process_toc(self, toc_soup):
        for itm in toc_soup.find_all('p', class_='toc'):
            fname = itm.find('a')['href']
            soup = self.give_soup(fname).find('body')
            title = soup.find('div', class_='passagetitle').text
            article = self.process_article(soup)

    def start(self):
        self.path = 'orig/OEBPS/Text/'
        soup = self.give_soup('a00.resources.xhtml')
        self.process_toc(soup)

    def give_soup(self, fname):
        input_data = open(os.path.join(self.path,fname)).read()
        return BeautifulSoup(input_data, 'xml')



