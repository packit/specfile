%dnl %global commit 202ab7e698a34154129bb9ded589db58996eeb53
%global shortcommit %(c=%{commit}; echo ${c:0:7})

%global upstream_version 0.1.2

Name:           test
%if 0%{?commit:1}
Version:        %{upstream_version}^git%{shortcommit}
%else
Version:        %{upstream_version}
%endif
Release:        1%{?dist}
Summary:        Test package

License:        MIT

%if 0%{?commit:1}
Source0:        https://example.com/archive/%{name}/%{commit}/%{name}-%{shortcommit}.tar.xz
%else
Source0:        https://example.com/archive/%{name}/v%{version}/%{name}-%{version}.tar.xz
%endif
Patch0:         patch0.patch
Patch1:         patch1.patch
Patch2:         patch2.patch


%description
Test package


%prep
%if 0%{?commit:1}
%autosetup -p1 -n %{name}-%{shortcommit}
%else
%autosetup -p1 -n %{name}-%{version}
%endif


%changelog
* Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 0.1.2-1
- first version
