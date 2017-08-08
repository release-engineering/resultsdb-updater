# This will produce and image to be used in OpenShift
# Build should be triggered from the repo root like:
# docker build -f openshift/Dockerfile --tag 172.30.1.1:5000/myproject/resultsdb-updater:latest --build-arg resultsdb_updater_rpm=resultsdb-updater-2.4.0-1.el7eng.noarch.rpm .
FROM centos:latest

ARG resultsdb_updater_rpm
COPY $resultsdb_updater_rpm /tmp

RUN yum install -y epel-release && \
    yum update -y && \
    yum install -y --setopt=tsflags=nodocs \
        /tmp/$(basename $resultsdb_updater_rpm) && \
    yum -y clean all && \
    rm -f /tmp/$(basename $resultsdb_updater_rpm)

RUN ln -s /etc/resultsdb-updater/resultsdb-updater.py /etc/fedmsg.d/resultsdb-updater.py

ENTRYPOINT fedmsg-hub
