Name:           test
Version:        0.1
Release:        1%{?dist}
Summary:        Test package

License:        MIT

Source:         %{name}-%{version}.tar.xz
Patch0:         patch0.patch
Patch1:         patch1.patch
Patch2:         patch2.patch


%description
Test package


%prep
%autosetup -p1


%changelog
* Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 0.1-1
- first version
