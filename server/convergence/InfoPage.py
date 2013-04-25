#-*- coding: utf-8 -*-
from __future__ import print_function

from twisted.web.resource import Resource
from twisted.web.error import UnsupportedMethod
from twisted.web.server import NOT_DONE_YET
from twisted.web.iweb import IRenderable

try: from twisted.web.template import renderElement
except ImportError: renderElement = None

import types


class InfoPage(Resource):

    isLeaf = True

    def __init__(self, verifier):
        self.verifier = verifier

    def render(self, request):
        if request.method != 'GET':
            raise UnsupportedMethod()

        try: description = self.verifier.getInfoNode(request)
        except NotImplementedError:
            description = self.verifier.__class__.__name__
            request.setHeader('Content-Type', 'text/plain')

        if not isinstance(description, types.StringTypes):
            if not renderElement or\
                not IRenderable.providedBy(description): description = str(description)
            else: return renderElement(request, description)

        return description
