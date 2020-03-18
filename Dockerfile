FROM fedora:31
LABEL \
    name="ResultsDB-Updater application" \
    vendor="ResultsDB-Updater developers" \
    license="LGPL-2.1" \
    description="ResultsDB-Updater is a micro-service that listens for test \
results on the CI message bus and updates ResultsDB in a standard format." \
    usage="https://github.com/release-engineering/resultsdb-updater" \
    build-date=""

RUN dnf install -y --nodocs --setopt=install_weak_deps=false \
        git-core \
        fedmsg \
        python3-pip \
        python3-requests \
        python3-semantic_version \
    && dnf clean -y all

COPY . /tmp/code

# Dependencies should be resolved in the dnf install step above,
# in order to avoid pulling something unsafe from pypi.
RUN pushd /tmp/code \
    && pip install --no-deps . \
    && sed --regexp-extended -i -e "/^    version=/c\\    version='$(./version.sh)'," setup.py \
    && popd \
    && dnf remove -y git-core \
    && rm -rf /tmp/*

USER 1001
VOLUME ["/etc/resultsdb", "/etc/fedmsg.d"]
CMD ["/usr/bin/fedmsg-hub"]
