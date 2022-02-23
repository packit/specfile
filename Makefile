TEST_IMAGE = specfile-tests
CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)

TEST_TARGET ?= ./tests/unit ./tests/integration

.PHONY: check install build-test-image check-in-container

check:
	PYTHONPATH=$(CURDIR) PYTHONDONTWRITEBYTECODE=1 python3 -m pytest --verbose --showlocals $(TEST_TARGET) --full-trace

install:
	pip3 install --user .

build-test-image:
	$(CONTAINER_ENGINE) build --rm --tag $(TEST_IMAGE) -f Containerfile.tests

check-in-container:
	$(CONTAINER_ENGINE) run --rm -ti -v $(CURDIR):/src:Z -w /src --env TEST_TARGET $(TEST_IMAGE) make check
