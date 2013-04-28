Convergence notary
--------------------

This is a "server" part of Convergence, responsible for providing client with an
SSL/TLS certificate signature for requested domain.



Setup
--------------------


### Installation

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

##### Requirements

 - [Twisted](https://pypi.python.org/pypi/Twisted)
 - [pyOpenSSL](https://pypi.python.org/pypi/pyOpenSSL)
 - [M2Crypto](https://pypi.python.org/pypi/M2Crypto)
 - (optional) [PyYAML](http://pyyaml.org/) - only if -c/--config option is used.


### Configuration

 - Generate a key pair: `convergence gencert`

 - Create database: `sudo convergence createdb`

 - Start the server:

```bash
% sudo convergence notary \
  -c path/to/certificate.pem -k path/to/key.key
```


### Publish

 - Generate a notary bundle: `convergence-bundle`
 - Publish the resulting file on your website, with a ".notary" extension.
 - You're done! Anyone can use your notary by clicking on the link to your ".notary" file.



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



Configuration files
--------------------

Allow to specify all the parameters that are allowed on the command-line and
extended [logging configuration](http://docs.python.org/library/logging.config.html).
Multiple config files (e.g. `-c file1 -c file2`) are stacked (with
[shipped one](https://github.com/mk-fg/convergence/blob/master/server/convergence/core.yaml)
being the baseline) - values set in latter ones overriding the ones from former.

For example:

	notary:
	  proxy_port: 8080
	  tls_port: 8443
	  interface: localhost
	  cert: notary.crt
	  cert_key: notary.key
	  db: notary.db
	  backend: test_positive

Running `convergence -c example.yaml notary` will then start notary with all the
parameters specified above (in the "example.yaml" file).

As noted, config also can contain extended logging setup
(see also [baseline config](https://github.com/mk-fg/convergence/blob/master/server/convergence/core.yaml)),
for example:

```yaml
logging:
  handlers:
    # To be able to access verbose log on any problems
    debug_logfile:
      class: logging.handlers.RotatingFileHandler
      filename: /var/log/convergence/debug.log
      formatter: basic
      encoding: utf-8
      maxBytes: 5_242_880 # 5 MiB
      backupCount: 2
      level: DEBUG
  loggers:
    # Supress verbose output from a specific logger
    convergence.verifier.perspective:
      handlers: [console]
      level: WARNING
  root:
    level: DEBUG
    handlers: [console, debug_logfile]
```

Requires [PyYAML](http://pyyaml.org/) module to be installed (e.g. `pip install
pyyaml` - it's optional, so not pulled-in by setup.py).



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
