#-*- coding: utf-8 -*-

from convergence.verifier import Verifier

from twisted.internet import defer

import logging

log = logging.getLogger(__name__)


class AlwaysTrueVerifier(Verifier):
    'Verifier class that always returns positive result.'

    description = 'Verifier that always returns positive result'\
        ' and the same fingerprint as was passed to it. For testing purposes only.'

    def verify(self, host, port, address, fingerprint, log):
        return defer.succeed((200, fingerprint))


verifier = AlwaysTrueVerifier
