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

from convergence.FingerprintDatabase import FingerprintDatabase
from convergence.NotaryResponse import NotaryResponse

from twisted.protocols.basic import FileSender
from twisted.internet import defer
from twisted.web import resource, server, error, iweb

try: from twisted.web.template import renderElement
except ImportError: renderElement = None

import os, hashlib, json, base64, types, logging

log = logging.getLogger(__name__)


class TaggedLogger(object):
    'Wraps logger to produce lines with a random tag prefix.'

    def __init__(self, logger):
        self.logger = logger
        self.tag = os.urandom(3).encode('base64').rstrip('=\n').replace('/', '-')

    def __getattr__(self, k):
        return lambda msg: getattr(self.logger, k)('[{}] {}'.format(self.tag, msg))


# This class is responsible for responding to actions
# on the REST noun 'target,' which results in triggering
# verification or returning certificate histories for
# a destination target.

class TargetPage(resource.Resource):

    isLeaf = True

    def __init__(self, databaseConnection, privateKey, verifier):
        self.database = FingerprintDatabase(databaseConnection)
        self.verifier, self.privateKey = verifier, privateKey

    def sendErrorResponse(self, request, code, message):
        if request._disconnected: return
        request.setResponseCode(code)
        request.write('<html><body>' + message + '</body></html>')
        request.finish()

    def sendResponse(self, request, code, recordRows):
        if request._disconnected:
            request.log.debug('Lost connection to client before response')
            return
        response = NotaryResponse(request, self.privateKey)
        response.sendResponse(code, recordRows)

    def isCacheMiss(self, recordRows, fingerprint):
        if not recordRows: return True
        if fingerprint == None: return False
        for row in recordRows:
            if row[0] == fingerprint: return False
        return True

    @defer.inlineCallbacks
    def updateCache(self, request, host, port, submittedFingerprint):
        try:
            code, fingerprint =\
                yield self.verifier.verify(host, int(port), submittedFingerprint, request.log)
        except Exception as err:
            request.log.warn('Fetch certificate error: {}'.format(err))
            raise

        request.log.debug('Got fingerprint: {}'.format(fingerprint))
        if fingerprint is None: defer.returnValue((code, None))
        else:
            try:
                recordRows = yield self.database.updateRecordsFor(host, port, fingerprint)
            except Exception as err:
                request.log.warn('Update records error: {}'.format(err))
                raise
            else: defer.returnValue((code, recordRows))

    @defer.inlineCallbacks
    def getRecordsComplete(self, recordRows, request, host, port, fingerprint):
        if self.isCacheMiss(recordRows, fingerprint):
            request.log.debug('Handling cache miss...')
            try: code, recordRows = yield self.updateCache(request, host, port, fingerprint)
            except Exception as err:
                request.log.warn('Certificate-fetch handling error: {}'.format(err))
                self.sendErrorResponse(request, 503, 'Internal Error')
            else: self.sendResponse(request, code, recordRows)
        else: self.sendResponse(request, 200, recordRows)

    def getRecordsError(self, error, request):
        request.log.warn('Get records error: {}'.format(error))
        self.sendErrorResponse(request, 503, 'Error retrieving records.')

    def render(self, request):
        request.log = TaggedLogger(log)

        if request.method != 'POST' and request.method != 'GET':
            self.sendErrorResponse(request, 405, 'Unsupported method.')
            return

        if len(request.postpath) == 0:
            self.sendErrorResponse(request, 400, 'You must specify a target.')
            return

        target, fingerprint = request.postpath[0], None

        if '+' not in target:
            self.sendErrorResponse(request, 400, 'Destination port must be specified.')
            return

        host, port = target.split('+')

        if request.method == 'POST':
            if 'fingerprint' not in request.args:
                self.sendErrorResponse(request, 400, 'Fingerprint must be specified.')
                return
            else:
                fingerprint = request.args['fingerprint'][0]
                request.log.debug('Fingerprint: {}'.format(fingerprint))

        deferred = self.database.getRecordsFor(host, port)
        deferred.addCallback(self.getRecordsComplete, request, host, port, fingerprint)
        deferred.addErrback(self.getRecordsError, request)

        return server.NOT_DONE_YET


class InfoPage(resource.Resource):

    isLeaf = True

    def __init__(self, verifier):
        self.verifier = verifier

    def render(self, request):
        if request.method != 'GET':
            raise error.UnsupportedMethod()

        try: description = self.verifier.getInfoNode(request)
        except NotImplementedError:
            description = self.verifier.__class__.__name__
            request.setHeader('Content-Type', 'text/plain')

        if not isinstance(description, types.StringTypes):
            if not renderElement or\
                not iweb.IRenderable.providedBy(description): description = str(description)
            else: return renderElement(request, description)

        return description
