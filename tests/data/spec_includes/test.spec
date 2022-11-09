Name:           test
Version:        0.1
Release:        1%{?dist}
Summary:        Test package

License:        MIT

Source0:        %{name}-%{version}.tar.xz
Source1:        patches.inc
Source2:        provides.inc
Source3:        description.inc

%include %{SOURCE1}

Provides:       test0-%{version} %(sed "s/$/-%{version}/" %{SOURCE2} | tr "\n" " ")


%description
%include %{SOURCE3}


%prep
%autosetup -p1


%changelog
* Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 0.1-1
- first version
