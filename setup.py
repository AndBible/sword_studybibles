#!/usr/bin/env python

import setuptools

setuptools.setup(name='study2osis', version='0.0.5',
                 package_dir={"": "src"},
                 packages=setuptools.find_packages('src'),
                 include_package_data=True,
                 zip_safe=False)
