.PHONY: build patch test check webflasher

build:
	./build_thai.sh

patch:
	./build_thai.sh --update-patches

test:
	python3 -m unittest discover -s tests -v

check: build test

webflasher:
	@test -e third_party/evenRealities-webflasher/.git || \
	  git submodule update --init third_party/evenRealities-webflasher
	@if [ -f third_party/evenRealities-webflasher/src/lib/localTempleFlashTargets.js ]; then \
	  echo "webflasher patch already applied"; \
	else \
	  git -C third_party/evenRealities-webflasher checkout --detach c437fdf22b71c7e3c0b9de2b4669d8a4847ce919 && \
	  git -C third_party/evenRealities-webflasher apply ../../patches/webflasher_case_usb_thai.patch && \
	  echo "applied patches/webflasher_case_usb_thai.patch"; \
	fi
	python3 tools/check_webflasher_pin.py

