Convergence "Extra"
--------------------

-----

**Not maintained here since ~2014 and does not work with newer FIrefox versions.**

If you'd like to work on it, feel free to just fork the repo
(this is a fork of Moxie's Convergence project anyway).

-----

This is a fork of Moxie Marlinspike's Convergence tool: http://convergence.io/

Convergence is a Firefox browser addon replacing default Certificate Authority
TLS authentication model with custom validation model, which is implemented by
"notary" servers.

Queries to notary servers can be anonymized via simple (built-in) onion routing,
list of such notaries to trust can be changed at any time and validation logic
on notaries themselves is designed to be customizable to provide "trust agility"
property, which current CA system lacks.

Good high-level overview of the tool and approach can be found in Moxie's "SSL
And The Future Of Authenticity" talk at BlackHat USA 2011: http://www.youtube.com/watch?v=Z7Wl2FW2TcA

See also [wikipedia page](https://en.wikipedia.org/wiki/Convergence_%28SSL%29).

More details on creating and running a notary server can be found in README file
in `server` section. `client` directory contains browser extension.

More-or-less up-to-date version of the built addon is available for install via AMO:
https://addons.mozilla.org/en-us/firefox/addon/convergence-extra/


### Note on compatibility

As changes to both client (addon) and server (notary) in this fork are quite
extensive at this point, old notaries (pre-fork) might not work with client from
here.

Due to things like e.g. SNI usage in client it WILL see different certificate
than non-SNI-using (pre-fork) notary.

Some protocol changes like passing IP address client picked to notary while
shouldn't (I think) cause old notaries to return http-400, are not (and were
not) tested with them and may also cause whatever behavior.

In short - just set up your own notaries using code in this fork.

Also, I don't use "bounce notaries", as all notaries I use are private anyway
and there aren't any useable public ones (due to compatibility things outlined
above), so that feature might be broken.

I suggest disabling it with your own notaries, as it serves no purpose in that
case (nothing to anonymize with just one user), while opening notaries to be
used as public to-port-4242-only proxies.


### Changes from upstream

 - client

   - Should work with newer firefox versions.

     - Merged fix from upstream [PR #170](https://github.com/moxie0/Convergence/pull/170).

     - Fixed major issue with extension hanging forever polling on connection to
       notary after receiving http response (bbdc538).
       Upstream [PR #173](https://github.com/moxie0/Convergence/pull/173).

     - Minor issue with displaying cached fingerprint timestamps as NaN-NaN-NaN
       (816c74e).
       Upstream [PR #174](https://github.com/moxie0/Convergence/pull/174).

     - Fix for breakage due to private browsing changes in firefox-20 (ffb7c7b).

     - Work with nspr/sqlite/ssl libs folded into nss on Windows with FF>=22
       (see [#1](https://github.com/mk-fg/convergence/issues/1) for more
       details).

   - Updated extension metadata to avoid clashes with the original thing and/or
     other forks.

     This one should be named "Convergence Extra", have a bit different version
     schema and distinct UUIDs for components.
     Settings for both are shared and should be compatible.

     Should probably still be a bad idea to have more than one Convergence
     extension enabled.

   - Backends' "isNotaryUri" check seem to have typo bugs (c96d242), messing up
     results (silently with >1 notaries).

   - Bugfix in nsIWebBrowserPersist.saveURI call (b5dbb50), preventing adding
     notaries from URL (at least in newer ff).

   - Use SNI TLS extension for client connections. This is kinda major flaw in
     the original extension, as it's quite widespread yet original Convergence
     only saw "generic" certificate for IP both on client and server (see also
     corresponding notary fix).

   - Added "Exceptions" tab to options for hostname patterns that convergence
     should not touch.

     Useful for local networks and dynamic hostnames (e.g. "vm-X.mydomain.tld")
     that never validate with available notaries for some reason, where adding
     individual exceptions can be problematic.

     Default value is previously hardcoded list of exceptions - localhost and
     mozilla "aus3" addons-update host.

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

   - Certificates for invalid names now can be validated - CN or SubjectAltNames
     are irrelevant to the client (and always being overidden) - only
     fingerprint and notary responses matter.

   - Handle too long (for cert subject line) hostnames by generating wildcard
     certificates (776728d).

   - More organized, prefixed and disableable (per-source, if necessary)
     logging. Can be enabled by setting "convergence.logging.enabled" to "true"
     in about:config or by changing "print_all: null" to "true" in Logger.js.

   - TODO: Cache fingerprnts for (hostname, port, ip) tuples, not just
     (hostname, port), because of cdn's and round-robin-dns mirrors -
     server-side as well, though there can be several signatures for one
     hostname there.

   - TODO: Certificates for IPs don't seem to be checked via notaries at all, so
     don't have "verificationDetails" comment and never validate with
     convergence.

   - TODO: "Allowed as bounce notary" checkbox in notaries' list to block local
     notaries from acting as such, for instance.

   - TODO: Make hardcoded check timeouts configurable.

       So that plugin won't hang on bogus notaries any longer than necessary
       with a specific connection latency in mind.

   - TODO: Make caching timeouts configurable.

       Caching for longer period might be desirable, especially for exceptions,
       which ideally would have their own timeout, which can maybe also be
       configurable when creating each exception, to be less annoying in some
       cases.

   - TODO: CLI tool to work with ff xml config - decode, maybe alter it, and to
     run queries for random sites via notaries defined there.

     Can also be implemented as
     [XPCOM commandline component](https://developer.mozilla.org/en-US/docs/Chrome/Command_Line),
     but that might be a bad idea due to unnecessary dep on firefox/xulrunner.

   - TODO: Replace js-ctypes with XPCOM where possible.

     These interfaces seem to be way more safe, stable and maintained.

     Also might need to check on security hooks there and if there's simplier
     way to override ff cert checks instead of full-blown content proxy.

   - TODO: At least some failures in the extension can be made more informative
     - i.e. ctypes load fail can force-disable addon and issue a dialog box
     telling user why, not just result in broken interfaces.

   - TODO: Merge tack branch if/when there will be something real to test it on.

   - TODO: Add bootstrap.js to load extension after installation without
     requiring browser restart.

   - TODO: Use
     [Log.jsm](https://developer.mozilla.org/en-US/docs/Mozilla/JavaScript_code_modules/Log.jsm)
     for logging, if available.

   - TODO: Store all the xml and sqlite stuff in special ["extension-store"
     place](https://bugzilla.mozilla.org/show_bug.cgi?id=915838).

   - TODO: Update for compatibility with ff-32 and beyond that (especially e10s
     "pid for tab" thing).

   - TODO: Migrate to JPM addon SDK, node deps instead of custom modules.

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

   - TODO: With perspectives + ca_check, if newer Twisted is detected, use its
     new service_identity verifier, check if new cryptography-based (py module)
     pyopenssl has less hacky way to use SNI.

   - TODO: Add option to serve bundle for browsers at some URL.

   - TODO: Statistics on queries.

 - packaging

   - TODO: Build script for windows (bat or cmd).

   - TODO: Update this (and maybe add one to /client) doc with simple debug
     steps - i.e. how to enable logging (about:config), were to expect it
     (jsconsole with +1 thing enabled, otherwise terminal or "-console" opt).
