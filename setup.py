#/usr/bin/env python
import codecs
import os

from setuptools import setup, find_packages

read = lambda filepath: codecs.open(filepath, 'r', 'utf-8').read()

# Load package meta from the pkgmeta module without loading cacheablefiles.
pkgmeta = {}
execfile(os.path.join(os.path.dirname(__file__),
         'cacheablefiles', 'pkgmeta.py'), pkgmeta)

setup(
    name='django-cacheablefiles',
    version=pkgmeta['__version__'],
    description='A collection of utilities to ease the caching of files by the server.',
    long_description=read(os.path.join(os.path.dirname(__file__), 'README.rst')),
    author='Matthew Tretter',
    author_email='m@tthewwithanm.com',
    url='http://github.com/hzdg/django-cacheablefiles/',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    tests_require=[
    ],
    install_requires=[
        'Django>=1.4',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Utilities'
    ],
)
