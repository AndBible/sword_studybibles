"""
    Copyright (C) 2015 Tuomas Airaksinen.
    See LICENCE.txt
"""
import os, zipfile, tempfile, codecs, shutil, subprocess, logging

from bs4 import BeautifulSoup
import jinja2

from .html2osis import HTML2OsisMixin
from .overlapping import FixOverlappingVersesMixin
from .bible_data import BOOKREFS, TAGS_BOOK

HTML_DIRECTORY = ['OEBPS', 'Text']
IMAGE_DIRECTORY = ['OEBPS', 'Images']
BIBLE_CONF_TEMPLATE = os.path.join(__file__.rsplit(os.path.sep,1)[0], 'template.conf')
GENBOOK_CONF_TEMPLATE = os.path.join(__file__.rsplit(os.path.sep,1)[0], 'genbook_template.conf')

COMMENTARY_TEMPLATE_XML = os.path.join(__file__.rsplit(os.path.sep,1)[0], 'template.xml')
GENBOOK_TEMPLATE_XML = os.path.join(__file__.rsplit(os.path.sep,1)[0], 'genbook_template.xml')

logger = logging.getLogger('study2osis')

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

class Study2Osis(FixOverlappingVersesMixin, HTML2OsisMixin):
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

    def _read_studynotes_file(self, data_in):
        input_html = BeautifulSoup(data_in, 'xml')

        body = input_html.find('body')
        self._adjust_studynotes(body)
        self._write_studynotes_into_osis(body)

    def process_epub(self, epub_filename, output_filename=None, assume_zip=False):
        if not zipfile.is_zipfile(epub_filename):
            raise Exception('Zip file assumed!')

        epub_zip = zipfile.ZipFile(epub_filename)
        studynote_files = [i for i in epub_zip.namelist() if i.endswith('studynotes.xhtml')]
        if not studynote_files:
            raise Exception('No studynotes in zip file')

        if self.options.debug:
            studynote_files = studynote_files[:1]

        logger.info('Reading studynotes')
        for fn in studynote_files:
            logger.debug('Reading studynotes %s %s', studynote_files.index(fn), fn)
            data_in = epub_zip.read(fn)
            self._read_studynotes_file(data_in)

        self.fix_overlapping_ranges()

        self.articles = Articles2Osis(self.options)
        self.articles.read_intros_and_articles(epub_zip)

        if self.options.sword:
            self.make_sword_module(epub_zip, output_filename, epub_filename)

        else:
            output_filename = output_filename or '%s.xml' % epub_filename.rsplit('.')[0]
            self.write_osis_file(output_filename)
        if epub_zip:
            epub_zip.close()

    def write_osis_file(self, output_filename):
        logger.info('Writing OSIS file %s', output_filename)

        out = codecs.open(output_filename, 'w', encoding='utf-8')
        if self.options.debug:
            out.write(self.root_soup.prettify())
        else:
            out.write(unicode(self.root_soup))
        out.close()

    def make_sword_module(self, epub_zip, output_filename, input_dir):
        from study2osis import __version__
        logger.info('Making sword module')
        fd, bible_osis_filename = tempfile.mkstemp()
        temp = codecs.open(bible_osis_filename, 'w', 'utf-8')
        temp.write(unicode(self.root_soup))
        temp.close()
        os.close(fd)
        fd, articles_osis_filename = tempfile.mkstemp()
        temp = codecs.open(articles_osis_filename, 'w', 'utf-8')
        temp.write(unicode(self.articles.root_soup))
        temp.close()
        os.close(fd)

        module_dir = tempfile.mkdtemp()
        os.mkdir(os.path.join(module_dir, 'mods.d'))
        os.mkdir(os.path.join(module_dir, 'modules'))
        os.mkdir(os.path.join(module_dir, 'modules', 'comments'))
        os.mkdir(os.path.join(module_dir, 'modules', 'comments', 'zcom'))
        module_final = os.path.join(module_dir, 'modules', 'comments', 'zcom', self.options.work_id.lower())
        os.mkdir(module_final)
        articles_final = os.path.join(module_final, 'articles')
        os.mkdir(articles_final)
        image_path = os.path.join(module_final, 'images')
        os.mkdir(image_path)
        for i in self.images + self.articles.images:
            if epub_zip:
                image_fname_in_zip = '/'.join(IMAGE_DIRECTORY + [i])
                image_fname_in_fs = os.path.join(image_path, i)
                with open(image_fname_in_fs, 'w') as f:
                    f.write(epub_zip.open(image_fname_in_zip).read())
            else:
                shutil.copyfile(os.path.join(*([input_dir]+IMAGE_DIRECTORY+[i])), os.path.join(image_path, i))
        # bible conf
        conf_filename = os.path.join('mods.d', self.options.work_id.lower()+'.conf')
        if os.path.exists(os.path.join('module_dir', conf_filename)):
            shutil.copy(os.path.join('module_dir', conf_filename), os.path.join(module_dir, conf_filename))
        else:
            f = codecs.open(os.path.join(module_dir, conf_filename), 'w', 'utf-8')
            conf_str = jinja2.Template(codecs.open(BIBLE_CONF_TEMPLATE, 'r', 'utf-8').read()).render(
                                                                    work_id=self.options.work_id,
                                                                    filename=input_dir,
                                                                    title=self.options.title,
                                                                    revision=__version__,
                                                                    )
            f.write(conf_str)
            f.close()

        # articles conf
        conf_filename = os.path.join('mods.d', self.options.work_id.lower()+'_articles.conf')
        if os.path.exists(os.path.join('module_dir', conf_filename)):
            shutil.copy(os.path.join('module_dir', conf_filename), os.path.join(module_dir, conf_filename))
        else:
            f = codecs.open(os.path.join(module_dir, conf_filename), 'w', 'utf-8')
            conf_str = jinja2.Template(codecs.open(GENBOOK_CONF_TEMPLATE, 'r', 'utf-8').read()).render(
                                                                    work_id=self.options.work_id,
                                                                    filename=input_dir,
                                                                    title=self.options.title,
                                                                    revision=__version__,
                                                                    )
            f.write(conf_str)
            f.close()

        process = subprocess.Popen(['osis2mod', module_final, bible_osis_filename, '-v', 'NRSV', '-z', '-b', '3'], stdout=subprocess.PIPE)
        process.communicate()
        process.wait()
        os.unlink(bible_osis_filename)

        process = subprocess.Popen(['xml2gbs', articles_osis_filename, articles_final], stdout=subprocess.PIPE)
        process.communicate()
        process.wait()
        os.unlink(articles_osis_filename)

        zip_filename = output_filename or '%s_module.zip' % input_dir.rsplit('.')[0]
        sword_zip = zipfile.ZipFile(zip_filename, 'w')
        for root, dirs, files in os.walk(module_dir):
            for file in files:
                root_in_zip = root[len(module_dir):]
                sword_zip.write(os.path.join(root, file), os.path.join(root_in_zip, file))
        sword_zip.close()
        shutil.rmtree(module_dir)
        logger.info('Sword module written in %s', zip_filename)

