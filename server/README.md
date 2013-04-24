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
