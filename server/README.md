Convergence notary
--------------------

This is a "server" part of Convergence, responsible for providing client with an
SSL/TLS certificate signature for requested domain.


Installation
--------------------

 - Install the dependencies (example for debian/ubuntu):

```bash
% sudo apt-get install python python-twisted-web \
  python-twisted-names python-m2crypto python-openssl
```

 - Get the notary source:

```bash
% git clone https://github.com/mk-fg/convergence
```

 - Run the install script:

```bash
% cd convergence/server
% sudo python setup.py install
```

Alternatively, "./convergence-cli" can be used right from the checkout tree
without system-wide installation (as per last step).

### Requirements

 - [Twisted](https://pypi.python.org/pypi/Twisted)
 - [pyOpenSSL](https://pypi.python.org/pypi/pyOpenSSL)
 - [M2Crypto](https://pypi.python.org/pypi/M2Crypto)


Configuration
--------------------

 - Generate a key pair: `convergence gencert`

 - Create database: `sudo convergence createdb`

 - Start the server:

```bash
% sudo convergence notary \
  -c path/to/certificate.pem -k path/to/key.key
```


Publish
--------------------

 - Generate a notary bundle: `convergence-bundle`
 - Publish the resulting file on your website, with a ".notary" extension.
 - You're done! Anyone can use your notary by clicking on the link to your ".notary" file.


Extending
--------------------

Clients send host+port and TLS certificate fingerprint to notaries, which in
turn employ a "Verifier" backend class to get the fingerprint that should
actually be there.

For "perspective" backend this involves connecting to the same host+port and
getting/returning fingerprint of the certificate that is returned there.
"dns" backend sends TXT query with host+port to some DNS host to get that
fingerpriint.

Additional backends can be installed as
[setuptools/distribute entry points](http://packages.python.org/distribute/setuptools.html#dynamic-discovery-of-services-and-plugins)
(name: convergence.verifier) and will be available for selection for running a
notary via --backend option under the entry point name.

Entry point modules must include "verifier" attribute with backend
implementation constructor (e.g. class) assigned to it.

Backend implementation can (and probably should) extend
`convergence.verifier.Verifier` class, which implements one-argument class init
method (will be passed from --backend-options string) and `backend.verify(host,
port, fingerprint)` method, returning `(responseCode, fingerprintToCache)` tuple
via deferred callback.

See `convergence.verifier.Verifier` class for more details.


Included verifier backends
--------------------

Full list with descriptions can be acquired using "notary --backend help" on the
command line.

Here's a possibly-obsolete list it provides (as of 2013-04-27):

	- dns

	  Description:
	    Check certificate fingerprint via a DNS-based certificate catalog.

	  Options:
	    Hostname of the DNS server to query (required).

	- perspective

	  Description:
	    Check if remote presents the same certificate to the notary as it did to
	    client, optionally also performing verification against OpenSSL CA list
	    (on the notary host).

	  Options:
	    Optional list of flags, separated by any non-word characters, optionally
	    prefixed by "-" to disable that flag instead of enabling. Default flags:
	    (none); supported flags: verify_ca.

	- test_negative

	  Description:
	    Verifier that always returns negative result. For testing purposes only.

	- test_positive

	  Description:
	    Verifier that always returns positive result and the same fingerprint as
	    was passed to it. For testing purposes only.
