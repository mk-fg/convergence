Convergence
--------------------

This is a fork of Moxie Marlinspike's Convergence tool: http://convergence.io/

Good high-level overview of the tool can be found in Moxie's "SSL And The Future
Of Authenticity" talk at BlackHat USA 2011: http://www.youtube.com/watch?v=Z7Wl2FW2TcA

### This fork

Short-term goals of the fork is to integrate existing non-merged third-party
fixes/enhancements and extend client compatibility to newer firefox versions.

More long-term goal is to extend backends for integration with
[CrossBear](https://pki.net.in.tum.de/), OONI and related projects.


Installation
--------------------

 - Install the dependencies (example for debian/ubuntu):

	% sudo apt-get install python python-twisted-web \
	  python-twisted-names python-m2crypto python-openssl

 - Get the notary source:

	% git clone https://github.com/mk-fg/convergence

 - Run the install script:

	% cd convergence/server
	% sudo python setup.py install

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

	% sudo convergence notary \
	  -c path/to/certificate.pem -k path/to/key.key


Publish
--------------------

 - Generate a notary bundle: `convergence-bundle`
 - Publish the resulting file on your website, with a ".notary" extension.
 - You're done! Anyone can use your notary by clicking on the link to your ".notary" file.
