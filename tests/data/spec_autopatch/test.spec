Name:           test
Version:        0.1
Release:        1%{?dist}
Summary:        Test package

License:        MIT

Source:         %{name}-%{version}.tar.xz
Patch0:         patch0.patch
Patch1:         patch1.patch
Patch2:         patch2.patch
Patch3:         patch3.patch
Patch4:         patch4.patch
Patch5:         patch5.patch
Patch6:         patch6.patch


%description
Test package


%prep
%autosetup -N
# apply the first 3 patches
%autopatch -p1 -M 2
# apply patch 3
%autopatch -p1 3
# apply patches 4-6
%autopatch -p1 -m 4


%changelog
* Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 0.1-1
- first version
