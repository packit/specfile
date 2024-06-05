%global majorver 0
%global minorver 1
%global patchver 2
%global mainver %{majorver}.%{minorver}.%{patchver}

%global prever rc2

%global commit 7e1bb4465bf84a256411a8ebb3b46130939c8e88
%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global gitdate 20230830
%global gitversion %{gitdate}git%{shortcommit}

%if !0%{?use_snapshot}
%global package_version %{mainver}%{?prever:~%{prever}}
%else
%global package_version %{mainver}%{?gitversion:^%{gitversion}}
%endif

%global release 1%{?dist}


Name:           test
Version:        %{package_version}
Release:        %{release}
Summary:        Test package

License:        MIT

Source0:        https://example.com/archive/%{name}/v%{version}/%{name}-v%{version}.tar.xz
Source1:        tests-%{majorver}%{minorver}.tar.xz
Patch0:         patch0.patch
Patch1:         patch1.patch
Patch2:         patch2.patch


%description
Test package


%prep
%setup -q -n %{name}-%{version}
%setup -c -T -D -b 1
%patch -P0 -p1
%patch -P1 -p1
%patch -P2 -p1


%changelog
* Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 0.1.2~rc2-1
- first version
