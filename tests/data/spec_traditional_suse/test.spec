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
%setup -q
%patch -P0 -p1
%patch -P1 -p1
%patch -P2 -p1


%changelog
