#-*- coding: utf-8 -*-

# Copyright (c) 2011 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

from convergence.verifier import Verifier, OptionsError

from twisted.internet import reactor, defer, ssl
from twisted.internet.protocol import ClientFactory, Protocol

from OpenSSL.SSL import (
    Context, SSLv23_METHOD, TLSv1_METHOD,
    VERIFY_PEER, VERIFY_FAIL_IF_NO_PEER_CERT, OP_NO_SSLv2 )

import os, re, logging

log = logging.getLogger(__name__)


# It's not critical, but includes mozilla certs for major legit hosts like akamai
ca_certs_pem = '/etc/ssl/certs/ca-certificates.crt'
if not os.path.exists(ca_certs_pem): ca_certs_pem = None


class NetworkPerspectiveVerifier(Verifier):
    '''
    This class is responsible for verifying a target fingerprint
    by connecting to the same target and checking if the fingerprints
    match across network perspective.
    '''

    flags_supported = {'verify_ca'}
    flags_default = {}

    description = (
        'Check if remote presents the same certificate to the notary as it did to client,'
        ' optionally also performing verification against OpenSSL CA list (on the notary host).' )

    options_description = '\n'.join([
        'Optional list of flags, separated by any non-word characters,'
            ' optionally prefixed by "-" to disable that flag instead of enabling.',
        'Default flags: {};'.format(', '.join(flags_default) or '(none)'),
        'supported flags: {}.'.format(', '.join(flags_supported)) ])

    html_description = '''
        <p>This notary uses the NetworkPerspective verifier.</p>
        <p>Given a pair of an url and a certificate,
                the notary will confirm the authenticity in the following cases:
            <ol>
                <li>It has successfully verified the authenticity
                    before and still has the result in its cache.</li>
                <li>The server presents the same certificate to the notary as it did to you.</li>
            </ol>
        </p>
        <p>Otherwise the notary will <strong>not</strong> confirm the authenticity.</p>
        <p>Optionally, it can also be enabled to do verification against OpenSSL CA list.</p>
    '''

    def __init__(self, flags):
        self.flags = set(self.flags_default)
        if flags:
            flags = re.findall(r'\b[-+=\w]+\b', flags)
            for flag in flags:
                disable = False
                if flag[0] == '-': flag, disable = flag[1:], True
                if flag not in self.flags_supported:
                    raise OptionsError(( 'Passed flag {!r} is not supported.'
                        ' Full list of supported flags: {}' ).format(flag, ', '.join(self.flags_supported)))
                if disable: self.flags.discard(flag)
                else: self.flags.add(flag)
        log.debug('Enabled options: {}'.format(', '.join(self.flags)))

    def verify(self, host, port, fingerprint):
        deferred = defer.Deferred()
        factory = CertificateFetcherClientFactory(deferred, host, port)
        contextFactory = CertificateContextFactory(
            deferred, fingerprint, verify_ca='verify_ca' in self.flags,
            # Don't use SNI for IP addresses
            sni_hostname=host if not re.search(r'^(\d+\.){3}\d+$', host) else None )

        log.debug('Fetching certificate from: ' + host + ':' + str(port))

        reactor.connectSSL(host, port, factory, contextFactory)
        return deferred


class CertificateFetcherClient(Protocol):

    def connectionMade(self):
        log.debug('Connection made...')


class CertificateFetcherError(Exception): pass

class CertificateFetcherClientFactory(ClientFactory):

    noisy = False
    protocol = CertificateFetcherClient

    def __init__(self, deferred, host, port):
        self.deferred, self.host, self.port = deferred, host, port

    def clientConnectionFailed(self, connector, reason):
        try:
            raise CertificateFetcherError(
                'Connection to ({!r}, {!r}) failed - {}'\
                .format(self.host, self.port, reason.getErrorMessage()) )
        except: self.deferred.errback()

    def clientConnectionLost(self, connector, reason):
        log.debug('Connection lost')

        if not self.deferred.called:
            log.debug('Lost before verification callback')
            try: raise CertificateFetcherError('Connection lost')
            except: self.deferred.errback()


class CertificateContextFactory(ssl.ContextFactory):

    isClient = True

    def __init__(self, deferred, fingerprint, verify_ca, sni_hostname=None):
        self.deferred, self.fingerprint = deferred, fingerprint
        self.verify_ca, self.sni_hostname = verify_ca, sni_hostname

    def handshake_callback(self, conn, stage, errno):
        if self.sni_hostname:
            conn.set_tlsext_host_name(self.sni_hostname)
            self.sni_hostname = None

    def getContext(self):
        ctx = Context(SSLv23_METHOD)
        ctx.load_verify_locations(ca_certs_pem, '/etc/ssl/certs')
        ctx.set_verify(VERIFY_PEER | VERIFY_FAIL_IF_NO_PEER_CERT, self.verifyCertificate)
        ctx.set_options(OP_NO_SSLv2)
        if self.sni_hostname: ctx.set_info_callback(self.handshake_callback)
        return ctx

    def verifyCertificate(self, connection, x509, errno, depth, preverify_ok):
        if depth != 0: return True
        log.debug('Verifying certificate (ca check: {})'.format(preverify_ok))

        fingerprintSeen = x509.digest('sha1')\
            if not self.verify_ca or preverify_ok else None
        if fingerprintSeen == self.fingerprint:
            self.deferred.callback((200, fingerprintSeen))
        else:
            self.deferred.callback((409, fingerprintSeen))

        return False


verifier = NetworkPerspectiveVerifier