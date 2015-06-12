"""
    Copyright (C) 2014 Tuomas Airaksinen.
    See LICENCE.txt
"""

import logging

logger = logging.getLogger('study2osis')
import os, zipfile, tempfile, codecs, subprocess, shutil
import jinja2
from bs4 import BeautifulSoup

HTML_DIRECTORY = ['OEBPS', 'Text']
IMAGE_DIRECTORY = ['OEBPS', 'Images']
TEMPLATE_CONF = os.path.join(__file__.rsplit(os.path.sep,1)[0], 'template.conf')

class IOMixin(object):
    """
        File reading / writing functions are organized here
    """
    def read_file(self, data_in):
        input_html = BeautifulSoup(data_in, 'xml')

        body = input_html.find('body')
        self._adjust_studynotes(body)
        self._write_studynotes_into_osis(body)

    def process_files(self, input_dir, output_filename=None):
        epub_zip = None
        if zipfile.is_zipfile(input_dir):
            epub_zip = zipfile.ZipFile(input_dir)
            files = [i for i in epub_zip.namelist() if i.endswith('studynotes.xhtml')]
        else:
            files = sorted(
                [os.path.join(*([input_dir] + HTML_DIRECTORY + [f])) for f in os.listdir(os.path.join(*([input_dir] + HTML_DIRECTORY))) if
                 f.endswith('studynotes.xhtml')])

        if self.options.debug:
            files = files[:6]
        for fn in files:
            logger.info('processing %s %s', files.index(fn), fn)
            if epub_zip:
                data_in = epub_zip.read(fn)
            else:
                data_in = codecs.open(fn, 'r', encoding='utf-8').read()
            self.read_file(data_in)
        self.fix_overlapping_ranges()
        if self.options.sword:
            self.make_sword_module(epub_zip, output_filename, input_dir)

        else:
            output_filename = output_filename or '%s.xml' % input_dir.rsplit('.')[0]
            self.write_osis_file(output_filename)
        if epub_zip:
            epub_zip.close()

    def make_sword_module(self, epub_zip, output_filename, input_dir):
        logger.info('Making sword module')
        fd, filename = tempfile.mkstemp()
        temp = open(filename, 'w')
        temp.write(unicode(self.root_soup).encode('utf-8'))
        temp.close()
        os.close(fd)
        module_dir = tempfile.mkdtemp()
        os.mkdir(os.path.join(module_dir, 'mods.d'))
        os.mkdir(os.path.join(module_dir, 'modules'))
        os.mkdir(os.path.join(module_dir, 'modules', 'comments'))
        os.mkdir(os.path.join(module_dir, 'modules', 'comments', 'zcom'))
        module_final = os.path.join(module_dir, 'modules', 'comments', 'zcom', self.options.work_id.lower())
        os.mkdir(module_final)
        image_path = os.path.join(module_dir, 'modules', 'comments', 'zcom', self.options.work_id.lower(), 'images')
        os.mkdir(image_path)
        for i in self.images:
            if epub_zip:
                image_fname_in_zip = '/'.join(IMAGE_DIRECTORY + [i])
                image_fname_in_fs = os.path.join(image_path, i)
                with open(image_fname_in_fs, 'w') as f:
                    f.write(epub_zip.open(image_fname_in_zip).read())
            else:
                shutil.copyfile(os.path.join(*([input_dir]+IMAGE_DIRECTORY+[i])), os.path.join(image_path, i))
        conf_filename = os.path.join('mods.d', self.options.work_id.lower()+'.conf')
        if os.path.exists(os.path.join('module_dir', conf_filename)):
            shutil.copy(os.path.join('module_dir', conf_filename), os.path.join(module_dir, conf_filename))
        else:
            f = open(os.path.join(module_dir, conf_filename), 'w')
            conf_str = jinja2.Template(open(TEMPLATE_CONF).read()).render(work_id=self.options.work_id, filename=input_dir)
            f.write(conf_str)
            f.close()

        process = subprocess.Popen(['osis2mod', module_final, filename, '-v', 'NRSV', '-z', '-b', '3'], stdout=subprocess.PIPE)
        process.communicate()
        process.wait()
        os.unlink(filename)
        zip_filename = output_filename or '%s_module.zip' % input_dir.rsplit('.')[0]
        sword_zip = zipfile.ZipFile(zip_filename, 'w')
        for root, dirs, files in os.walk(module_dir):
            for file in files:
                root_in_zip = root[len(module_dir):]
                sword_zip.write(os.path.join(root, file), os.path.join(root_in_zip, file))
        sword_zip.close()
        shutil.rmtree(module_dir)
        logger.info('Sword module written in %s', zip_filename)

    def write_osis_file(self, output_filename):
        logger.info('Writing OSIS file %s', output_filename)

        if self.options.debug:
            out2 = codecs.open('pretty_%s' % output_filename, 'w', encoding='utf-8')
            out2.write(self.root_soup.prettify())
            out2.close()
        else:
            out = codecs.open(output_filename, 'w', encoding='utf-8')
            out.write(unicode(self.root_soup))
            out.close()
