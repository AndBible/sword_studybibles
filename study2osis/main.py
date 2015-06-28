# encoding: utf-8
"""
    Copyright (C) 2015 Tuomas Airaksinen.
    See LICENCE.txt
"""
import os
import zipfile
import tempfile
import codecs
import shutil
import subprocess
import logging
import time
import re
import optparse

from bs4 import BeautifulSoup
import jinja2

from .html2osis import HTML2OsisMixin, parse_studybible_reference
from .overlapping import FixOverlappingVersesMixin, sort_tag_content
from study2osis.bibleref import Ref

HTML_DIRECTORY = ['OEBPS', 'Text']
IMAGE_DIRECTORY = ['OEBPS', 'Images']
BIBLE_CONF_TEMPLATE = os.path.join(__file__.rsplit(os.path.sep, 1)[0], 'commentary_template.conf')
GENBOOK_CONF_TEMPLATE = os.path.join(__file__.rsplit(os.path.sep, 1)[0], 'genbook_template.conf')

COMMENTARY_TEMPLATE_XML = os.path.join(__file__.rsplit(os.path.sep, 1)[0], 'commentary_template.xml')
GENBOOK_TEMPLATE_XML = os.path.join(__file__.rsplit(os.path.sep, 1)[0], 'genbook_template.xml')
GENBOOK_BRANCH_SEPARATION_LETTER = '/'

logger = logging.getLogger('study2osis')


class Options(object):
    def __init__(self, d=None):
        if d:
            self.update(d)

    def setdefault(self, k, v):
        self.__dict__.setdefault(k, v)

    def update(self, d):
        self.__dict__.update(d)


def dict_to_options(opts):
    if not isinstance(opts, dict):
        opts = opts.__dict__

    options = Options(opts)

    default_options = dict(
        debug=False,
        sword=True,
        osis=False,
        no_nonadj=False,
    )
    for key, value in default_options.iteritems():
        options.setdefault(key, value)

    return options


def fix_osis_id(osisid):
    """Remove illegal characters from osisIDs"""
    osisid = re.sub(r'[^\w]', ' ', osisid)
    osisid = re.sub(r'  +', ' ', osisid)
    return osisid.strip()


class AbstractStudybible(object):
    """
        Some common methods for Commentary and Articles
    """

    def clean_tags(self):
        """
            Finally remove all temporary/illegal attributes
        """

        for i in self.osistext.find_all(unwrap=True):
            i.unwrap()

        attrs = set()
        for t in self.osistext.find_all():
            for a in t.attrs.keys():
                if a not in ['osisID', 'type', 'src', 'role', 'osisRef', 'osisWork', 'href', 'annotateRef',
                             'annotateType']:
                    attrs.add(a)
                    del t[a]
        logger.info('Removed attributes: %s', ', '.join(attrs))

    def fix_postponed_references(self, link_map):
        """ Fix postponed reference links from the mapping collected in self.link_map"""
        logger.info('Fixing postponed references')
        for r in self.osistext.find_all('reference', postpone='1'):
            if r['origRef'] in link_map:
                r['osisRef'] = link_map[r['origRef']]
                del r['postpone']
            else:
                r.replace_with('[%s]' % r.text)
                logger.error('link not found %s', r['origRef'])

    def collect_linkmap(self, linkmap):
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

            linkmap[origref] = self._get_full_ref(t)


