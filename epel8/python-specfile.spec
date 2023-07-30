%global desc %{expand:
Python library for parsing and manipulating RPM spec files.
Main focus is on modifying existing spec files, any change should result
in a minimal diff.}


Name:           python-specfile
Version:        0.20.1
Release:        1%{?dist}

Summary:        A library for parsing and manipulating RPM spec files
License:        MIT
URL:            https://github.com/packit/specfile

Source0:        %{pypi_source specfile}

BuildArch:      noarch

BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  %{py3_dist setuptools setuptools-scm setuptools-scm-git-archive}
BuildRequires:  %{py3_dist importlib-metadata dataclasses rpm typing-extensions}
BuildRequires:  %{py3_dist flexmock pytest}
BuildRequires:  git-core


%description
%{desc}


%package -n python%{python3_pkgversion}-specfile
Summary:        %{summary}


%description -n python%{python3_pkgversion}-specfile
%{desc}


%prep
%autosetup -p1 -n specfile-%{version}
# Use packaged RPM python bindings downstream
sed -i 's/rpm-py-installer/rpm/' setup.cfg
# Remove bundled egg-info
rm -rf specfile.egg-info


%build
%py3_build


%install
%py3_install


%check
%pytest


%files -n python%{python3_pkgversion}-specfile
%license LICENSE
%doc README.md
%{python3_sitelib}/specfile
%{python3_sitelib}/specfile-%{version}-py%{python3_version}.egg-info


%changelog
* Sun Jul 30 2023 Packit Team <hello@packit.dev> - 0.20.1-1
- New upstream release 0.20.1

* Fri Oct 07 2022 Packit Team <hello@packit.dev> - 0.7.0-1
- New upstream release 0.7.0

* Thu Aug 25 2022 Nikola Forró <nforro@redhat.com> - 0.6.0-1
- New upstream release 0.6.0

* Tue Aug 09 2022 Nikola Forró <nforro@redhat.com> - 0.5.1-1
- New upstream release 0.5.1

* Thu Jul 21 2022 Nikola Forró <nforro@redhat.com> - 0.5.0-1
- New upstream release 0.5.0

* Thu Jun 16 2022 Nikola Forró <nforro@redhat.com> - 0.4.0-1
- New upstream release 0.4.0

* Tue May 10 2022 Nikola Forró <nforro@redhat.com> - 0.3.0-1
- New upstream release 0.3.0

* Wed Mar 30 2022 Nikola Forró <nforro@redhat.com> - 0.2.0-1
- New upstream release 0.2.0

* Mon Feb 21 2022 Nikola Forró <nforro@redhat.com> - 0.1.1-1
- New upstream release 0.1.1

* Tue Feb 08 2022 Nikola Forró <nforro@redhat.com> - 0.1.0-1
- Initial package
