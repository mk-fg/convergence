#-*- coding: utf-8 -*-

from convergence.verifier import Verifier

from twisted.internet import defer

import logging

log = logging.getLogger(__name__)


class AlwaysFalseVerifier(Verifier):
    'Verifier class that always returns negative result.'

    description = 'Verifier that always returns negative result. For testing purposes only.'

    def verify(self, host, port, fingerprint):
        return defer.succeed((409, None))


verifier = AlwaysFalseVerifier