class Commentary(AbstractStudybible, HTML2OsisMixin, FixOverlappingVersesMixin):
    """
        Write commentary studynotes as OSIS xml that can be converted
        to SWORD commentary with osis2mod
    """

    def __init__(self, options):
        if isinstance(options, dict):
            options = dict_to_options(options)
        self.options = options
        self.images_path = options.commentary_images_path
        self.work_id = options.commentary_work_id
        self.verse_comment_dict = {}
        self.verse_comments_all_dict = {}  # list of comments that appear on verses
        self.verse_comments_firstref_dict = {}
        self.images = []
        self.link_map = {}
        self.current_filename = ''

        template = jinja2.Template(open(COMMENTARY_TEMPLATE_XML).read())
        output_xml = BeautifulSoup(template.render(commentary_work_id=self.work_id, metadata=options.metadata), 'xml')
        self.root_soup = output_xml
        self.osistext = output_xml.find('osisText')

    def _get_full_ref(self, t):
        target = t.find_parent('div', annotateType='commentary')['annotateRef'].split(' ')[0]
        return '%s:%s' % (self.work_id, target)

    def write_osis_file(self, output_filename):
        logger.info('Writing OSIS file %s', output_filename)

        out = codecs.open(output_filename, 'w', encoding='utf-8')
        if self.options.debug:
            out.write(self.root_soup.prettify())
        else:
            out.write(unicode(self.root_soup))
        out.close()

    def read_studynotes(self, epub_zip):
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

            body = BeautifulSoup(data_in, 'xml').find('body')
            for i in body.find_all(recursive=False):
                i['origFile'] = fn
                self.osistext.append(i.extract())

        self._adjust_studynotes()
        #     self._write_studynotes_into_osis(body)

    def read_crossreferences(self, epub_zip):
        crossref_files = [p for p in epub_zip.namelist() if p.endswith('crossrefs.xhtml')]
        if not crossref_files:
            raise Exception('No crossreference in zip file')

        if self.options.debug:
            crossref_files = crossref_files[:2]

        logger.info('Reading crossreferences')
        for fn in crossref_files:
            logger.debug('Reading studynotes %s %s', crossref_files.index(fn), fn)
            data_in = epub_zip.read(fn)
            self.current_filename = fn

            body = BeautifulSoup(data_in, 'xml').find('body')
            for p in body.find_all('p', class_='crossref', recursive=False):
                p.extract()
                verse = Ref(parse_studybible_reference(p.a.extract()['href'].split('#')[1]))
                target_comment = self.verse_comments_firstref_dict.get(verse)
                p.name = 'item'
                p.insert(0, self.root_soup.new_string('ESV: '))
                self._all_fixes(p)

                if target_comment:
                    links = target_comment.find('list', cls='reference_links')
                    if not links:
                        links = self.create_new_reference_links_list()
                        target_comment.append(links)
                    links.append(p)
                else:
                    new_div = self._create_empty_comment(verse)
                    links = self.create_new_reference_links_list()
                    new_div.append(links)
                    links.append(p)
                    assert verse not in self.verse_comment_dict

                    # find next verse that can be found
                    n = verse
                    try:
                        while n not in self.verse_comments_firstref_dict:
                            n = n.next()
                        position = self.verse_comments_firstref_dict[n]
                        position.insert_before(new_div)
                    except n.LastVerse:
                        self.osistext.append(new_div)

                    self.verse_comment_dict[verse] = new_div
                    self.verse_comments_firstref_dict[verse] = new_div
                    vl = self.verse_comments_all_dict.get(verse)
                    if not vl:
                        vl = self.verse_comments_all_dict[verse] = set()
                    vl.add(new_div)

