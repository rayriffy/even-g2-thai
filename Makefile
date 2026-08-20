.PHONY: build patch test check

build:
	./build_thai.sh

patch:
	./build_thai.sh --update-patches

test:
	python3 -m unittest discover -s tests -v

check: build test

