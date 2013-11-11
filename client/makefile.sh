#!/bin/sh
EXTENSION_NAME=Convergence
XPI_NAME=$EXTENSION_NAME.xpi
ZIP_NAME=$EXTENSION_NAME.zip

# Targets
	find . -name '~*' -exec rm {} \;
	find . -name '*.swp' -exec rm {} \;
	rm -f $XPI_NAME
	rm -f $ZIP_NAME

	zip -qr $ZIP_NAME ./chrome
	zip -qr $ZIP_NAME ./chrome.manifest
	zip -qr $ZIP_NAME ./components
	zip -qr $ZIP_NAME ./defaults
	zip -qr $ZIP_NAME ./style
	zip -qr $ZIP_NAME ./install.rdf
	zip -qr $ZIP_NAME ./update.rdf
	zip -qr $ZIP_NAME ./icon.png
	zip -qr $ZIP_NAME ./icon64.png
	mv $ZIP_NAME $XPI_NAME