class Articles(AbstractStudybible, HTML2OsisMixin):
    """
        Write articles & book introdcutions as OSIS xml that can be converted
        to SWORD genbook with xml2gbs
    """

    class TitleNotFound(Exception):
        pass

    class ExceptionalProcessing(Exception):
        pass

    def __init__(self, options, commentary_xml):
        if isinstance(options, dict):
            options = dict_to_options(options)
        self.options = options
        self.images_path = options.articles_images_path
        self.work_id = options.articles_work_id
        self.commentary_xml = commentary_xml
        self.current_filename = ''
        self.images = []
        self.used_resources = []

        template = jinja2.Template(open(GENBOOK_TEMPLATE_XML).read())
        output_xml = BeautifulSoup(template.render(articles_work_id=self.work_id, metadata=options.metadata), 'xml')
        self.root_soup = output_xml
        self.osistext = output_xml.find('osisText')
        self.articles = output_xml.new_tag('div', type='book', osisID=fix_osis_id('Articles'))
        self.intros = output_xml.new_tag('div', type='book', osisID=fix_osis_id('Book introductions'))
        self.other = output_xml.new_tag('div', type='book', osisID=fix_osis_id('Uncategorized resources'))
        self.osistext.append(self.intros)
        self.osistext.append(self.articles)
        self.osistext.append(self.other)
        self.path = HTML_DIRECTORY[0]

    def _read_resources(self, files, target):
        if self.options.debug:
            files = files[:2]
        for f in files:
            logger.debug('Reading %s', f)
            self.current_filename = f
            bs = self._give_soup(f).find('body')
            try:
                self._process_html_body(bs)
            except (self.TitleNotFound, self.ExceptionalProcessing):
                logger.info('Processed via exception (OK): %s', f)
                continue
            for h1 in bs.find_all('h1'):
                h1.extract()
            target.append(bs)

    def read_resources_from_epub(self, epub_zip):
        self.zip = epub_zip

        logger.info('Reading articles')
        soup = self._give_soup(os.path.join(self.path, 'toc.xhtml'))
        self._process_toc(soup)

        bookintro_files = [i for i in epub_zip.namelist() if i.endswith('intros.xhtml')]

        logger.info('Reading intros')
        self._read_resources(bookintro_files, self.intros)

        logger.info('Reading other resources')
        resource_files = [i for i in epub_zip.namelist() if i.endswith('resources.xhtml')
                          and i.split(os.path.sep)[-1] not in self.used_resources]

        self._read_resources(resource_files, self.other)

        # do not split sections in short articles
        # TODO: make optional
        for c in self.root_soup.find_all('div', type='chapter'):
            if len(c.text) < 20000:
                for pt in c.find_all('div', type='section'):
                    pt.unwrap()

        for pt in self.root_soup.find_all('div', type='section'):
            pt['osisID'] = fix_osis_id(pt.title.text)
            # pt['osisID'] = '- ' + self.fix_osis_id(pt.title.text)

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
            del p.attrs['type']

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

        sort_tag_content(self.other, key=lambda x: x.attrs.get('osisID', ''))

        full_toc = self.root_soup.new_tag('div', type='book', osisID=fix_osis_id('Full Table of Contents'))
        full_toc.append(self.root_soup.new_tag('title'))
        full_toc.title.string = 'Full table of contents'
        full_toc.append(self._generate_toc(self.osistext, 2))
        self.osistext.insert(0, full_toc)

        for d in self.osistext.find_all('div', osisID=True):
            children = d.find_all('div', osisID=True, recursive=False)
            if children:
                root_list = self._generate_toc(d, 2)
                if root_list:
                    p = self.root_soup.new_tag('p')
                    p.append(self.root_soup.new_tag('title'))
                    p.title.string = 'Table of Contents'
                    p.append(root_list)
                    d.find('div', osisID=True).insert_before(p)

    def write_osis_file(self, output_filename):
        logger.info('Writing articles into OSIS file %s', output_filename)
        output = codecs.open(output_filename, 'w', encoding='utf-8')
        if self.options.debug:
            output.write(self.root_soup.prettify())
        else:
            output.write(unicode(self.root_soup))
        output.close()

    def _get_full_ref(self, t):
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
                target = '%s%s%s' % (t['osisID'], GENBOOK_BRANCH_SEPARATION_LETTER, target)

        return '%s:%s' % (self.work_id, target)

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
            if i < len(h_tags) - 1:
                end = h_tags[i + 1]

            for t in next_siblings:
                if t == end:
                    break
                section.append(t.extract())

    def _fix_sections(self, soup):
        self._fix_section_one_level(soup, 'h2', 'section')
        for i in soup.find_all('div', type='section'):
            self._fix_section_one_level(i, 'h3', 'subSection')

    def _find_title(self, soup):
        titletag = soup.find(re.compile('^(h1|h2|h3|title)$'))
        if not titletag:
            titletag = soup.find('p', class_='concordance-section')
        if not titletag:
            logger.error('No title in %s, skipping.', self.current_filename)
            raise self.TitleNotFound
        title = titletag.text.strip(' \n')
        return titletag, title

    def _move_to_studynote(self, tag, target_ref):
        """
            To fix properly also links, this should be run actually *before* doing final fixes to studynotes
        """
        tag = tag.extract()
        self._all_fixes(tag)
        studynote = self.commentary_xml.find('div', annotateRef=re.compile('^%s' % target_ref))
        tag['type'] = 'paragraph'
        studynote.append(tag)
        logger.info('Moved %s to %s', tag.title.text, target_ref)

    def _manual_fixes(self, soup):
        """
            Manually fix some inconsistencies in ESV Study Bible (should does not affect other works)
        """

        titletag, title = self._find_title(soup)

        if titletag.attrs.get('class', '') == 'concordance-section':
            target = self.articles.find(osisID=fix_osis_id('Concordance'))
            target.append(soup.extract())
            titletag.name = 'title'
            titletag['origFile'] = self.current_filename
            soup['type'] = 'section'
            self._fix_sections(soup)
            self._all_fixes(soup)
            soup.name = 'div'
            soup['osisID'] = fix_osis_id(title)
            soup['origFile'] = self.current_filename
            raise self.ExceptionalProcessing

        # TODO: first check if this is really ESV Study Bible!
        if self.current_filename.endswith('intros.xhtml'):
            if title == 'The Battle at Mount Gilboa':
                self._move_to_studynote(titletag.parent, '1Sam.31.1')
            elif title == 'The Deity of Jesus Christ in 2 Peter':
                self._move_to_studynote(titletag.parent, '2Pet.3.1')

        if title in [u'Ezra—History of Salvation in the Old Testament',
                     u'Song of Solomon—History of Salvation in the Old Testament']:
            target = self.articles.find(osisID=fix_osis_id('History of Salvation in the Old Testament'
                                                           '  Preparing the Way for Christ'))
            self._fix_sections(soup)
            self._all_fixes(soup)
            for i in soup.children:
                target.append(i)
            raise self.ExceptionalProcessing
        return True

    def _process_html_body(self, soup):
        if self.current_filename.endswith('resources.xhtml') and len(soup.find_all('h1')) > 1:
            logger.error('More than 1 h1 header in a file %s!', self.current_filename)

        self._manual_fixes(soup)

        titletag, title = self._find_title(soup)

        soup.name = 'div'
        soup['type'] = 'chapter'
        soup['origFile'] = self.current_filename
        titletag.name = 'title'
        titletag['origFile'] = self.current_filename
        # titletag.string = title
        soup['osisID'] = fix_osis_id(title)
        self._fix_sections(soup)
        self._all_fixes(soup)

    def _process_toc(self, toc_soup):
        for itm in toc_soup.find_all('li'):
            fname = itm.find('a')['href'].split('#')[0]
            if fname.endswith('resources.xhtml'):
                self.used_resources.append(fname.split(os.path.sep)[-1])
                self.current_filename = fname
                soup = self._give_soup(os.path.join(self.path, fname)).find('body')
                try:
                    self._process_html_body(soup)
                except self.TitleNotFound:
                    logger.error('No title in %s, skipping.', self.current_filename)
                    continue
                self.articles.append(soup)

    def _generate_toc(self, node, depth):
        if not depth:
            return
        root_list = self.root_soup.new_tag('list')
        for n in node.find_all('div', osisID=True, recursive=False):
            item = self.root_soup.new_tag('item')
            ref = self._get_full_ref(n)
            item.append(self.root_soup.new_tag('reference', osisRef=ref))
            title_tag = n.find('title', recursive=False)
            item.reference.string = title_tag.text if title_tag else n['osisID']
            root_list.append(item)
            l = self._generate_toc(n, depth - 1)
            if l:
                item.append(l)
        if root_list.contents:
            return root_list

    def _give_soup(self, fname):
        input_data = self.zip.read(fname)
        return BeautifulSoup(input_data, 'xml')


