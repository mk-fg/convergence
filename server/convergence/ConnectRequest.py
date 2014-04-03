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

from twisted.internet.protocol import BaseProtocol, ClientFactory
from twisted.internet import reactor
from twisted.web import http

import re, logging

log = logging.getLogger(__name__)


# This class is responsible for parsing incoming requests
# on the HTTP port.  The only method it supports is CONNECT,
# and will only setup a proxy tunnel to a destination port
# of 4242.

class ConnectRequest(http.Request):

    def __init__(self, channel, queued, log=log):
        http.Request.__init__(self, channel, queued)
        self.log = log

    def isValidConnectRequest(self, method, destinations):
        if (method is None or destinations is None or len(destinations) == 0):
            return False

        for destination in destinations:
            if ((destination.find(':') != -1) and (not destination.endswith(':4242'))):
                return False

            if ((destination.find('+') != -1) and (not destination.endswith('+4242'))):
                return False

        return method.strip() == 'CONNECT'

    def getDestinations(self):
        destinations = []

        if not self.uri is None:
            destinations.append(self.uri)

        headers = self.getAllHeaders()
        destinationHeaders = self.requestHeaders.getRawHeaders('x-convergence-notary')

        if destinationHeaders is not None:
            destinations.extend(destinationHeaders)

        self.log.debug('Destination(s): %s', destinations)
        return destinations

    def process(self):
        self.log.debug('Got connect request: %s', self.uri)

        destinations = self.getDestinations()

        if self.isValidConnectRequest(self.method, destinations):
            self.log.debug('Valid connect request')
            self.proxyRequest(destinations);
        else:
            self.log.debug('Denying invalid connect request')
            self.denyRequest()

    def proxyRequest(self, destinations):
        factory = NotaryConnectionFactory(self, log=self.log)
        factory.protocol = NotaryConnection

        for destination in destinations:
            if (destination.find(':') != -1):
                destination = destination.split(':')[0]
            elif (destination.find('+') != -1):
                destination = destination.split('+')[0]

            self.log.debug('Connecting to: %s', destination)

            connector = reactor.connectTCP(destination, 4242, factory)
            factory.addConnector(connector, destination)

    def denyRequest(self):
        self.setResponseCode(http.FORBIDDEN, 'Access Denied')
        self.setHeader('Connection', 'close')
        self.write( '<html>The request you issued is'
            ' not an authorized Convergence Notary request.</html>\n' )
        self.finish()


# This class is resonsible for setting up the proxy tunnel to another
# notary.
class NotaryConnection(BaseProtocol):

    def __init__(self, client, host, log=log):
        self.client = client
        self.host = host

    def connectionMade(self):
        self.log.debug('Connection made to notary: %s', self.host)
        self.client.channel.proxyConnection = self
        self.client.channel.setRawMode()
        self.client.transport.write('HTTP/1.0 200 Connection Established\r\n')
        self.client.transport.write('Proxy-Agent: Convergence\r\n')
        self.client.transport.write('X-Convergence-Notary: {}\r\n\r\n'.format(self.host))

    def dataReceived(self, data):
        self.client.transport.write(data)

    def connectionLost(self, reason):
        self.log.debug('Connection to notary lost: %s', reason)
        self.client.transport.loseConnection()

# The ConnectionFactory for a proxy tunnel to another notary.
class NotaryConnectionFactory(ClientFactory):

    def __init__(self, client, log=log):
        self.client = client
        self.connectors = []
        self.connectorHosts = {}
        self.connectedConnector = None

    def buildProtocol(self, addr):
        if self.connectedConnector is None:
            for connector in self.connectors[:]:
                if connector.state == 'connected':
                    self.connectedConnector = connector
                else:
                    self.connectors.remove(connector)
                    del self.connectorHosts[connector]
                    connector.disconnect()

            host = self.connectorHosts[self.connectedConnector]
            return NotaryConnection(self.client, host, log=self.log)

    def addConnector(self, connector, host):
        self.connectors.append(connector)
        self.connectorHosts[connector] = host

    def clientConnectionFailed(self, connector, reason):
        if connector in self.connectors:
            self.log.debug(
                'Connection to notary (%s) failed: %s',
                self.connectorHosts[connector], reason )
            self.connectors.remove(connector)
            del self.connectorHosts[connector]

        if len(self.connectors) == 0:
            self.log.warning('Connection to notary failed!')
            self.client.setResponseCode(http.NOT_FOUND, 'Unable to connect')
            self.client.setHeader('Connection', 'close')
            self.client.write('<html><body>Unable to connect to notary!</body></html>')
            self.client.finish()
