#-*- coding: utf-8 -*-
from __future__ import print_function


__author__ = 'Moxie Marlinspike'
__email__ = 'moxie@thoughtcrime.org'

__license__= '''
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


from convergence.TargetPage import TargetPage
from convergence.ConnectChannel import ConnectChannel

from convergence.verifier.NetworkPerspectiveVerifier import NetworkPerspectiveVerifier
from convergence.verifier.DNSVerifier import DNSVerifier

from twisted.enterprise import adbapi
from twisted.web import http
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor, endpoints
from twisted.application import strports

import logging


def get_backend(name):
    if name == 'perspective': return NetworkPerspectiveVerifier()
    elif name.startswith('dns:'): return DNSVerifier(opts.backend.split(':')[1])


def run_notary(opts, backend, log=None):
    if log is None: log = logging.getLogger(__name__)

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
    # from OpenSSL import SSL
    # ctx = SSL.Context(SSL.SSLv23_METHOD)
    # ctx.set_options(SSL.OP_NO_SSLv2)

    svc_http.startService()
    svc_tls.startService()

    log.debug('Convergence Notary started...')
    reactor.run()
    log.debug('Convergence Notary stopped')