class Convert(object):
    """
        Main class for study bible to SWORD module conversion
    """

    def __init__(self, options):
        options = dict_to_options(options)
        self.options = options
        self.linkmap = {}

    def set_options(self):
        self.options.setdefault('bible_work_id', 'None')
        work_id_base = fix_osis_id(self.options.metadata.title)
        commentary_work_id = work_id_base + ' Commentary'
        articles_work_id = work_id_base + ' Articles'
        commentary_data_path = 'modules/comments/zcom/{wid}'.format(wid=commentary_work_id.replace(' ', '_'))
        articles_data_path = 'modules/genbook/rawgenbook/{wid}/{wid}'.format(wid=articles_work_id.replace(' ', '_'))

        self.options.setdefault('commentary_work_id', commentary_work_id)
        self.options.setdefault('commentary_data_path', commentary_data_path)
        self.options.setdefault('articles_work_id', articles_work_id)
        self.options.setdefault('articles_data_path', articles_data_path)
        self.options.setdefault('commentary_images_path', 'images/')
        self.options.setdefault('articles_images_path', '../../../../%s/images/' % commentary_data_path)

    def process_epub(self, epub_filename, output_filename=None):
        time_start = time.time()
        if not zipfile.is_zipfile(epub_filename):
            raise Exception('Zip file assumed!')

        epub_zip = zipfile.ZipFile(epub_filename)
        self.options.metadata = self.read_metadata(epub_zip)
        self.set_options()

        self.commentary = Commentary(self.options)
        self.articles = Articles(self.options, self.commentary.osistext)

        self.commentary.read_studynotes(epub_zip)

        self.articles.read_resources_from_epub(epub_zip)

        logger.info('Expand all ranges in commentaries')
        self.commentary.expand_all_ranges()

        self.commentary.read_crossreferences(epub_zip)



        self.commentary.fix_overlapping_ranges()
        self.commentary.collect_linkmap(self.linkmap)

        self.articles.collect_linkmap(self.linkmap)
        self.articles.post_process()

        self.commentary.fix_postponed_references(self.linkmap)
        self.articles.fix_postponed_references(self.linkmap)

        logger.info('Cleaning up illegal/temporary attributes')
        self.commentary.clean_tags()
        self.articles.clean_tags()

        if self.options.sword:
            self.make_sword_module(epub_zip, output_filename, epub_filename)

        if self.options.osis:
            output_filename = output_filename or '%s.xml' % epub_filename.rsplit('.')[0]
            self.commentary.write_osis_file(output_filename)
            self.articles.write_osis_file('articles_' + output_filename)

        epub_zip.close()
        logger.info('Processing took %.2f minutes', (time.time() - time_start) / 60.)

    def read_metadata(self, epub_zip):
        data = BeautifulSoup(epub_zip.read('OEBPS/content.opf'), 'xml').find('metadata')
        metadata = {}
        for d in data.find_all(recursive=False):
            txt = BeautifulSoup(d.text).text
            if txt:
                metadata[d.name] = txt
        return Options(metadata)

    def make_sword_module(self, epub_zip, output_filename, input_dir):
        from study2osis import __version__

        logger.info('Making sword module')

        fd, bible_osis_filename = tempfile.mkstemp()
        temp = codecs.open(bible_osis_filename, 'w', 'utf-8')
        temp.write(unicode(self.commentary.root_soup))
        temp.close()
        os.close(fd)
        fd, articles_osis_filename = tempfile.mkstemp()
        temp = codecs.open(articles_osis_filename, 'w', 'utf-8')
        temp.write(unicode(self.articles.root_soup))
        temp.close()
        os.close(fd)

        module_dir = tempfile.mkdtemp()

        os.mkdir(os.path.join(module_dir, 'mods.d'))
        commentary_save_path = os.path.join(module_dir, *self.options.commentary_data_path.split('/'))
        os.makedirs(commentary_save_path)
        articles_save_path = os.path.join(module_dir, *self.options.articles_data_path.split('/'))
        os.makedirs(articles_save_path)
        image_path = os.path.join(commentary_save_path, self.options.commentary_images_path)
        os.makedirs(image_path)
        for i in set(self.commentary.images + self.articles.images):
            if epub_zip:
                image_fname_in_zip = '/'.join(IMAGE_DIRECTORY + [i])
                image_fname_in_fs = os.path.join(image_path, i)
                with open(image_fname_in_fs, 'w') as f:
                    f.write(epub_zip.open(image_fname_in_zip).read())
            else:
                shutil.copyfile(os.path.join(*([input_dir] + IMAGE_DIRECTORY + [i])), os.path.join(image_path, i))
        # bible conf
        conf_filename = os.path.join('mods.d', self.options.commentary_work_id.replace(' ', '_').lower() + '.conf')
        conf_str = jinja2.Template(codecs.open(BIBLE_CONF_TEMPLATE, 'r', 'utf-8').read()).render(
            commentary_work_id=self.options.commentary_work_id,
            commentary_data_path=self.options.commentary_data_path,
            filename=input_dir,
            revision=__version__,
            metadata=self.options.metadata,
        )

        with codecs.open(os.path.join(module_dir, conf_filename), 'w', 'utf-8') as f:
            f.write(conf_str)

        # articles conf
        conf_filename = os.path.join('mods.d', self.options.articles_work_id.replace(' ', '_').lower() + '.conf')
        conf_str = jinja2.Template(codecs.open(GENBOOK_CONF_TEMPLATE, 'r', 'utf-8').read()).render(
            articles_work_id=self.options.articles_work_id,
            articles_data_path=self.options.articles_data_path,
            filename=input_dir,
            revision=__version__,
            metadata=self.options.metadata,
        )
        with codecs.open(os.path.join(module_dir, conf_filename), 'w', 'utf-8') as f:
            f.write(conf_str)

        process = subprocess.Popen(
            ['osis2mod', commentary_save_path, bible_osis_filename, '-v', 'NRSV', '-z', '-b', '3'],
            stdout=subprocess.PIPE)
        process.communicate()
        process.wait()
        os.unlink(bible_osis_filename)

        process = subprocess.Popen(['xml2gbs', articles_osis_filename, articles_save_path], stdout=subprocess.PIPE)
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


def main():
    parser = optparse.OptionParser(usage='Usage. %prog [options] directory_or_epub_file')
    parser.add_option('--debug', action='store_true', dest='debug', default=False,
                      help='Debug mode')
    parser.add_option('--sword', action='store_true', dest='sword', default=False,
                      help='Generate sword module. osis2mod anx xml2gbs from libsword-tools are needed.')
    parser.add_option('--osis', action='store_true', dest='osis', default=False,
                      help='Write OSIS files.')
    parser.add_option('--no_nonadj', action='store_true', dest='no_nonadj', default=False,
                      help='Do not create empty comments (with only links) for non-adjacent verse ranges')
    parser.add_option('--bible_work_id', dest='bible_work_id', default='None',
                      help='Bible work_id (verses are linked there). "None" -> no work_id specification')

    options, args = parser.parse_args()
    if len(args) == 1:
        input_file = args[0]
        if options.debug or True:
            from ipdb import launch_ipdb_on_exception

            with launch_ipdb_on_exception():
                Convert(options).process_epub(input_file)
        else:
            Convert(options).process_epub(input_file)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
