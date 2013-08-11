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
  * This ChromeWorker is responsible for establishing an SSL connection
  * to the destination server, validating the target's SSL certificate
  * with the local cache or with the configured notaries, and then
  * establishing an SSL connection with the client.
  *
  * It then passes off the pair of established connections to its parent,
  * which hands them to the ShuffleWorker for all further shuffling.
  *
  * This is setup by the ConnectionManager in 'components.'
  *
  **/

importScripts(
  'chrome://convergence/content/Logger.js',
  'chrome://convergence/content/ctypes/NSPR.js',
  'chrome://convergence/content/ctypes/NSS.js',
  'chrome://convergence/content/ctypes/SSL.js',
  'chrome://convergence/content/ctypes/SQLITE.js',
  'chrome://convergence/content/ctypes/Serialization.js',
  'chrome://convergence/content/sockets/ConvergenceNotarySocket.js',
  'chrome://convergence/content/sockets/ConvergenceServerSocket.js',
  'chrome://convergence/content/sockets/ConvergenceClientSocket.js',
  'chrome://convergence/content/sockets/MultiDestinationConnector.js',
  'chrome://convergence/content/http/ConnectResponseParser.js',
  'chrome://convergence/content/http/HttpRequestBuilder.js',
  'chrome://convergence/content/http/HttpParser.js',
  'chrome://convergence/content/proxy/HttpProxyServer.js',
  'chrome://convergence/content/proxy/BaseProxyConnector.js',
  'chrome://convergence/content/proxy/HttpProxyConnector.js',
  'chrome://convergence/content/proxy/NotaryProxyConnector.js',
  'chrome://convergence/content/proxy/SOCKS5Connector.js',
  'chrome://convergence/content/proxy/ProxyConnector.js',
  'chrome://convergence/content/ssl/CertificateInfo.js',
  'chrome://convergence/content/ssl/Notary.js',
  'chrome://convergence/content/ssl/PhysicalNotary.js',
  'chrome://convergence/content/ssl/NativeCertificateCache.js',
  'chrome://convergence/content/ssl/ActiveNotaries.js',
  'chrome://convergence/content/ssl/CertificateManager.js',
  'chrome://convergence/content/ConvergenceResponseStatus.js' );

function sendClientResponse(localSocket, certificateManager, certificateInfo) {
  localSocket.writeBytes(NSPR.lib.buffer('HTTP/1.0 200 Connection established\r\n\r\n'), 39);
  localSocket.negotiateSSL(certificateManager, certificateInfo);
};

function checkCertificateValidity(
  certificateCache, activeNotaries, host, port, ip,
  certificateInfo, privatePkiExempt)
{
  var target = host + ':' + port;

  if (privatePkiExempt && certificateInfo.isLocalPki) {
    CV9BLog.worker_conn('Certificate is a local PKI cert.');
    return {
      'status' : true,
      'target' : target,
      'certificate' : certificateInfo.original,
      'details' : [{
        'notary' : 'Local PKI',
        'status' : ConvergenceResponseStatus.VERIFICATION_SUCCESS }] };
  }

  CV9BLog.worker_conn('Checking certificate cache: ' + certificateInfo.sha1);

  if (certificateCache.isCached(host, port, certificateInfo.sha1))
    return {
      'status' : true,
      'target' : target,
      'certificate' : certificateInfo.original,
      'details' : [{
        'notary' : 'Certificate Cache',
        'status' : ConvergenceResponseStatus.VERIFICATION_SUCCESS }] };

  CV9BLog.worker_conn('Not cached, checking notaries: ' + certificateInfo.sha1);
  var results = activeNotaries.checkValidity(host, port, ip, certificateInfo);

  if (results['status'] === true) {
    CV9BLog.worker_conn('Caching notary result: ' + certificateInfo.sha1);
    certificateCache.cacheFingerprint(host, port, certificateInfo.sha1);
    return results;
  } else {
    return results;
  }
};

onmessage = function(event) {
  var localSocket = null;
  var targetSocket = null;

  try {
    if (typeof event.data.logging === 'boolean') CV9BLog.print_all = event.data.logging;
    CV9BLog.worker_conn('Got message...');

    NSPR.initialize(event.data.nsprFile);
    NSS.initialize(event.data.nssFile);
    SSL.initialize(event.data.sslFile);
    SQLITE.initialize(event.data.sqliteFile);

    var certificateManager = new CertificateManager(event.data.certificates);
    var activeNotaries = new ActiveNotaries(event.data.settings, event.data.notaries);
    localSocket = new ConvergenceServerSocket(null, event.data.clientSocket);
    var destination = new HttpProxyServer(localSocket).getConnectDestination();
    targetSocket = new ConvergenceClientSocket(
      destination.host, destination.port, event.data.proxy );
    var certificate = targetSocket.negotiateSSL();
    var certificateInfo = new CertificateInfo(certificate);
    var certificateCache = new NativeCertificateCache(
      event.data.cacheFile, event.data.settings['cacheCertificatesEnabled'] );

    CV9BLog.worker_conn('Checking validity...');

    var results = this.checkCertificateValidity(
      certificateCache, activeNotaries,
      destination.host, destination.port, targetSocket.ip,
      certificateInfo, event.data.settings['privatePkiExempt'] );
    CV9BLog.worker_conn('Validity check results:', results);

    // Such override allows totally invalid certificates to be used,
    //  e.g. if CN and SubjectAltNames had nothing to do with the hostname/ip.
    certificateInfo.commonName = new NSS.lib.buffer(
      results['status'] === true ? destination.host : 'Invalid Certificate' );
    certificateInfo.altNames = null;

    certificateInfo.encodeVerificationDetails(results);
    this.sendClientResponse(localSocket, certificateManager, certificateInfo);
    postMessage({
      'clientFd' : Serialization.serializePointer(localSocket.fd),
      'serverFd' : Serialization.serializePointer(targetSocket.fd) });
    certificateCache.close();

    CV9BLog.worker_conn('done');
  } catch (e) {
    CV9BLog.worker_conn('exception - ' + e + ', ' + e.stack);
    if (localSocket != null) localSocket.close();
    if (targetSocket != null) targetSocket.close();
    CV9BLog.worker_conn('moving on from exception...');
  }
};
