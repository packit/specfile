%global majorver 0
%global minorver 1
%global patchver 2
%global prever rc2
%global package_version %{majorver}.%{minorver}.%{patchver}
%global release 1%{?dist}


Name:           test
Version:        %{package_version}%{?prever:~%{prever}}
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
%patch0 -p1
%patch1 -p1
%patch2 -p1


%changelog
* Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 0.1.2~rc2-1
- first version
