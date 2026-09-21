.PHONY: test validate build preview collect synthesize

test:
	python3 -m unittest discover -s tests -v

validate:
	python3 -m pipeline.cli validate-public

build:
	python3 scripts/build_site.py

preview: build
	python3 -m http.server 8000 --directory dist

collect:
	python3 -m pipeline.cli collect

synthesize:
	python3 -m pipeline.cli synthesize
