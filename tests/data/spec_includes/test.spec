Name:           test
Version:        0.1
Release:        1%{?dist}
Summary:        Test package

License:        MIT

Source0:        %{name}-%{version}.tar.xz
Source1:        patches.inc
Source2:        description.inc

%include %{SOURCE1}


%description
%include %{SOURCE2}


%prep
%autosetup -p1


%changelog
* Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 0.1-1
- first version
