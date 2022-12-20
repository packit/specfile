# Contributing Guidelines

Please follow common guidelines for our projects [here](https://github.com/packit/contributing).

## Running tests

The easiest way of running tests locally is inside containers:

```bash
# Needs to be re-run only when dependencies change
make build-test-image

# Run the whole test suite
make check-in-container

# Run only unit tests
TEST_TARGET=./tests/unit make check-in-container
```

To reproduce a testing environment similar to the one used in Fedora CI,
[tmt](https://github.com/teemtee/tmt) can be used (this will run tests in a
virtual machine, for other options, refer to the
[tmt documentation](https://tmt.readthedocs.io/en/stable/):

```bash
tmt run plan -n full
```

Since Packit directly relies on specfile, we also have a reverse-dependency
test that runs Packit's tests with the currently checked out specfile.
In Github pull requests, this is done automatically. To reproduce this
behavior locally, you first need to build an RPM package from the current
checkout, e.g. by using `packit build locally`:

```bash
# Build using the current sources using rpmbuild, results are placed inside noarch/
packit build locally

# The plan installs RPMs from the noarch/ directory. The VM image that you use
# must match the built RPM package Fedora version so that the package can be installed.
tmt -c how=integration run -avvv plan -n packit-integration provision -h virtual -i fedora-36
```
