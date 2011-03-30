#!/usr/bin/env python

from distutils.core import setup

name = 'openerp_libclient'
version = '0.0.1'

setup(
    name=name,
    version=version,
    description='Client Library for the OpenERP protocol',
    long_description="This library allows client applications connect and work "
                    "against an OpenERP server.",
    license='LGPLv3',
    platforms='Platform Independent',
    author="Panos Christeas",
    author_email='xrg@openerp.com',
    url='http://git.hellug.gr/?p=xrg/openerp-libcli',
    download_url="http://git.hellug.gr/?p=xrg/openerp-libcli",
    packages=['openerp_libclient'],
    keywords=['xml-rpc', 'openerp', 'client', 'python',],
    classifiers=[
          'Development Status :: 1 - Experimental',
          'Environment :: Libraries',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: LGPL v3',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System :: Filesystems',
          ],
    )
