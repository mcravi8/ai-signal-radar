.PHONY: test validate validate-events build preview collect collect-events synthesize

test:
	python3 -m unittest discover -s tests -v

validate:
	python3 -m pipeline.cli validate-public

validate-events:
	python3 -m pipeline.cli validate-events

build:
	python3 scripts/build_site.py

preview: build
	python3 -m http.server 8000 --directory dist

collect:
	python3 -m pipeline.cli collect

collect-events:
	python3 -m pipeline.cli collect-events

synthesize:
	python3 -m pipeline.cli synthesize
