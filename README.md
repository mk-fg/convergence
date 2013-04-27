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

     - Fixed major issue with extension hanging forever polling on connection to
       notary after receiving http response (bbdc538).

         Upstream [PR #173](https://github.com/moxie0/Convergence/pull/173).

     - Minor issue with displaying cached fingerprint timestamps as NaN-NaN-NaN
       (816c74e).

         Upstream [PR #174](https://github.com/moxie0/Convergence/pull/174).

   - Bumped plugin version, max ff version is 50.* and automatic upstream
     updates are disabled.

   - TODO: Checkbox for option to always query enabled localhost notaries first.

   - TODO: Make hardcoded check timeouts configurable.

       So that plugin won't hang on bogus notaries any longer than necessary
       with a specific connection latency in mind.

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

   - TODO: [CrossBear](https://pki.net.in.tum.de/) verifier via dns-txt they
     provide.

   - TODO: Statistics on queries.

   - TODO: Look into integration with OONI, EFF Observatory, Sovereign Keys and
     similar projects.
