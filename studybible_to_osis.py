#!/usr/bin/env python

# encoding: utf-8
"""
    Copyright (C) 2015 Tuomas Airaksinen.
    See LICENCE.txt
"""

import optparse
from study2osis import Commentary
from ipdb import launch_ipdb_on_exception
import logging
logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    parser = optparse.OptionParser(usage='Usage. %prog [options] directory_or_epub_file')
    parser.add_option('--debug', action='store_true', dest='debug', default=False,
                      help='Debug mode')
    parser.add_option('--sword', action='store_true', dest='sword', default=False,
                      help='Generate sword module (zip file). osis2mod is needed.')
    parser.add_option('--no_nonadj', action='store_true', dest='no_nonadj', default=False,
                      help='Do not create empty comments (with only links) for non-adjacent verse ranges')
    parser.add_option('--tag_level', dest='tag_level', default=0, type=int,
                      help='Tag level: 0: none, 1: book divs, 2: chapter divs, 3: verse divs')
    parser.add_option('--title', dest='title', default='ESV Study Bible Notes',
                      help='OSIS title')
    parser.add_option('--work_id', dest='work_id', default='ESVN',
                      help='OSIS work_id')
    parser.add_option('--bible_work_id', dest='bible_work_id', default='ESVS',
                      help='Bible work_id (verses are linked there). "None" -> no work_id specification')

    options, args = parser.parse_args()
    if len(args) == 1:
        input_dir = args[0]
        with launch_ipdb_on_exception():
            o = Commentary(options)
            o.process_epub(input_dir)
    else:
        parser.print_help()
