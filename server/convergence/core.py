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


from contextlib import contextmanager, closing
from os.path import exists, dirname, realpath
import os, sys, logging, pkg_resources


# Check python version
if sys.version_info < (2, 7):
    print('Sorry, convergence requires at least Python 2.7', file=sys.stderr)
    sys.exit(3)

# Extend sys.path, if run from the checkout tree
try: import convergence
except ImportError:
    sys.path.insert(0, dirname(dirname(realpath(__file__))))
    import convergence

from convergence import __version__


default_db_path = '/var/lib/convergence/convergence.db'
default_backend = 'perspective'
default_proxied_tls_port = 4242


def install_reactor():
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
    from twisted.internet import reactor
    return reactor


def get_backend_list():
    from os.path import join, dirname, basename
    from convergence import verifier
    import glob, importlib

    base_verifiers = set( basename(p)[:-3] for p in
        glob.iglob(join(dirname(verifier.__file__), '[!_]*.py')) )
    backends = dict( (ep.name, ep)
        for ep in pkg_resources.iter_entry_points('convergence.verifier') )

    # If convergence is ran from a checkout tree,
    #  shipped entry_points won't be found, so make sure they are
    base_verifiers.difference_update(backends)

    for name in base_verifiers:
        mod = importlib.import_module('convergence.verifier.{}'.format(name))
        backends[name] = type( 'EntryPoint', (object,),
            dict(name=name, load=lambda s,mod=mod: mod) )()

    return backends


