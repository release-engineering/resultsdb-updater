# This will produce and image to be used in OpenShift
# Build should be triggered from the repo root like:
# docker build -f openshift/Dockerfile \
#              --tag <IMAGE_TAG> \
#              --build-arg resultsdb_updater_rpm=<RESULTSDB_UPDATER_RPM> ./

FROM fedora:28
LABEL \
    name="ResultsDB-Updater application" \
    vendor="ResultsDB-Updater developers" \
    license="LGPL-2.1" \
    description="ResultsDB-Updater is a micro-service that listens for test \
results on the CI message bus and updates ResultsDB in a standard format." \
    usage="https://github.com/release-engineering/resultsdb-updater" \
    build-date=""

# The caller should build a resultsdb-updater RPM package used and then
# pass it in this arg.
# Accept both a URL or a local path relative to the build context.
ARG resultsdb_updater_rpm
ADD $resultsdb_updater_rpm /tmp

RUN dnf -y update && \
    dnf -y install --setopt=tsflags=nodocs \
        /tmp/$(basename $resultsdb_updater_rpm) && \
    dnf -y clean all && \
    rm -f /tmp/$(basename $resultsdb_updater_rpm)

VOLUME ["/etc/resultsdb", "/etc/fedmsg.d"]
ENTRYPOINT fedmsg-hub
