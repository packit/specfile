Name:           test
Version:        0.1
Release:        1%{?dist}
Summary:        Test package

License:        MIT

Source:         %{name}-%{version}.tar.xz

# this is a downstream-only patch
Patch0:         patch0.patch

# this is patch1
Patch1:         patch1.patch
# this is patch2
Patch2:         patch2.patch

# these two patches are related to each other
Patch3:         patch3.patch
Patch4:         patch4.patch

# this is patch5
# it's a temporary workaround for some issue
Patch5:         patch5.patch
# this is patch6
Patch6:         patch6.patch


%description
Test package


%prep
%autosetup -p1


%changelog
* Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 0.1-1
- first version
