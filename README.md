Convergence
--------------------

This is a fork of Moxie Marlinspike's Convergence tool: http://convergence.io/

Good high-level overview of the tool can be found in Moxie's "SSL And The Future
Of Authenticity" talk at BlackHat USA 2011: http://www.youtube.com/watch?v=Z7Wl2FW2TcA

See README in `server` section for details on running notary and `client` for
browser extension.


### Fork

 - client

   - Should work with newer firefox versions.

     - Merged fix from upstream [PR #170](https://github.com/moxie0/Convergence/pull/170).

     - Fixed major issue with extension hanging forever polling on connection to
       notary after receiving http response (bbdc538).
       Upstream [PR #173](https://github.com/moxie0/Convergence/pull/173).

     - Minor issue with displaying cached fingerprint timestamps as NaN-NaN-NaN
       (816c74e).
       Upstream [PR #174](https://github.com/moxie0/Convergence/pull/174).

   - Bumped plugin version, max ff version is 50.* and automatic upstream
     updates are disabled.

   - Backends' "isNotaryUri" check seem to have typo bugs (c96d242), messing up
     results (silently with >1 notaries).

   - Bugfix in nsIWebBrowserPersist.saveURI call (b5dbb50), preventing adding
     notaries from URL (at least in newer ff).

   - Supress unhandled non-critical JS errors here and there, mostly to keep JS
     console clean.

   - Send IP along with hostname (for e.g. SNI and cert validation) and port,
     because same name can be resolved to different hosts in case of CDNs or
     round-robin-dns mirrors, which can have unrelated certificates.

   - "Priority" checkbox in options dialog to always query marked notaries first
     (if their count is more than "subset to query" - subset is picked at
     random among these).
     Idea is to have some subset of notaries to *always* query, picking others
     at random from the rest.

   - TODO: Cache fingerprnts for (hostname, port, ip) tuples, not just
     (hostname, port), because of cdn's and round-robin-dns mirrors -
     server-side as well, though there can be several signatures for one
     hostname there.

   - TODO: "Allowed as bounce notary" checkbox in notaries' list to block local
     notaries from acting as such, for instance.

   - TODO: Make hardcoded check timeouts configurable.

       So that plugin won't hang on bogus notaries any longer than necessary
       with a specific connection latency in mind.

   - TODO: For google servers, ff interface seem to report different
     fingerprints than convergence checks - investigate whether it
     re-establishes connection between check and the actual data channel.

   - TODO: Check how other stuff like "https everywhere" gets the certs, maybe
     swap socks proxy mitm for some warning or connection-killer hook.

 - server

   - Has simplier (implementation/maintenance-wise) argparse-based CLI.

   - Renders basic info about the node on GET requests from e.g. browsers (based
     on upstream [PR #120](https://github.com/moxie0/Convergence/pull/120)).

   - Does not implement any
     [daemonization](http://0pointer.de/public/systemd-man/daemon.html) - can be
     done either naively from shell, with os-specific "start-stop-daemon" in
     init-scripts or proper init like upstart or systemd.

   - Allows more stuff to be configurable.

   - Verifier backends can be installed as a "convergence.verifier" entry points.

   - "perspective" verifier has "verify_ca" option (disabled by default) to also
     perform OpenSSL verification of the server certificate chain, allowing to
     combine network perspectives with an old-style CA-list verification (and
     whatever other backends).

   - Enable TLS SNI in "perspective" verifier during handshake, so that host can
     return appropriate cert for a hostname.

         It is done in a hackish way at the very first
         Context.set_info_callback() callback invocation.

         For a more proper way see [twisted #5374](http://twistedmatrix.com/trac/ticket/5374)
         (still unresolved at the moment of writing).

   - Can be configured from YAML file, including python logging module configuration.

   - Pass IP address to verifiers along with hostname, if provided (see
     corresponding send feature in client for rationale).

   - Batch same-target requests arriving at the same time (lot of static content
     from subdomain, for instance), returning same response to all of them,
     instead of running a separate check (and e.g. connection) for each one of
     them.

   - "bind" option for perspective verifier to use for special routing -
     e.g. through some tunnel or tor/i2p network.

   - TODO: Add option to serve bundle for browsers at some URL.

   - TODO: Statistics on queries.
