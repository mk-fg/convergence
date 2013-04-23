#!/usr/bin/env python

# Copyright (c) 2011 Moxie Marlinspike <moxie@thoughtcrime.org>
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA


from setuptools import setup, find_packages
import os, glob

pkg_root = os.path.dirname(__file__)

# Error-handling here is to allow package to be built w/o README included
try: readme = open(os.path.join(pkg_root, 'README.md')).read()
except IOError: readme = ''

setup(

    name = 'convergence-notary',
    version = '0.5',
    author = 'Moxie Marlinspike',
    author_email = 'moxie@thoughtcrime.org',
    license = 'GPL',
    url = 'http://convergence.io/',

    description = 'An agile, distributed, and'
        ' secure alternative to the Certificate Authority system',
    long_description = readme,

    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Framework :: Twisted',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Telecommunications Industry',
        'License :: OSI Approved',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2 :: Only',
        'Topic :: Internet',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Security',
        'Topic :: System :: Networking :: Monitoring' ],

    install_requires = ['Twisted', 'pyOpenSSL', 'M2Crypto'],

    packages = find_packages(),
    include_package_data = True,
    zip_safe = False,

    entry_points = dict(console_scripts=sorted(
        '{} = {}:main'.format(link, target[:-3].replace(os.sep, '.'))
        for link, target in
            ((link, os.readlink(link)) for link in glob.glob('convergence-*'))
        if target.endswith('.py') )) )
