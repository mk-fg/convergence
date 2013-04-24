#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function


__author__ = 'Moxie Marlinspike'
__email__ = 'moxie@thoughtcrime.org'

__license__ = '''
Copyright (c) 2010 Moxie Marlinspike <moxie@thoughtcrime.org>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA
'''


import os, sys

# Check python version
if sys.version_info < (2, 7):
    print('Sorry, convergence requires at least Python 2.7', file=sys.stderr)
    sys.exit(3)

# Extend sys.path, if run from the checkout tree
try: import convergence
except ImportError:
    from os.path import dirname, realpath
    sys.path.insert(0, dirname(dirname(realpath(__file__))))
    import convergence


# BSD and Mac OS X, kqueue
try:
    from twisted.internet import kqreactor as event_reactor
except:
    # Linux 2.6 and newer, epoll
    try:
        from twisted.internet import epollreactor as event_reactor
    except:
        # Linux pre-2.6, poll
        from twisted.internet import pollreactor as event_reactor

event_reactor.install()


from convergence.TargetPage import TargetPage
from convergence.ConnectChannel import ConnectChannel
from convergence.ConnectRequest import ConnectRequest

from convergence.verifier.NetworkPerspectiveVerifier import NetworkPerspectiveVerifier
from convergence.verifier.DNSVerifier import DNSVerifier
from convergence import __version__

from twisted.enterprise import adbapi
from twisted.web import http
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor, endpoints
from twisted.application import strports

from OpenSSL import SSL

from contextlib import contextmanager
import logging


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        description='Convergence {} by Moxie Marlinspike.'.format(__version__))
    parser.add_argument('--debug',
        action='store_true', help='Verbose operation mode.')
    cmds = parser.add_subparsers(
        title='Supported operations (have their own suboptions as well)')

    @contextmanager
    def subcommand(name, **kwz):
        cmd = cmds.add_parser(name, **kwz)
        cmd.set_defaults(call=name)
        yield cmd

    with subcommand('notary', help='Start notary daemon.') as cmd:
        cmd.add_argument('-p', '--http-port', type=int, metavar='port', default=80,
            help='HTTP port to listen on (default %(default)s).')
        cmd.add_argument('-s', '--tls-port', type=int, metavar='port', default=443,
            help='TLS port to listen on (default %(default)s).')
        cmd.add_argument('--no-https', action='store_true',
            help='Turn off TLS wrapping for --tls-port, e.g. to put Twisted behind Nginx.')
        cmd.add_argument('-i', '--interface', metavar='ip_or_hostname',
            help='Interface (IP address or hostname) to listen on for incoming connections (optional).')
        cmd.add_argument('-c', '--cert', metavar='path', required=True, help='TLS certificate path.')
        cmd.add_argument('-k', '--cert-key', metavar='path',
            help='TLS private key path. Not necessary if also contained in the --cert file.')
        cmd.add_argument('-d', '--db',
            metavar='path', default='/var/lib/convergence/convergence.db',
            help='SQLite database path (default: %(default)s).')
        cmd.add_argument('-b', '--backend',
            metavar='perspective|dns:<host>', default='perspective',
            help='Verifier backend (default: %(default)s). Available backends: perspective, dns.')

    # TODO: all the other convergence-* commands here

    opts = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if opts.backend == 'perspective': backend = NetworkPerspectiveVerifier()
    elif opts.backend.startswith('dns:'): backend = DNSVerifier(opts.backend.split(':')[1])
    else: raise parser.error('Invalid backend: {}'.format(opts.backend))

    cert_key_path = opts.cert_key or opts.cert
    cert_key = open(opts.cert_key or opts.cert).read() # TODO: is it really used?
    database = adbapi.ConnectionPool('sqlite3', opts.db, cp_max=1, cp_min=1)

    connectFactory = http.HTTPFactory(timeout=10)
    connectFactory.protocol = ConnectChannel

    notary = Resource()
    notary.putChild('target', TargetPage(database, cert_key, backend))
    notaryFactory = Site(notary)

    # It'd be easier and more flexible to specify endpoints in config, but we don't have one yet
    ep_interface = '' if not opts.interface else ':interface={}'.format(opts.interface)
    svc_http = strports.service('tcp:{}{}'.format(opts.http_port, ep_interface), connectFactory)
    tls_endpoint = ( 'tcp:{{}}{}'.format(ep_interface) if opts.no_https else
            'ssl:{{}}{}:certKey={}:privateKey={}'.format(ep_interface, opts.cert, cert_key_path) )\
        .format(opts.tls_port)
    svc_tls = strports.service(tls_endpoint, notaryFactory)

    # TODO: make sure these are used in endpoints' tls setup
    # ctx = SSL.Context(SSL.SSLv23_METHOD)
    # ctx.set_options(SSL.OP_NO_SSLv2)

    svc_http.startService()
    svc_tls.startService()

    # TODO: proper logging configuration or at least twisted-logging observer
    logging.basicConfig(
        logging.INFO if not opts.debug else logging.DEBUG,
        format='%(asctime)s :: %(name)s :: %(levelname)s: %(message)s' )
    logging.info('Convergence Notary started...')

    reactor.run()


if __name__ == '__main__': main()
