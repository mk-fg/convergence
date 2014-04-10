// Copyright (c) 2011 Moxie Marlinspike <moxie@thoughtcrime.org>
// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU General Public License as
// published by the Free Software Foundation; either version 3 of the
// License, or (at your option) any later version.

// This program is distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// General Public License for more details.

// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the Free Software
// Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
// USA


/**
  * This class is responsible for making an SSL connection to the
  * destination server the client is trying to reach.  This is the
  * first time we see the destination certificate, the validation of
  * which is what this entire game is about.
  *
  **/

function ConvergenceClientSocket(host, port, proxy, fd) {
  if (typeof fd != 'undefined') {
    this.fd = fd;
    return;
  }

  var addrInfo = NSPR.lib.PR_GetAddrInfoByName(
    proxy == null ? host : proxy.host,
    NSPR.lib.PR_AF_INET,
    NSPR.lib.PR_AI_ADDRCONFIG );

  if (addrInfo == null || addrInfo.isNull()) {
    NSPR.lib.PR_FreeAddrInfo(addrInfo);
    throw 'DNS lookup failed: ' + NSPR.lib.PR_GetError() + '\n';
  }

  var netAddressBuffer = NSPR.lib.PR_Malloc(1024);
  var netAddress = ctypes.cast(netAddressBuffer, NSPR.types.PRNetAddr.ptr);
  var error;

  try {
    NSPR.lib.PR_EnumerateAddrInfo(null, addrInfo, 0, netAddress);
    NSPR.lib.PR_SetNetAddr(
      NSPR.lib.PR_IpAddrNull, NSPR.lib.PR_AF_INET,
      proxy == null ? port : proxy.port, netAddress );

    var ip_buff = NSPR.lib.buffer(50);
    var status = NSPR.lib.PR_NetAddrToString(netAddress, ip_buff, 50);
    if (status != 0) throw 'Failed to get peer address';
    this.ip = ip_buff.readString();

    this.fd = NSPR.lib.PR_OpenTCPSocket(NSPR.lib.PR_AF_INET);
    if (this.fd == null) throw 'Unable to construct socket!\n';

    try {
      status = NSPR.lib.PR_Connect(this.fd, netAddress, NSPR.lib.PR_SecondsToInterval(5));

      if (status != 0) {
        var err_code = NSPR.lib.PR_GetError(),
          err_text = NSPR.lib.PR_ErrorToName(err_code).readString();
        throw 'Failed to connect to ' + host + ':' + port + ' -- (' + err_code + ') ' + err_text;
      }

      if (proxy != null) {
        CV9BLog.proto('Making proxied connection...');
        var proxyConnector = new ProxyConnector(proxy);
        proxyConnector.makeConnection(this, host, port);
      }

  // Make sure to close and free stuff here
    } catch (e) {
      NSPR.lib.PR_Close(this.fd);
      throw e;
    }
  } catch (e) { error = e; }

  NSPR.lib.PR_Free(netAddressBuffer);
  NSPR.lib.PR_FreeAddrInfo(addrInfo);
  if (error) throw error;

  this.host = host;
  this.port = port;
}

function allGoodAuth(arg, fd, foo, bar) {
  return 0;
}

function clientAuth(arg, fd, caNames, retCert, retKey) {
  CV9BLog.proto('Server requested client certificate...');
  var status = SSL.lib.NSS_GetClientAuthData(arg, fd, caNames, retCert, retKey);
  CV9BLog.proto('Client certificate status: ' + staus);
}

ConvergenceClientSocket.prototype.negotiateSSL = function() {
  var status;

  this.fd = SSL.lib.SSL_ImportFD(null, this.fd);
  var callbackFunction = SSL.types.SSL_AuthCertificate(allGoodAuth);
  status = SSL.lib.SSL_AuthCertificateHook(this.fd, callbackFunction, null);
  if (status == -1) throw 'Error setting auth certificate hook!';

  if (this.host) { // undefined for e.g. notary connections
    status = SSL.lib.SSL_SetURL(this.fd, this.host);
    if (status == -1) throw 'Error setting SNI hostname';
  }

  // var callbackFunction = SSL.types.SSLGetClientAuthData(clientAuth);
  // var status = SSL.lib.SSL_GetClientAuthDataHook(this.fd, callbackFunction, null);
  // if (status == -1) throw 'Error setting client auth certificate hook!';

  status = SSL.lib.SSL_ResetHandshake(this.fd, NSPR.lib.PR_FALSE);
  if (status == -1) throw 'Error resetting handshake!';

  while (
      ((status = SSL.lib.SSL_ForceHandshakeWithTimeout(
        this.fd, NSPR.lib.PR_SecondsToInterval(10) )) == -1)
      && (NSPR.lib.PR_GetError() == NSPR.lib.PR_WOULD_BLOCK_ERROR) ) {
    CV9BLog.proto('Polling on handshake...');
    if (!this.waitForInput(10000)) throw 'SSL handshake failed (timeout)';
  }
  if (status == -1) {
    // Not sure if these are correct/meaningful errors here
    var err_code = NSPR.lib.PR_GetError(),
      err_text = NSPR.lib.PR_ErrorToName(err_code).readString();
    throw 'SSL handshake failed: (' + err_code + ') ' + err_text;
  }

  return SSL.lib.SSL_PeerCertificate(this.fd);
};

ConvergenceClientSocket.prototype.available = function() {
  return NSPR.lib.PR_Available(this.fd);
};

ConvergenceClientSocket.prototype.writeBytes = function(buffer, length) {
  return NSPR.lib.PR_Write(this.fd, buffer, length);
};

ConvergenceClientSocket.prototype.readString = function(n) {
  if (n === null) n = 4095;
  else if (n <= 0) return null;

  var read, buffer = new NSPR.lib.buffer(n+1);

  while (((read = NSPR.lib.PR_Read(this.fd, buffer, n)) == -1) &&
      (NSPR.lib.PR_GetError() == NSPR.lib.PR_WOULD_BLOCK_ERROR)) {
    CV9BLog.proto('polling on read...');
    if (!this.waitForInput(8000)) return null; // TODO: hardcoded fail-timeout
  }

  if (read <= 0) {
    CV9BLog.proto('Error read: ' + read + ' , ' + NSPR.lib.PR_GetError());
    return null;
  }

  buffer[read] = 0;
  return buffer.readString();
};

ConvergenceClientSocket.prototype.readFully = function(length) {
  var buff, response = '', n = length;

  while ((buff = this.readString(n)) != null) {
    response += buff;
    n -= buff.length;
  }

  if (response.length != length) {
    throw 'Assertion error on read fully (' + read + ', ' + length + ')!';
  }

  return response;
};

ConvergenceClientSocket.prototype.close = function() {
  NSPR.lib.PR_Close(this.fd);
};

ConvergenceClientSocket.prototype.waitForInput = function(timeout_ms, timeout_ok) {
  var pollfds_t = ctypes.ArrayType(NSPR.types.PRPollDesc);
  var pollfds = new pollfds_t(1);
  pollfds[0].fd = this.fd;
  pollfds[0].in_flags = NSPR.lib.PR_POLL_READ | NSPR.lib.PR_POLL_EXCEPT;
  pollfds[0].out_flags = 0;

  var status = NSPR.lib.PR_Poll(pollfds, 1, timeout_ms);

  if (status == -1 || (!timeout_ok && status == 0)) {
    return false;
  }

  return true;
};
