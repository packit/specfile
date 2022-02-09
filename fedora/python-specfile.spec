%{?!python3_pkgversion:%global python3_pkgversion 3}

%global srcname specfile

%global desc %{expand:
Python library for parsing and manipulating RPM spec files.
Main focus is on modifying existing spec files, any change should result
in a minimal diff.}


Name:           python-%{srcname}
Version:        0.1.0
Release:        1%{?dist}

Summary:        A library for parsing and manipulating RPM spec files
License:        MIT
URL:            https://github.com/packit/specfile

Source0:        %{pypi_source}

BuildArch:      noarch

BuildRequires:  python%{python3_pkgversion}-devel


%description
%{desc}


%package -n python%{python3_pkgversion}-%{srcname}
Summary:        %{summary}

%{?python_provide:%python_provide python3-%{srcname}}


%description -n python%{python3_pkgversion}-%{srcname}
%{desc}


%generate_buildrequires
%pyproject_buildrequires -x testing


%prep
%autosetup -p1 -n %{srcname}-%{version}


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files %{srcname}


%check
%pytest


%files -n python%{python3_pkgversion}-%{srcname} -f %{pyproject_files}
%license LICENSE
%doc README.md


%changelog
* Tue Feb 08 2022 Nikola Forró <nforro@redhat.com> - 0.1.0-1
- Initial package
