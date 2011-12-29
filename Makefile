SHELL := /bin/bash

all:

install :
	cp plotcut.py /usr/local/bin/plotcut

uninstall :
	rm -f /usr/local/bin/plotcut
