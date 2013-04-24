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
import os, sys, logging


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

    default_db_path = '/var/lib/convergence/convergence.db'

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
        cmd.add_argument('-d', '--db', metavar='path', default=default_db_path,
            help='SQLite database path (default: %(default)s).')
        cmd.add_argument('-b', '--backend',
            metavar='perspective|dns:<host>', default='perspective',
            help='Verifier backend (default: %(default)s). Available backends: perspective, dns.')

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
    if opts.call == 'notary': install_reactor()

    # TODO: proper logging configuration or at least twisted-logging observer
    logging.basicConfig(
        level=logging.INFO if not opts.debug else logging.DEBUG,
        format='%(asctime)s :: %(name)s :: %(levelname)s: %(message)s' )

    if opts.call == 'notary':
        from convergence.notary import pick_backend, run_notary
        backend = pick_backend(opts.backend)
        if not backend: parser.error('Invalid backend: {}'.format(opts.backend))
        return run_notary(opts, backend)

    elif opts.call == 'bundle':
        from convergence.bundle import promptForBundleInfo, writeBundle

        # Try to provide nicer prompt with editing/history
        try:
            import readline
            readline.parse_and_bind('tab: complete')
        except: pass

        bundle = promptForBundleInfo()
        return writeBundle(bundle, opts.output_file)

    elif opts.call == 'createdb':
        from sqlite3 import connect

        db_dir = dirname(opts.db_path)
        if not exists(db_dir): os.makedirs(db_dir)

        with connect(opts.db_path) as connection,\
                closing(connection.cursor()) as cursor:
            return cursor.execute(
                'CREATE TABLE fingerprints (id integer'
                ' primary key, location TEXT, fingerprint TEXT, timestamp_start'
                ' INTEGER, timestamp_finish INTEGER)' )

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


if __name__ == '__main__': main()
