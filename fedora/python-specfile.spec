%if 0%{?rhel} == 9
# RHEL 9 is missing python-flexmock
%bcond_with tests
%else
%bcond_without tests
%endif


%global desc %{expand:
Python library for parsing and manipulating RPM spec files.
Main focus is on modifying existing spec files, any change should result
in a minimal diff.}


Name:           python-specfile
Version:        0.13.2
Release:        1%{?dist}

Summary:        A library for parsing and manipulating RPM spec files
License:        MIT
URL:            https://github.com/packit/specfile

Source0:        %{pypi_source specfile}

BuildArch:      noarch

BuildRequires:  python%{python3_pkgversion}-devel


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


%generate_buildrequires
%pyproject_buildrequires %{?with_tests: -x testing}


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files specfile


%if %{with tests}
%check
%pytest
%endif


%files -n python%{python3_pkgversion}-specfile -f %{pyproject_files}
%doc README.md


%changelog
* Mon Jan 30 2023 Packit Team <hello@packit.dev> - 0.13.2-1
- New upstream release 0.13.2

* Mon Jan 23 2023 Packit Team <hello@packit.dev> - 0.13.1-1
- New upstream release 0.13.1

* Fri Jan 20 2023 Packit Team <hello@packit.dev> - 0.13.0-1
- New upstream release 0.13.0

* Fri Jan 06 2023 Packit Team <hello@packit.dev> - 0.12.0-1
- New upstream release 0.12.0

* Wed Dec 14 2022 Packit Team <hello@packit.dev> - 0.11.1-1
- New upstream release 0.11.1

* Fri Dec 09 2022 Packit Team <hello@packit.dev> - 0.11.0-1
- New upstream release 0.11.0

* Sat Nov 26 2022 Packit Team <hello@packit.dev> - 0.10.0-1
- New upstream release 0.10.0

* Fri Nov 11 2022 Packit Team <hello@packit.dev> - 0.9.1-1
- New upstream release 0.9.1

* Tue Oct 25 2022 Packit Team <hello@packit.dev> - 0.9.0-1
- New upstream release 0.9.0

* Fri Oct 14 2022 Packit Team <hello@packit.dev> - 0.8.0-1
- New upstream release 0.8.0

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