class Articles2Osis(HTML2OsisMixin):
    """
        Write articles & book introdcutions as a SWORD genbook
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
        self.articles = output_xml.new_tag('div', type='book', osisID='Articles')
        self.intros = output_xml.new_tag('div', type='book', osisID='Book introductions')

        self.osistext.append(self.intros)
        self.osistext.append(self.articles)
        self.path = HTML_DIRECTORY[0]

    def _fix_section_one_level(self, soup, tag, type):
        h_tags = soup.find_all(tag, recursive=False)
        for i in xrange(len(h_tags)):
            start = h_tags[i]
            next_siblings = list(start.next_siblings)
            start['old_name'] = start.name
            start.name = 'title'
            if tag =='h3':
                start.name = 'p'
                hi = self.root_soup.new_tag('hi', type='bold')
                for c in start.children:
                    hi.append(c.extract())
                start.append(hi)

            section = self.root_soup.new_tag('div', type=type)

            start.wrap(section)

            end = None
            if i < len(h_tags)-1:
                end = h_tags[i+1]

            for t in next_siblings:
                if t == end:
                    break
                section.append(t.extract())

    def _fix_sections(self, soup):
        self._fix_section_one_level(soup, 'h2', 'section')
        for i in soup.find_all('div', type='section'):
            self._fix_section_one_level(i, 'h3', 'subSection')

    def _process_html_body(self, soup, fname):
        if fname.endswith('resources.xhtml') and len(soup.find_all('h1')) > 1:
            logger.error('More than 1 h1 header in a file %s!', fname)
        titletag = soup.find('h1')
        if not titletag:
            titletag = soup.find('h2')
        if not titletag:
            titletag = soup.find('h3')
        if not titletag:
            logger.error('No title in %s, skipping.', fname)
            return
        title = titletag.text.strip(' \n')
        titletag.name = 'title'
        titletag.string = '* %s *' % title
        self._fix_sections(soup)
        self._all_fixes(soup)
        soup.name = 'div'
        soup['type'] = 'chapter'
        soup['osisID'] = title
        soup['origfile'] = fname
        self.articles.append(soup)


    def _process_toc(self, toc_soup):
        for itm in toc_soup.find_all('li'):
            fname = itm.find('a')['href'].split('#')[0]
            if fname.endswith('resources.xhtml'):
                soup = self._give_soup(os.path.join(self.path, fname)).find('body')
                self._process_html_body(soup, fname)

    def read_intros_and_articles(self, epub_zip):
        self.zip = epub_zip

        logger.info('Reading articles')
        soup = self._give_soup(os.path.join(self.path, 'toc.xhtml'))
        self._process_toc(soup)

        bookintro_files = [i for i in epub_zip.namelist() if i.endswith('intros.xhtml')]

        logger.info('Reading intros')
        for f in bookintro_files:
            logger.debug('Reading intros %s', f)
            bs = self._give_soup(f).find('body')
            self._process_html_body(bs, f)
            for h1 in bs.find_all('h1'):
                h1.extract()
            self.intros.append(bs)

        for p in self.root_soup.find_all('div', type='paragraph'):
            p.name = 'p'
        for pt in self.root_soup.find_all('div', class_='passagetitle'):
            pt.unwrap()
        for pt in self.root_soup.find_all('div'):
            if 'epub:type' in pt.attrs:
                del pt['epub:type']

        for pt in self.root_soup.find_all('div', type='subSection'):
            pt.unwrap()

        # do not split sections in short articles
        for c in self.root_soup.find_all('div', type='chapter'):
            if len(c.text) < 20000:
                for pt in c.find_all('div', type='section'):
                    pt.unwrap()

        for pt in self.root_soup.find_all('div', type='section'):
            pt['osisID'] = '- ' + pt.title.text

        for pt in self.root_soup.find_all('div'):
            if 'type' not in pt.attrs:
                pt.unwrap()

    def write(self, output_filename):
        output = codecs.open(output_filename, 'w', encoding='utf-8')
        output.write(unicode(self.root_soup))
        output.close()

    def _give_soup(self, fname):
        input_data = self.zip.read(fname)
        return BeautifulSoup(input_data, 'xml')



