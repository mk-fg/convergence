# Variables
EXTENSION_NAME=Convergence
XPI_NAME=$(EXTENSION_NAME).xpi
ZIP_NAME=$(EXTENSION_NAME).zip

# Targets
default: build

clean:
	find . -name '~*' -delete
	find . -name '*.swp' -delete
	rm -f $(XPI_NAME)
	rm -f $(ZIP_NAME)

build: clean
	zip -qr $(ZIP_NAME) ./chrome
	zip -qr $(ZIP_NAME) ./chrome.manifest
	zip -qr $(ZIP_NAME) ./components
	zip -qr $(ZIP_NAME) ./defaults
	zip -qr $(ZIP_NAME) ./style
	zip -qr $(ZIP_NAME) ./install.rdf
	zip -qr $(ZIP_NAME) ./icon.png
	zip -qr $(ZIP_NAME) ./icon64.png
	mv $(ZIP_NAME) $(XPI_NAME)
