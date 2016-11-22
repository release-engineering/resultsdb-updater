# -*- mode: ruby -*-
# vi: set ft=ruby :

$script = <<SCRIPT
    dnf install -y \
        python \
        python-virtualenv \
        python-devel \
        libffi-devel \
        redhat-rpm-config \
        openssl-devel \
        gcc \
        swig
    virtualenv /opt/resultsdb-updater/env
    source /opt/resultsdb-updater/env/bin/activate
    pip install -r /opt/resultsdb-updater/src/requirements.txt
    pip install -r /opt/resultsdb-updater/src/test-requirements.txt
    cd /opt/resultsdb-updater/src
    python setup.py develop
SCRIPT

Vagrant.configure("2") do |config|
  config.vm.box = "boxcutter/fedora24"
  config.vm.synced_folder "./", "/opt/resultsdb-updater/src"
  config.vm.provision "shell", inline: $script
end
