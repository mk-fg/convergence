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
            # Don't use SNI/matching for IP addresses
            hostname=host if not re.search(r'^(\d+\.){3}\d+$', host) else None )

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


class CertificateError(ValueError): pass

def _dnsname_to_pat(dn):
    pats = []
    for frag in dn.split(r'.'):
        if frag == '*':
            # When '*' is a fragment by itself, it matches a non-empty dotless
            # fragment.
            pats.append('[^.]+')
        else:
            # Otherwise, '*' matches any dotless fragment.
            frag = re.escape(frag)
            pats.append(frag.replace(r'\*', '[^.]*'))
    return re.compile(r'\A' + r'\.'.join(pats) + r'\Z', re.IGNORECASE)

# The match_hostname() function from Python 3.2.2
def match_hostname(x509, hostname):
    '''Verify that *cert* (in decoded format as returned by
            SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 rules
            are mostly followed, but IP addresses are not accepted for *hostname*.
        CertificateError is raised on failure. On success, the function returns nothing.'''
    if not x509: raise ValueError('empty or no certificate')
    dnsnames = list()
    for ext in xrange(x509.get_extension_count()):
        ext = x509.get_extension(ext)
        if ext.get_short_name() == 'subjectAltName':
            for val in str(ext).split(','):
                if not val.strip().startswith('DNS:'): continue
                val = val.strip()[4:]
                if _dnsname_to_pat(val).match(hostname): return
                dnsnames.append(val)
    if not dnsnames:
        # The subject is only checked when there is no dNSName entry in subjectAltName
        val = x509.get_subject().commonName
        if _dnsname_to_pat(val).match(hostname): return
        dnsnames.append(val)
    if len(dnsnames) > 1:
        raise CertificateError(( 'hostname {!r} does'
            ' not match either of {}' ).format(hostname, ', '.join(map(repr, dnsnames))))
    elif len(dnsnames) == 1:
        raise CertificateError(( 'hostname {!r} does'
            ' not match {!r}' ).format(hostname, dnsnames[0]))
    else:
        raise CertificateError( 'no appropriate'
            ' commonName or subjectAltName fields were found' )


class CertificateContextFactory(ssl.ContextFactory):

    isClient = True

    def __init__(self, deferred, fingerprint, verify_ca, hostname=None):
        self.deferred, self.fingerprint = deferred, fingerprint
        self.verify_ca, self.hostname, self.sni_sent = verify_ca, hostname, False

    def handshake_callback(self, conn, stage, errno):
        if not self.sni_sent and self.hostname:
            conn.set_tlsext_host_name(self.hostname)
            self.sni_sent = True

    def getContext(self):
        ctx = Context(SSLv23_METHOD)
        ctx.load_verify_locations(ca_certs_pem, '/etc/ssl/certs')
        ctx.set_verify(VERIFY_PEER | VERIFY_FAIL_IF_NO_PEER_CERT, self.verifyCertificate)
        ctx.set_options(OP_NO_SSLv2)
        if self.hostname: ctx.set_info_callback(self.handshake_callback)
        return ctx

    def verifyCertificate(self, connection, x509, errno, depth, preverify_ok):
        if depth != 0: return True
        log.debug('Verifying certificate (ca check: {})'.format(preverify_ok))

        try:
            fingerprintSeen = x509.digest('sha1')\
                if not self.verify_ca or preverify_ok else None

            if fingerprintSeen == self.fingerprint:
                if self.verify_ca and self.hostname:
                    try: match_hostname(x509, self.hostname)
                    except CertificateError as err:
                        log.debug('Failed to match certificate against hostname: {}'.format(err))
                        fingerprintSeen = None # so that it won't get cached
                        raise
                self.deferred.callback((200, fingerprintSeen))

            else:
                raise CertificateError(fingerprintSeen)

        except CertificateError:
            self.deferred.callback((409, fingerprintSeen))

        return False


verifier = NetworkPerspectiveVerifier