def build_notary(opts, verifier):
    from convergence.pages import TargetPage, InfoPage
    from convergence.ConnectChannel import ConnectChannel

    from twisted.web import http, server, resource
    from twisted.application import strports, service
    from twisted.enterprise import adbapi

    cert_key_path = opts.cert_key or opts.cert
    cert_key = open(opts.cert_key or opts.cert).read() # TODO: is it really used?
    # See http://twistedmatrix.com/trac/ticket/3629
    #  for the rationale behind check_same_thread=False
    database = adbapi.ConnectionPool( 'sqlite3',
        opts.db, cp_max=1, cp_min=1, check_same_thread=False )

    connectFactory = http.HTTPFactory(timeout=10)
    connectFactory.protocol = ConnectChannel

    notary = resource.Resource()
    notary.putChild('', InfoPage(verifier))
    notary.putChild('target', TargetPage(database, cert_key, verifier))
    notaryFactory = server.Site(notary)

    # It'd be easier and more flexible to specify endpoints in config, but we don't have one yet
    ep_interface = '' if not opts.interface else ':interface={}'.format(opts.interface)
    tls_endpoint = 'tcp:{{}}{}'.format(ep_interface) if opts.no_https else\
        'ssl:{{}}{}:certKey={}:privateKey={}'.format(ep_interface, opts.cert, cert_key_path)

    app = service.MultiService()
    strports\
        .service('tcp:{}{}'.format(opts.proxy_port, ep_interface), connectFactory)\
        .setServiceParent(app)
    strports\
        .service(tls_endpoint.format(opts.tls_port), notaryFactory)\
        .setServiceParent(app)
    if opts.tls_port_proxied:
        strports\
            .service(tls_endpoint.format(opts.tls_port_proxied), notaryFactory)\
            .setServiceParent(app)

    return app


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        description='Convergence {} by Moxie Marlinspike.'.format(__version__))
    parser.add_argument('-v', '--verbose',
        action='store_true', help='Verbose operation mode (most logging from twisted).')
    parser.add_argument('--debug',
        action='store_true', help='Even more verbose operation than with --verbose.')
    cmds = parser.add_subparsers(
        title='Supported operations (have their own suboptions as well)')

    @contextmanager
    def subcommand(name, **kwz):
        cmd = cmds.add_parser(name, **kwz)
        cmd.set_defaults(call=name)
        yield cmd

    with subcommand('notary', help='Start notary daemon.') as cmd:
        cmd.add_argument('-p', '--proxy-port', type=int, metavar='port', default=80,
            help='Port to listen on for CONNECT requests'
                ' to act as proxy to other notaries (default: %(default)s).')
        cmd.add_argument('-s', '--tls-port', type=int, metavar='port', default=443,
            help='Port to listen on for direct TLS connections (default: %(default)s).')
        cmd.add_argument('-x', '--tls-port-proxied', type=int, metavar='port',
            help=( 'Port to listen on for proxied TLS connections'
                        ' (default: {}, unless --no-https is specified).'
                    ' Must be 4242 for the outside world, because proxies only accept that one.'
                    ' Disabled (unless explicitly specified) if --no-https is also used -- reverse-proxy'
                        ' should be set to pass connections to --tls-port in that case instead.' )\
                .format(default_proxied_tls_port))
        cmd.add_argument('--no-https', action='store_true',
            help='Turn off TLS wrapping for all sockets, e.g. to put Twisted behind Nginx.'
                ' Also disables --tls-port-proxied (unless explicitly specified) as redundant'
                    ' -- these connections should be proxied to the same --tls-port instead.')
        cmd.add_argument('-i', '--interface', metavar='ip_or_hostname',
            help='Interface (IP address or hostname) to listen on for incoming connections (optional).')
        cmd.add_argument('-c', '--cert', metavar='path', required=True, help='TLS certificate path.')
        cmd.add_argument('-k', '--cert-key', metavar='path',
            help='TLS private key path. Not necessary if also contained in the --cert file.')
        cmd.add_argument('-d', '--db', metavar='path', default=default_db_path,
            help='SQLite database path (default: %(default)s).')
        cmd.add_argument('-b', '--backend', metavar='name',
            help='Verifier backend (default: %(default)s).'
                ' Specify "help" or "list" to list available backends and their options.')
        cmd.add_argument('-o', '--backend-options', metavar='data',
            help='Backend-specific options-string (e.g. host to query'
                ' for "dns" backend), use "-b help" to get more info on these.')

    with subcommand('bundle',
            help='Produce notary "bundles", which can be easily imported to a web browser.') as cmd:
        cmd.add_argument('output_file',
            nargs='?', default='mynotarybundle.notary',
            help='Path to write resulting bundle to (default: %(default)s).')

    with subcommand('createdb', help='Construct Convergence Notary database.') as cmd:
        cmd.add_argument('db_path', nargs='?', default=default_db_path,
            help='SQLite database path (default: %(default)s).')

    with subcommand('gencert', help='Generates TLS certificates.') as cmd:
        cmd.add_argument('-c', '--cert', metavar='path', default='mynotary.pem',
            help='Generated TLS certificate path (default: %(default)s.')
        cmd.add_argument('-k', '--cert-key', metavar='path',
            help='Generated TLS certificate private key path'
                ' (defaults to --cert name + ".key", e.g. "mynotary.key").')
        cmd.add_argument('-s', '--cert-subject', metavar='tls_subject',
            help='Subject of a generated TLS cert (default: prompt interactively).')
        cmd.add_argument('-b', '--rsa-key-size', metavar='bits', type=int, default=2048,
            help='Size of the generated cert RSA key in bits (e.g. 2048 or 4096, default: %(default)s).')
        cmd.add_argument('--cert-expire', metavar='days', type=int, default=14600,
            help='Expiration period for generated cert in days (default: %(default)s).')

    opts = parser.parse_args(argv if argv is not None else sys.argv[1:])

    # This must be done before any other twisted-related stuff:
    if opts.call == 'notary': reactor = install_reactor()

    # TODO: extended logging configuration
    from twisted.python import log as twisted_log
    if opts.debug: log = logging.DEBUG
    elif opts.verbose: log = logging.INFO
    else: log = logging.WARNING
    logging.basicConfig( level=log,
        format='%(asctime)s :: %(name)s :: %(levelname)s: %(message)s' )
    twisted_log.PythonLoggingObserver().start()
    log = logging.getLogger('convergence.core')

    if opts.call == 'notary':
        if opts.tls_port_proxied is None and not opts.no_https:
            opts.tls_port_proxied = default_proxied_tls_port # stays disabled otherwise

        from convergence.verifier import OptionsError

        # To present list of these in CLI help
        backends = get_backend_list()
        if not opts.backend and default_backend in backends:
            opts.backend = default_backend
        if not opts.backend or opts.backend in ['help', 'list']:
            import textwrap
            indent = 2
            print('Available verifier backends:')
            for name, ep in sorted(backends.viewitems()):
                print('\n{}- {}'.format(' '*indent, name))
                backend = ep.load().verifier
                for k, desc in [
                        ('Description', backend.description),
                        ('Options', backend.options_description) ]:
                    if desc:
                        print('\n{}{}:'.format(' '*indent*2, k))
                        print(textwrap.fill( desc.strip(), width=78,
                            initial_indent=' '*indent*3, subsequent_indent=' '*indent*3 ))
            print()
            if not opts.backend: parser.error('Backend name must be specified.')
            return

        try: backend = backends[opts.backend]
        except KeyError:
            parser.error(
                'Invalid backend (available: {}): {}'\
                .format(', '.join(backends), opts.backend) )
        try: backend = backend.load().verifier(opts.backend_options)
        except OptionsError as err: parser.error(err.message)

        build_notary(opts, backend).startService()

        log.debug('Convergence Notary started...')
        reactor.run()
        log.debug('Convergence Notary stopped')
        return

    elif opts.call == 'bundle':
        from convergence.bundle import promptForBundleInfo, writeBundle

        # Try to provide nicer prompt with editing/history
        try:
            import readline
            readline.parse_and_bind('tab: complete')
        except: pass

        bundle = promptForBundleInfo()
        writeBundle(bundle, opts.output_file)
        return

    elif opts.call == 'createdb':
        from sqlite3 import connect

        db_dir = dirname(realpath(opts.db_path))
        if not exists(db_dir): os.makedirs(db_dir)

        with connect(opts.db_path) as connection,\
                closing(connection.cursor()) as cursor:
            cursor.execute(
                'CREATE TABLE fingerprints (id integer'
                ' primary key, location TEXT, fingerprint TEXT, timestamp_start'
                ' INTEGER, timestamp_finish INTEGER)' )
        return

    elif opts.call == 'gencert':
        from subprocess import Popen, PIPE
        from tempfile import NamedTemporaryFile

        with open(os.devnull, 'w') as devnull:
            if Popen(['openssl', 'version'], stdout=devnull).wait():
                return print('Failed to run "openssl" binary. You must install OpenSSL first!')

        if opts.cert_key is None:
            opts.cert_key = '{}.key'.format(opts.cert.rsplit('.', 1)[0])

        def run_command(*argv):
            argv = map(bytes, argv)
            err = Popen(argv).wait()
            if err:
                raise RuntimeError( 'Failed running'
                    ' command (exit code: {}): {}'.format(err, ' '.join(argv)) )

        key_path, csr_path = None, NamedTemporaryFile(dir='.', delete=False).name
        try:
            # RSA key
            run_command('openssl', 'genrsa', '-out', opts.cert_key, opts.rsa_key_size)
            key_path = opts.cert_key
            # Certificate request
            cmd = ['openssl', 'req', '-new', '-key', key_path, '-out', csr_path]
            if opts.cert_subject: cmd.extend(['-subj', opts.cert_subject])
            run_command(*cmd)
            # Sign the request
            run_command( 'openssl', 'x509', '-req', '-days',
                opts.cert_expire, '-in', csr_path, '-signkey', opts.cert_key, '-out', opts.cert )
        except RuntimeError as err:
            if key_path: os.unlink(key_path)
            return print(err.message, file=sys.stderr)
        finally: os.unlink(csr_path)

        return print('Certificate and key generated in {} and {}'.format(opts.cert, key_path))

    else: raise NotImplementedError(opts.call)
    raise AssertionError('Command {!r} did not return.'.format(opts.call))


if __name__ == '__main__': main()
