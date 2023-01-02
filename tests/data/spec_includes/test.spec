Name:           test
Version:        0.1
Release:        1%{?dist}
Summary:        Test package

License:        MIT

Source0:        %{name}-%{version}.tar.xz
Source1:        patches.inc
Source2:        provides.inc
Source3:        description1.inc
Source4:        description2.inc
Source5:        macros1.inc
Source6:        macros2.inc

%include %{SOURCE1}

Provides:       %(sed "s/$/-%{version}/" %{SOURCE2} | tr "\n" " ")


%description
%include %{SOURCE3}
%(cat %{S:4})


%include %{SOURCE5}
%{load:%{SOURCE6}}


%prep
%autosetup -p1
%if 0%{macro1} && 0%{macro2}
# noop
%endif


%changelog
* Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 0.1-1
- first version
