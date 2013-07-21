
function MultiDestinationConnector() {

}

MultiDestinationConnector.prototype.makeConnection = function(destinations) {
  var addresses = this.resolveNames(destinations);
  var sockets = this.makeSockets(addresses);
  var pollfds = this.makePollfds(sockets);
  var connectionIndex = this.waitForConnection(pollfds);

  this.freePollfds(pollfds, connectionIndex);
  this.freeAddresses(addresses);

  if (connectionIndex == -1) {
    throw 'MultiDestination connection failed!';
  } else {
    // this.makeBlocking(pollfds[connectionIndex].fd);
    return new ConvergenceClientSocket(null, null, null, pollfds[connectionIndex].fd);
  }
};

MultiDestinationConnector.prototype.makeBlocking = function(fd) {
  var socketOption = NSPR.types.PRSocketOptionData({'option' : 0, 'value' : 0});
  var status = NSPR.lib.PR_SetSocketOption(fd, socketOption.address());

  CV9BLog.proto('Switch back to blocking status: ' + status + ' , ' + NSPR.lib.PR_GetError());
};

MultiDestinationConnector.prototype.waitForConnection = function(pollfds, addresses) {
  var activeCount = pollfds.length;

  if (activeCount == 0) {
    return -1;
  }

  CV9BLog.proto('Active count: ' + activeCount);

  while (true) {
    var eventCount = NSPR.lib.PR_Poll(pollfds, pollfds.length, 5000);

    if (eventCount == -1) {
      CV9BLog.proto('MultiDestination poll failed!');
      return -1;
    }

    if (eventCount == 0) {
      CV9BLog.proto('MultiDestination poll timeout!');
      return -1;
    }

    for (var i=0;i<pollfds.length;i++) {
      if (pollfds[i].out_flags != 0) {
        var connectedStatus = NSPR.lib.PR_ConnectContinue(pollfds[i].fd, pollfds[i].out_flags);

        if (connectedStatus == 0) {
          CV9BLog.proto('Got connected event: '  + i + '!');
          return i;
        } else if (NSPR.lib.PR_GetError() != NSPR.lib.PR_IN_PROGRESS) {
          CV9BLog.proto('Got error event: ' + i + '!');
          if (--activeCount <= 0) {
            CV9BLog.proto('All MultiDestination polls failed!');
            return -1;
          }

          pollfds[i].in_flags = 0;
        }
      }
    }
  }
};

MultiDestinationConnector.prototype.freePollfds = function(pollfds, index) {
  for (var i=0;i<pollfds.length;i++) {
    if (i != index)
      NSPR.lib.PR_Close(pollfds[i].fd);
  }
};

MultiDestinationConnector.prototype.freeAddresses = function(addresses) {
  for (var i=0;i<addresses.length;i++) {
    NSPR.lib.PR_Free(addresses[i]);
  }
};

MultiDestinationConnector.prototype.makePollfds = function(sockets) {
  var pollfds_t = ctypes.ArrayType(NSPR.types.PRPollDesc);
  var pollfds = new pollfds_t(sockets.length);

  for (var i=0;i<sockets.length;i++) {
    pollfds[i].fd = sockets[i];
    pollfds[i].in_flags = NSPR.lib.PR_POLL_WRITE | NSPR.lib.PR_POLL_EXCEPT;
    pollfds[i].out_flags = 0;
  }

  return pollfds;
};

MultiDestinationConnector.prototype.makeSockets = function(addresses) {
  var results = new Array();
  var resultsIndex = 0;

  for (var i=0;i<addresses.length;i++) {
    var fd = NSPR.lib.PR_OpenTCPSocket(NSPR.lib.PR_AF_INET);

    if (fd == null) {
      CV9BLog.proto('Unable to construct socket!');
      continue;
    }

    var socketOption = NSPR.types.PRSocketOptionData({'option' : 0, 'value' : 1});

    NSPR.lib.PR_SetSocketOption(fd, socketOption.address());

    var status = NSPR.lib.PR_Connect(fd, addresses[i], NSPR.lib.PR_SecondsToInterval(10));

    if ((status == 0) && (NSPR.lib.PR_GetError() != NSPR.lib.PR_WOULD_BLOCK_ERROR)) {
      NSPR.lib.PR_Close(fd);
      continue;
    }

    results[resultsIndex++] = fd;
  }

  return results;
};

MultiDestinationConnector.prototype.resolveNames = function(destinations) {
  var results = new Array();
  var resultsIndex = 0;

  for (var i=0;i<destinations.length;i++) {
    var addrInfo = NSPR.lib.PR_GetAddrInfoByName(
      destinations[i].host, NSPR.lib.PR_AF_INET, NSPR.lib.PR_AI_ADDRCONFIG );

    if (addrInfo == null || addrInfo.isNull()) {
      CV9BLog.proto('DNS lookup failed: ' + NSPR.lib.PR_GetError());
      continue;
    }

    var netAddressBuffer = NSPR.lib.PR_Malloc(1024);
    var netAddress = ctypes.cast(netAddressBuffer, NSPR.types.PRNetAddr.ptr);

    NSPR.lib.PR_EnumerateAddrInfo(null, addrInfo, 0, netAddress);
    NSPR.lib.PR_SetNetAddr(
      NSPR.lib.PR_IpAddrNull, NSPR.lib.PR_AF_INET, destinations[i].port, netAddress );

    NSPR.lib.PR_FreeAddrInfo(addrInfo);

    results[resultsIndex++] = netAddress;
  }

  return results;
};
