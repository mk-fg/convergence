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
  * This class manages the ctypes bridge to the SSL libraries
  * distributed with Mozilla.
  *
  **/

function SSL() {

}

SSL.initialize = function(sslPath) {
  var sharedLib;

  try {
    sharedLib = ctypes.open(sslPath);
  } catch (e) {
    CV9BLog.core('Failed to find ssl3 in installed directory, checking system paths.');
    sharedLib = ctypes.open(ctypes.libraryName('ssl3'));
  }

  SSL.types = new Object();

  SSL.types.SSLVersionRange = ctypes.StructType(
    'SSLVersionRange', [{'min' : ctypes.uint16_t}, {'max' : ctypes.uint16_t}] );

  SSL.types.SSLGetClientAuthData = ctypes.FunctionType(ctypes.default_abi,
                                                          ctypes.int,
                                                          [ctypes.voidptr_t,
                                                          NSPR.types.PRFileDesc.ptr,
                                                          NSS.types.CERTDistNames.ptr,
                                                          NSS.types.CERTCertificate.ptr.ptr,
                                                          NSS.types.SECKEYPrivateKey.ptr.ptr]).ptr;


  SSL.types.SSL_AuthCertificate = ctypes.FunctionType(ctypes.default_abi,
                                                      ctypes.int32_t,
                                                      [ctypes.voidptr_t,
                                                        NSPR.types.PRFileDesc.ptr,
                                                        ctypes.int32_t,
                                                        ctypes.int32_t]).ptr;

  SSL.lib = {
    SSL_LIBRARY_VERSION_2 : 0x0002,
    SSL_LIBRARY_VERSION_3_0 : 0x0300,
    SSL_LIBRARY_VERSION_TLS_1_0 : 0x0301,
    SSL_LIBRARY_VERSION_TLS_1_1 : 0x0302,
    SSL_LIBRARY_VERSION_TLS_1_2 : 0x0303, // nss-3.15+ only
    ssl_variant_stream : 0,
    ssl_variant_datagram : 1,

    SSL_ConfigServerSessionIDCache : sharedLib.declare('SSL_ConfigServerSessionIDCache',
                                                        ctypes.default_abi,
                                                        ctypes.int,
                                                        ctypes.int,
                                                        ctypes.uint32_t,
                                                        ctypes.uint32_t,
                                                        ctypes.char.ptr),

    SSL_ImportFD : sharedLib.declare('SSL_ImportFD',
                                          ctypes.default_abi,
                                          NSPR.types.PRFileDesc.ptr,
                                          NSPR.types.PRFileDesc.ptr,
                                          NSPR.types.PRFileDesc.ptr),

    SSL_ConfigSecureServer : sharedLib.declare('SSL_ConfigSecureServer',
                                                ctypes.default_abi,
                                                ctypes.int,
                                                NSPR.types.PRFileDesc.ptr,
                                                NSS.types.CERTCertificate.ptr,
                                                NSS.types.SECKEYPrivateKey.ptr,
                                                ctypes.int),

    SSL_GetClientAuthDataHook : sharedLib.declare('SSL_GetClientAuthDataHook',
                                                      ctypes.default_abi,
                                                      ctypes.int,
                                                      NSPR.types.PRFileDesc.ptr,
                                                      SSL.types.SSLGetClientAuthData,
                                                      ctypes.voidptr_t),


    SSL_AuthCertificateHook : sharedLib.declare('SSL_AuthCertificateHook',
                                                    ctypes.default_abi,
                                                    ctypes.int32_t,
                                                    NSPR.types.PRFileDesc.ptr,
                                                    SSL.types.SSL_AuthCertificate,
                                                    ctypes.voidptr_t),

    SSL_ResetHandshake : sharedLib.declare('SSL_ResetHandshake',
                                                ctypes.default_abi,
                                                ctypes.int32_t,
                                                NSPR.types.PRFileDesc.ptr,
                                                ctypes.int),

    SSL_ForceHandshake : sharedLib.declare('SSL_ForceHandshake',
                                                ctypes.default_abi,
                                                ctypes.int32_t,
                                                NSPR.types.PRFileDesc.ptr),

    SSL_ForceHandshakeWithTimeout : sharedLib.declare('SSL_ForceHandshakeWithTimeout',
                                                      ctypes.default_abi,
                                                      ctypes.int32_t,
                                                      NSPR.types.PRFileDesc.ptr,
                                                      ctypes.uint32_t),

    SSL_PeerCertificate : sharedLib.declare('SSL_PeerCertificate',
                                                ctypes.default_abi,
                                                NSS.types.CERTCertificate.ptr,
                                                NSPR.types.PRFileDesc.ptr),

    SSL_SetURL : sharedLib.declare('SSL_SetURL',
                                                ctypes.default_abi,
                                                ctypes.int32_t,
                                                NSPR.types.PRFileDesc.ptr,
                                                ctypes.char.ptr),

    SSL_VersionRangeSet : sharedLib.declare('SSL_VersionRangeSet',
                                                ctypes.default_abi,
                                                ctypes.int,
                                                NSPR.types.PRFileDesc.ptr,
                                                SSL.types.SSLVersionRange.ptr),
    SSL_VersionRangeSetDefault : sharedLib.declare('SSL_VersionRangeSetDefault',
                                                ctypes.default_abi,
                                                ctypes.int,
                                                ctypes.int,
                                                SSL.types.SSLVersionRange.ptr),

    NSS_FindCertKEAType : sharedLib.declare('NSS_FindCertKEAType',
                                                ctypes.default_abi,
                                                ctypes.int,
                                                NSS.types.CERTCertificate.ptr),

    NSS_GetClientAuthData : sharedLib.declare('NSS_GetClientAuthData',
                                                  ctypes.default_abi,
                                                  ctypes.int,
                                                  ctypes.voidptr_t,
                                                  NSPR.types.PRFileDesc.ptr,
                                                  NSS.types.CERTDistNames.ptr,
                                                  NSS.types.CERTCertificate.ptr.ptr,
                                                  NSS.types.SECKEYPrivateKey.ptr.ptr)
  }


  // Default is to enable TLS up to 1.0, which is known to be weak
  var ver_range = new SSL.types.SSLVersionRange;
  ver_range.min = SSL.lib.SSL_LIBRARY_VERSION_3_0;
  ver_range.max = SSL.lib.SSL_LIBRARY_VERSION_TLS_1_2;

  var status = SSL.lib.SSL_VersionRangeSetDefault(SSL.lib.ssl_variant_stream, ver_range.address());
  if (status == -1) {
    ver_range.max = SSL.lib.SSL_LIBRARY_VERSION_TLS_1_1; // nss versions before 3.15
    status = SSL.lib.SSL_VersionRangeSetDefault(SSL.lib.ssl_variant_stream, ver_range.address());
    if (status == -1) throw 'SSL_VersionRangeSetDefault failed';
  }

};
