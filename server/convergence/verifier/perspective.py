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

    opts_default = dict(verify_ca=False, bind=None)

    description = (
        'Check if remote presents the same certificate to the notary as it did to client,'
        ' optionally also performing verification against OpenSSL CA list (on the notary host).' )

    options_description = '\n'.join([
        'List of options in "[-]key1[=value1] [-]key2[=value2] ..."'
            ' format, separated by spaces or commas.',
        'Boolean flags can be prefixed with "-" to disable them,'
            ' otherwise will be enabled if specified without a value.',
        'Example: verify_ca bind=10.1.2.3',
        'Default options: {}.'.format(
            ', '.join(map('{0[0]}={0[1]}'.format, opts_default.viewitems())) or '(none)' ) ])

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

    def __init__(self, opts):
        self.opts = self.opts_default.copy()
        if opts:
            for opt in re.findall(r'[^,\s]+', opts):
                value = True
                if opt[0] == '-': opt, value = opt[1:], False
                elif '=' in opt:
                    opt, value = opt.split('=', 1)
                    if value.lstrip('-').isdigit(): value = int(value)
                if opt not in self.opts_default:
                    raise OptionsError(( 'Passed option {!r} is not supported.'
                        ' Full list of supported options: {}' ).format(opt, ', '.join(self.opts_default)))
                self.opts[opt] = value

        if self.opts['bind']:
            bind = self.opts['bind'].rsplit(':', 1)
            self.opts['bind'] = (bind[0], int(bind[1])) if len(bind) != 1 else (bind[0], 0)

        log.debug('Options: %s', self.opts)

    def verify(self, host, port, address, fingerprint, log):
        deferred = defer.Deferred()
        factory_ctx = CertificateContextFactory(
            deferred, fingerprint, log=log, verify_ca=self.opts.get('verify_ca'),
            # Don't use SNI/matching for IP addresses
            hostname=host if not re.search(r'^(\d+\.){3}\d+$', host) else None )
        factory = CertificateFetcherClientFactory(deferred, host, port, factory_ctx, log)

        log.debug('Fetching certificate from: %s:%s', host, port)

        reactor.connectSSL( address or host, port,
            factory, factory_ctx, bindAddress=self.opts['bind'] )
        return deferred


class CertificateFetcherClient(Protocol):

    def connectionMade(self):
        self.log.debug('Connected to %s', self.transport.getPeer())


class CertificateFetcherError(Exception): pass

class CertificateFetcherClientFactory(ClientFactory, object):

    noisy = False
    protocol = CertificateFetcherClient

    def __init__(self, deferred, host, port, ctx, log):
        self.deferred, self.host, self.port = deferred, host, port
        self.ctx, self.log = ctx, log

    def buildProtocol(self, addr):
        self.ctx.address = addr.host # for later verification
        p = super(CertificateFetcherClientFactory, self).buildProtocol(addr)
        p.log = self.log
        return p

    def clientConnectionFailed(self, connector, reason):
        try:
            raise CertificateFetcherError(
                'Connection to ({!r}, {!r}) failed - {}'\
                .format(self.host, self.port, reason.getErrorMessage()) )
        except: self.deferred.errback()

    def clientConnectionLost(self, connector, reason):
        self.log.debug('Connection lost')

        if not self.deferred.called:
            self.log.debug('Connection lost before verification callback')
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

def _addr_to_tuple(addr):
    try: return map(int, addr.split('.'))
    except ValueError: return None

def match_x509(x509, hostname=None, address=None):
    'match_hostname() function from Python 3.2.2, adapted to work with pyOpenSSL.'
    if address:
        if ':' in address: raise ValueError('IPv6 addresses ({}) are not supported'.format(address))
        address = _addr_to_tuple(address)
    patterns = list()
    for ext in xrange(x509.get_extension_count()):
        ext = x509.get_extension(ext)
        if ext.get_short_name() == 'subjectAltName':
            for val in str(ext).split(','):
                val = val.strip()
                if hostname and val.startswith('DNS:'):
                    if _dnsname_to_pat(val[4:]).match(hostname): return
                    patterns.append(val[4:])
                if address and val.startswith('IP:'):
                    if address == _addr_to_tuple(val[3:]): return
                    patterns.append(val[3:])
    if not patterns:
        val = x509.get_subject().commonName
        if hostname and _dnsname_to_pat(val).match(hostname): return
        if address and address == _addr_to_tuple(val): return
        patterns.append(val)
    raise CertificateError(( 'Hostname/address {!r}/{!r} does not'
        ' match any of: {}' ).format(hostname, address, ', '.join(map(repr, patterns))))


class CertificateContextFactory(ssl.ContextFactory):

    isClient = True
    hostname = address = None

    def __init__(self, deferred, fingerprint, log, verify_ca, hostname=None):
        self.deferred, self.fingerprint, self.log = deferred, fingerprint, log
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
        self.log.debug('Verifying certificate (ca check: %s)', preverify_ok)

        try:
            fingerprintSeen = x509.digest('sha1')\
                if not self.verify_ca or preverify_ok else None

            if fingerprintSeen == self.fingerprint:
                if self.verify_ca and (self.hostname or self.address):
                    try: match_x509(x509, self.hostname, self.address)
                    except CertificateError as err:
                        self.log.debug('Failed to match certificate against hostname: %s', err)
                        fingerprintSeen = None # so that it won't get cached
                        raise
                self.deferred.callback((200, fingerprintSeen))

            else:
                raise CertificateError(fingerprintSeen)

        except CertificateError:
            self.deferred.callback((409, fingerprintSeen))

        return False


verifier = NetworkPerspectiveVerifier
