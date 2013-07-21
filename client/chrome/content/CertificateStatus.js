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

Components.utils.import('resource://gre/modules/ctypes.jsm');

/**
  * This class pulls out the notary vote results for the currently
  * rendered page.
  *
  **/

function CertificateStatus(convergenceManager) {
  CV9BLog.ui('CertificateStatus constructor called : ' + convergenceManager.nssFile.path);
  NSS.initialize(convergenceManager.nssFile.path);
  CV9BLog.ui('Constructed!');
}

CertificateStatus.prototype.getInvalidCertificate = function(destination) {
  CV9BLog.ui('Getting invalid certificate for: ' + destination);

  var badCertService = null;
  // FF <= 19
  if (typeof Components.classes['@mozilla.org/security/recentbadcerts;1'] !== 'undefined') {
    badCertService = Components.classes['@mozilla.org/security/recentbadcerts;1']
    .getService(Components.interfaces.nsIRecentBadCertsService);
  }
  // FF >= 20
  else if (typeof Components.classes['@mozilla.org/security/x509certdb;1'] !== 'undefined') {

    var certDB = Components.classes['@mozilla.org/security/x509certdb;1']
      .getService(Components.interfaces.nsIX509CertDB);
    if (!certDB) return null;

    var privateMode = false;
    // Seem to be unavailable in Nightly 24.0a1, so just to be safe...
    if (typeof Components.classes['@mozilla.org/privatebrowsing;1'] !== 'undefined')
      privateMode = Components.classes['@mozilla.org/privatebrowsing;1']
        .getService(Components.interfaces.nsIPrivateBrowsingService).privateBrowsingEnabled;

    badCertService = certDB.getRecentBadCerts(privateMode);
  }
  else {
    throw 'Failed to get "bad cert db" service (too new firefox version?)';
  }

  if (!badCertService)
    return null;

  var badCertStatus = badCertService.getRecentBadCert(destination);

  if (badCertStatus != null) {
    return badCertStatus.serverCert;
  } else {
    return null;
  }
};

CertificateStatus.prototype.getCertificateForCurrentTab = function() {
  var browser = gBrowser.selectedBrowser;

  if (browser.currentURI.scheme != 'https')
    return null;

  var securityProvider = browser.securityUI.QueryInterface(Components.interfaces.nsISSLStatusProvider);

  if (securityProvider.SSLStatus != null) {
    return securityProvider.SSLStatus.serverCert;
  } else {
    var port = browser.currentURI.port == -1 ? 443 : browser.currentURI.port;
    return this.getInvalidCertificate(browser.currentURI.host + ':' + port);
  }
};

CertificateStatus.prototype.getVerificationStatus = function(certificate) {
  var len = {};
  var derEncoding = certificate.getRawDER(len);

  var derItem = NSS.types.SECItem();
  derItem.data = NSS.lib.ubuffer(derEncoding);
  derItem.len = len.value;

  var completeCertificate = NSS.lib.CERT_DecodeDERCertificate(derItem.address(), 1, null);

  var extItem = NSS.types.SECItem();
  var status = NSS.lib.CERT_FindCertExtension(
    completeCertificate, NSS.lib.SEC_OID_NS_CERT_EXT_COMMENT, extItem.address() );

  if (status != -1) {
    var encoded = '';
    var asArray = ctypes.cast(extItem.data, ctypes.ArrayType(ctypes.unsigned_char, extItem.len).ptr).contents;
    var marker = false;

    for (var i=0;i<asArray.length;i++) {
      if (marker) {
        encoded += String.fromCharCode(asArray[i]);
      } else if (asArray[i] == 0x00) {
        marker = true;
      }
    }

    return JSON.parse(encoded);
  }
};

CertificateStatus.prototype.getCurrentTabStatus = function() {
  CV9BLog.ui('Getting current tab status...');
  var certificate = this.getCertificateForCurrentTab();

  if (certificate != null) {
    return this.getVerificationStatus(certificate);
  }

  return null;
};
