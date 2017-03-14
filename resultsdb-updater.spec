%{!?_licensedir: %global license %%doc}

%if 0%{?rhel} && 0%{?rhel} <= 6
%{!?__python2:        %global __python2 /usr/bin/python2}
%{!?python2_sitelib:  %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python2_sitearch: %global python2_sitearch %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif

Name:               resultsdb-updater
Version:            2.1.1
Release:            1%{?dist}
Summary:            Translates test results on the message bus to ResultsDB

Group:              Development/Libraries
License:            LGPLv2+
URL:                https://github.com/release-engineering/%{name}
Source0:            https://github.com/release-engineering/%{name}/archive/v%{version}.tar.gz
BuildArch:          noarch

BuildRequires:      python2-devel
BuildRequires:      python-setuptools

Requires:           fedmsg
Requires:           m2crypto
Requires:           python-moksha-hub
Requires:           python-fedmsg-commands
Requires:           python-fedmsg-consumers
Requires:           fedmsg-hub
Requires:           python-m2ext
Requires:           python-psutil
Requires:           python-qpid
Requires:           python-stomper
Requires:           python-requests

%description
A micro-service that listens for test results on the message bus and updates
ResultsDB

%prep
%setup -q -n %{name}-%{version}

# Remove bundled egg-info in case it exists
rm -rf %{name}.egg-info

%build
%{__python2} setup.py build

%install
%{__python2} setup.py install -O1 --skip-build --root=%{buildroot}

# setuptools installs these, but we don't want them.
rm -rf %{buildroot}%{python2_sitelib}/tests/

%files
%doc README.md
%license LICENSE
%{python2_sitelib}/resultsdbupdater/
%{python2_sitelib}/resultsdb_updater-%{version}*

%changelog
* Tue Mar 14 2017 Matt Prahl <mprahl@redhat.com> - 2.1.1-1
- Update to v2.1.1

* Fri Mar 3 2017 Matt Prahl <mprahl@redhat.com> - 2.1.0-1
- Update to v2.1.0

* Wed Jan 18 2017 Matt Prahl <mprahl@redhat.com> - 2.0.0-1
- Update to v2.0.0

* Mon Jan 9 2017 Matt Prahl <mprahl@redhat.com> - 1.4.0-1
- Update to v1.4.0

* Fri Jan 6 2017 Matt Prahl <mprahl@redhat.com> - 1.3.0-1
- Update to v1.3.0

* Fri Dec 2 2016 Matt Prahl <mprahl@redhat.com> - 1.2.0-1
- Update to v1.2.0

* Thu Dec 1 2016 Matt Prahl <mprahl@redhat.com> - 1.1.0-1
- Update to v1.1.0

* Tue Nov 29 2016 Matt Prahl <mprahl@redhat.com> - 1.0.1-1
- Add fedmsg-hub as a runtime dependency.

* Tue Nov 22 2016 Matt Prahl <mprahl@redhat.com> - 1.0.0-1
- The dawn of time.
