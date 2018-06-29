# ResultsDB-Updater

[![Build Status](https://travis-ci.org/release-engineering/resultsdb-updater.svg?branch=master)](https://travis-ci.org/release-engineering/resultsdb-updater)

ResultsDB-Updater is a micro-service that listens for test results on the CI
message bus and updates ResultsDB in a standard format.

### Installation

Install the Python dependencies:

```
pip install -r requirements.txt
```

Edit the configuration file at:

```
fedmsg.d/config.py
```

Generate the entry points for fedmsg-hub:

```
python setup.py egg_info
```

Run the service:

```
fedmsg-hub
```

### Running the service in a container

Building the container image requires the ResultsDB-Updater rpm to be provided
as a build argument:

```bash
$ docker build -f openshift/Dockerfile \
               --tag <IMAGE_TAG> \
               --build-arg resultsdb_updater_rpm=<RESULTSDB_UPDATER_RPM> ./
```

`IMAGE_TAG` is the tag to be applied on the image built.

`RESULTSDB_UPDATER_RPM` is either the URL of the ResultsDB-Updater rpm, or the
relative path of that rpm *within* the build context.

There are two volumes expected to be mounted when ResultsDB-Updater containers
are started:

1. A volume mounted at `/etc/fedmsg.d` with any `*.py` file holding fedmsg and
   ResultsDB-Updater configuration. For an example see `fedmsg.d/config.py` or
   the documentation on [how to configure
   fedmsg](http://www.fedmsg.com/en/latest/configuration/#).

2. A volume mounted at `/etc/resultsdb` holding the client certificate and
   private key files, to be used with STOMP when authenticating with the
   message broker (if configured).

`openshift/resultsdb-updater-test-template.yaml` defines a
[template](https://docs.openshift.org/latest/dev_guide/templates.html) to help
deploying ResultsDB-Updater to OpenShift and connecting it to a ResultsDB
service, and a message broker (using STOMP).

For the full list of template parameters see:

```bash
$ oc process -f openshift/resultsdb-updater-test-template.yaml --parameters
```

For creating the environment run:

```bash
$ oc process -f openshift/resultsdb-updater-test-template.yaml \
             -p TEST_ID=<TEST_ID> \
             -p RESULTSDB_UPDATER_IMAGE=<RESULTSDB_UPDATER_IMAGE> \
             -p RESULTSDB_API_URL=<RESULTSDB_API_URL> \
             -p STOMP_URI=<STOMP_URI> | oc apply -f -
```

Use the `-p` option of `oc process` to override default values of the template
parameters.
