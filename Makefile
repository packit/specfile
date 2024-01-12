TEST_IMAGE = specfile-tests
CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)
COLOR ?= yes
COV_REPORT ?= --cov=specfile --cov-report=term-missing

TEST_TARGET ?= ./tests/unit ./tests/integration

.PHONY: check install build-test-image check-in-container

check:
	PYTHONPATH=$(CURDIR) PYTHONDONTWRITEBYTECODE=1 python3 -m pytest --color=$(COLOR) --verbose --showlocals $(TEST_TARGET) $(COV_REPORT) --full-trace

install:
	pip3 install --user .

build-test-image:
	$(CONTAINER_ENGINE) build --rm --tag $(TEST_IMAGE) -f Containerfile.tests

check-in-container:
	$(CONTAINER_ENGINE) run --rm -ti \
		-v $(CURDIR):/src:Z -w /src \
		--env TEST_TARGET \
		--env COLOR \
		--env COV_REPORT \
		$(TEST_IMAGE) make check

generate-api-docs:
	PYTHONPATH=$(CURDIR):$(CURDIR)/docs/api pydoc-markdown --verbose docs/api/specfile.yml
