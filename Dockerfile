FROM fedora:28
LABEL \
    name="ResultsDB-Updater application" \
    vendor="ResultsDB-Updater developers" \
    license="LGPL-2.1" \
    description="ResultsDB-Updater is a micro-service that listens for test \
results on the CI message bus and updates ResultsDB in a standard format." \
    usage="https://github.com/release-engineering/resultsdb-updater" \
    build-date=""

RUN dnf install -y \
        fedmsg \
        python-requests \
        python2-semantic_version \
    && dnf clean -y all

COPY ["setup.py", "requirements.txt", "/src/resultsdb-updater/"]
COPY ["resultsdbupdater/", "/src/resultsdb-updater/resultsdbupdater/"]

# Dependencies should be resolved in the dnf install step above,
# in order to avoid pulling something unsafe from pypi.
RUN pip install --no-deps /src/resultsdb-updater/

VOLUME ["/etc/resultsdb", "/etc/fedmsg.d"]
ENTRYPOINT fedmsg-hub
