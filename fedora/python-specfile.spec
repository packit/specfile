%bcond_without tests


%global desc %{expand:
Python library for parsing and manipulating RPM spec files.
Main focus is on modifying existing spec files, any change should result
in a minimal diff.}


%global base_version 0.26.0
#%global prerelease   rc1

%global package_version %{base_version}%{?prerelease:~%{prerelease}}
%global pypi_version    %{base_version}%{?prerelease}


Name:           python-specfile
Version:        %{package_version}
Release:        1%{?dist}

Summary:        A library for parsing and manipulating RPM spec files
License:        MIT
URL:            https://github.com/packit/specfile

Source0:        %{pypi_source specfile %{pypi_version}}

BuildArch:      noarch

BuildRequires:  python3-devel
%if %{with tests}
# tests/unit/test_guess_packager.py
BuildRequires:  git-core
%endif


%description
%{desc}


%package -n python%{python3_pkgversion}-specfile
Summary:        %{summary}


%description -n python%{python3_pkgversion}-specfile
%{desc}


%prep
%autosetup -p1 -n specfile-%{pypi_version}

# since we are building from PyPI source, we don't need git-archive
# support in setuptools_scm
sed -i 's/setuptools_scm\[toml\]>=7/setuptools_scm[toml]/' pyproject.toml


%generate_buildrequires
%pyproject_buildrequires %{?with_tests: -x testing}


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files specfile


%if %{with tests}
%check
%pytest --verbose tests/unit tests/integration
%endif


%files -n python%{python3_pkgversion}-specfile -f %{pyproject_files}
%doc README.md


%changelog
* Fri Dec 08 2023 Packit Team <hello@packit.dev> - 0.26.0-1
- New upstream release 0.26.0

* Mon Nov 20 2023 Packit Team <hello@packit.dev> - 0.25.1~rc1-1
- New upstream release 0.25.1rc1

* Mon Nov 20 2023 Packit Team <hello@packit.dev> - 0.25.0-1
- New upstream release 0.25.0

* Tue Nov 14 2023 Nikola Forró <nforro@redhat.com> - 0.24.1~rc2-1
- New upstream release 0.24.1rc2

* Tue Nov 14 2023 Nikola Forró <nforro@redhat.com> - 0.24.1~rc1-1
- New upstream release 0.24.1-rc1

* Mon Nov 06 2023 Packit Team <hello@packit.dev> - 0.24.0-1
- New upstream release 0.24.0

* Sun Oct 29 2023 Packit Team <hello@packit.dev> - 0.23.0-1
- New upstream release 0.23.0

* Fri Oct 06 2023 Packit Team <hello@packit.dev> - 0.22.1-1
- New upstream release 0.22.1

* Fri Sep 01 2023 Packit Team <hello@packit.dev> - 0.22.0-1
- New upstream release 0.22.0

* Fri Aug 11 2023 Packit Team <hello@packit.dev> - 0.21.0-1
- New upstream release 0.21.0

* Fri Aug 04 2023 Tomas Tomecek <ttomecek@redhat.com> - 0.20.2-2
- Confirm License is SPDX compatible.

* Mon Jul 31 2023 Packit Team <hello@packit.dev> - 0.20.2-1
- New upstream release 0.20.2

* Sun Jul 30 2023 Packit Team <hello@packit.dev> - 0.20.1-1
- New upstream release 0.20.1

* Thu Jul 13 2023 Packit Team <hello@packit.dev> - 0.20.0-1
- New upstream release 0.20.0

* Thu Jun 22 2023 Packit Team <hello@packit.dev> - 0.19.0-1
- New upstream release 0.19.0

* Fri May 26 2023 Packit Team <hello@packit.dev> - 0.18.0-1
- New upstream release 0.18.0

* Thu May 11 2023 Packit Team <hello@packit.dev> - 0.17.0-1
- New upstream release 0.17.0

* Thu Apr 20 2023 Packit Team <hello@packit.dev> - 0.16.0-1
- New upstream release 0.16.0

* Fri Mar 10 2023 Packit Team <hello@packit.dev> - 0.15.0-1
- New upstream release 0.15.0

* Thu Feb 23 2023 Packit Team <hello@packit.dev> - 0.14.0-1
- New upstream release 0.14.0

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
