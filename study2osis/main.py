# encoding: utf-8
"""
    Copyright (C) 2015 Tuomas Airaksinen.
    See LICENCE.txt
"""
import os, zipfile, tempfile, codecs, shutil, subprocess, logging, itertools, time

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
        self.link_map = {}

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

    def _collect_linkmap(self):
        """
            Collect mapping from HTML ids to osisRefs
        """
        logger.info('Collecting linkmap from studynotes')
        for t in self.osistext.find_all(id=True):
            id = t['id']
            if 'origFile' in t.attrs:
                origfile = t['origFile']
            else:
                p = t.find_parent(origFile=True)
                origfile = p['origFile']

            origfile = origfile.split(os.path.sep)[-1]
            origref = '%s#%s' % (origfile, id)
            target = t.find_parent('div', annotateType='commentary')['annotateRef'].split(' ')[0]
            self.link_map[origref] = '%s:%s' % (self.options.work_id, target)

    def _fix_postponed_references(self):
        """ Fix postponed reference links from the mapping collected in self.link_map"""
        logger.info('Fixing postponed references')
        for r in itertools.chain(*[i.find_all('reference', postpone='1') for i in (self.osistext, self.articles.osistext)]):
            if r['origRef'] in self.link_map:
                r['osisRef'] = self.link_map[r['origRef']]
                del r['postpone']
            else:
                r.replace_with('[%s]' % r.text)
                logger.error('link not found %s', r['origRef'])

    def process_epub(self, epub_filename, output_filename=None, assume_zip=False):
        time_start = time.time()
        if not zipfile.is_zipfile(epub_filename):
            raise Exception('Zip file assumed!')

        epub_zip = zipfile.ZipFile(epub_filename)
        studynote_files = [i for i in epub_zip.namelist() if i.endswith('studynotes.xhtml')]
        if not studynote_files:
            raise Exception('No studynotes in zip file')

        if self.options.debug:
            studynote_files = studynote_files[:2]

        logger.info('Reading studynotes')
        for fn in studynote_files:
            logger.debug('Reading studynotes %s %s', studynote_files.index(fn), fn)
            data_in = epub_zip.read(fn)
            self.current_filename = fn
            self._read_studynotes_file(data_in)

        self.fix_overlapping_ranges()
        self._collect_linkmap()
        for i in self.osistext.find_all(unwrap=True):
            i.unwrap()
        self.articles = Articles2Osis(self.options)
        self.articles.read_intros_and_articles(epub_zip)
        self.articles.collect_linkmap(self.link_map)
        self.articles.post_process()
        self._fix_postponed_references()

        if self.options.sword:
            self.make_sword_module(epub_zip, output_filename, epub_filename)

        else:
            output_filename = output_filename or '%s.xml' % epub_filename.rsplit('.')[0]
            self.write_osis_file(output_filename)
            self.articles.write('articles_'+output_filename)
        if epub_zip:
            epub_zip.close()
        logger.info('Processing took %.2f minutes', (time.time()-time_start)/60.)

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
        self.current_filename = ''
        self.images = []
        self.used_resources = []

        template = jinja2.Template(open(GENBOOK_TEMPLATE_XML).read())
        output_xml = BeautifulSoup(template.render(title=options.title, author='-', work_id=options.work_id), 'xml')
        self.root_soup = output_xml
        self.osistext = output_xml.find('osisText')
        self.articles = output_xml.new_tag('div', type='book', osisID='Articles')
        self.intros = output_xml.new_tag('div', type='book', osisID='Book_introductions')
        self.other = output_xml.new_tag('div', type='book', osisID='Other_resources')

        self.osistext.append(self.intros)
        self.osistext.append(self.articles)
        self.osistext.append(self.other)
        self.path = HTML_DIRECTORY[0]

    def fix_osis_id(self, osisid):
        """Remove illegal characters from osisIDs"""
        for i in u':();—/.,[]{} ':
            osisid = osisid.replace(i, '_').strip()
        return osisid

    def collect_linkmap(self, link_map):
        """
            Collect mapping from HTML ids to osisRefs
        """
        logger.info('Collecting linkmap from resources')
        for t in self.osistext.find_all(id=True):
            id = t['id']
            if 'origFile' in t.attrs:
                origfile = t['origFile']
            else:
                p = t.find_parent(origFile=True)
                if not p:
                    logger.error('origFile could not be found for %s', t)
                    continue
                origfile = p['origFile']

            origfile = origfile.split(os.path.sep)[-1]
            origref = '%s#%s' % (origfile, id)

            link_map[origref] = self.get_full_ref(t)

    def get_full_ref(self, t):
        target_tag = None
        if 'osisID' in t.attrs:
            target_tag = t
        if not target_tag:
            target_tag = t.find_parent('div', type='section')
        if not target_tag:
            target_tag = t.find_parent('div', type='chapter')

        target = target_tag['osisID']
        for t in target_tag.parents:
            if 'osisID' in t.attrs:
                target = '%s/%s' % (t['osisID'], target)

        return '%s:%s' % (self.options.work_id + '_articles', target)

    def _fix_section_one_level(self, soup, tag, type):
        h_tags = soup.find_all(tag, recursive=False)
        for i in xrange(len(h_tags)):
            start = h_tags[i]
            next_siblings = list(start.next_siblings)
            start['old_name'] = start.name
            start.name = 'title'
            start['origFile'] = self.current_filename

            if tag == 'h3':
                start['h3'] = 1

            section = self.root_soup.new_tag('div', type=type, origFile=self.current_filename)

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
            return False

        title = titletag.text.strip(' \n')

        # Manually one inconsistency in ESV Study Bible (should does not affect other works)
        if title in [u'Ezra—History of Salvation in the Old Testament', u'Song of Solomon—History of Salvation in the Old Testament']:
            target = self.articles.find(osisID=self.fix_osis_id('History of Salvation in the Old Testament  Preparing the Way for Christ'))
            self._fix_sections(soup)
            self._all_fixes(soup)
            for i in soup.children:
                target.append(i)
            return False

        titletag.name = 'title'
        titletag['origFile'] = self.current_filename
        titletag.string = title #'* %s *' % title
        self._fix_sections(soup)
        self._all_fixes(soup)
        soup.name = 'div'
        soup['type'] = 'chapter'
        soup['osisID'] = self.fix_osis_id(title)
        soup['origFile'] = fname
        #self.articles.append(soup)
        return True


    def _process_toc(self, toc_soup):
        for itm in toc_soup.find_all('li'):
            fname = itm.find('a')['href'].split('#')[0]
            if fname.endswith('resources.xhtml'):
                self.used_resources.append(fname.split(os.path.sep)[-1])
                self.current_filename = fname
                soup = self._give_soup(os.path.join(self.path, fname)).find('body')
                self._process_html_body(soup, fname)
                self.articles.append(soup)

    def read_intros_and_articles(self, epub_zip):
        self.zip = epub_zip

        logger.info('Reading articles')
        soup = self._give_soup(os.path.join(self.path, 'toc.xhtml'))
        self._process_toc(soup)

        bookintro_files = [i for i in epub_zip.namelist() if i.endswith('intros.xhtml')]
        if self.options.debug:
            bookintro_files = bookintro_files[:2]

        logger.info('Reading intros')
        for f in bookintro_files:
            logger.debug('Reading intros %s', f)
            self.current_filename = f
            bs = self._give_soup(f).find('body')
            if not self._process_html_body(bs, f):
                continue
            for h1 in bs.find_all('h1'):
                h1.extract()
            self.intros.append(bs)

        logger.info('Reading other resources')
        resource_files = [i for i in epub_zip.namelist() if i.endswith('resources.xhtml') and i.split(os.path.sep)[-1] not in self.used_resources]
        if self.options.debug:
            resource_files = resource_files[:2]
        for f in resource_files:
            self.current_filename = f
            bs = self._give_soup(f).find('body')
            if not self._process_html_body(bs, f):
                continue
            for h1 in bs.find_all('h1'):
                h1.extract()
            self.other.append(bs)

        # do not split sections in short articles
        for c in self.root_soup.find_all('div', type='chapter'):
            if len(c.text) < 20000:
                for pt in c.find_all('div', type='section'):
                    pt.unwrap()

        for pt in self.root_soup.find_all('div', type='section'):
            pt['osisID'] = self.fix_osis_id(pt.title.text)
            #pt['osisID'] = '- ' + self.fix_osis_id(pt.title.text)

    def generate_toc(self, node):
        root_list = self.root_soup.new_tag('list')
        for n in node.find_all('div', osisID=True, recursive=False):
            item = self.root_soup.new_tag('item')
            ref = self.get_full_ref(n)
            item.append(self.root_soup.new_tag('reference', osisRef=ref))
            title_tag = n.find('title', recursive=False)
            item.reference.string = title_tag.text if title_tag else n['osisID']
            root_list.append(item)
            l = self.generate_toc(n)
            if l:
                root_list.append(l)
        if root_list.contents:
            return root_list

    def post_process(self):
        logger.info('Postprosessing resources')
        for t in self.root_soup.find_all('title', h3=1):
                t.name = 'p'
                hi = self.root_soup.new_tag('hi', type='bold')
                for c in t.children:
                    hi.append(c.extract())
                t.append(hi)

        for p in self.root_soup.find_all('div', type='paragraph'):
            p.name = 'p'
        for pt in self.root_soup.find_all('div', class_='passagetitle'):
            pt.unwrap()
        for pt in self.root_soup.find_all('div'):
            if 'epub:type' in pt.attrs:
                del pt['epub:type']

        for pt in self.root_soup.find_all('div', type='subSection'):
            pt.unwrap()

        for pt in self.root_soup.find_all('div'):
            if 'type' not in pt.attrs:
                pt.unwrap()

        self.other.contents.sort(key=lambda x: x.attrs.get('osisID', ''))

        for d in self.osistext.find_all('div', osisID=True):
            children = d.find_all('div', osisID=True, recursive=False)
            if children:
                root_list = self.generate_toc(d)
                if root_list:
                    p = self.root_soup.new_tag('p')
                    p.append(self.root_soup.new_tag('title'))
                    p.title.string = 'Table of contents'
                    p.append(root_list)
                    d.find('div', osisID=True).insert_before(p)


    def write(self, output_filename):
        logger.info('Writing articles into OSIS file %s', output_filename)
        output = codecs.open(output_filename, 'w', encoding='utf-8')
        if self.options.debug:
            output.write(self.root_soup.prettify())
        else:
            output.write(unicode(self.root_soup))
        output.close()

    def _give_soup(self, fname):
        input_data = self.zip.read(fname)
        return BeautifulSoup(input_data, 'xml')



