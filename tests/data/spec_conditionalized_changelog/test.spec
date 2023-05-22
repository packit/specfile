Name:           test
Version:        0.1
Release:        %autorelease
Summary:        Test package

License:        MIT


%description
Test package


%if 0%{?fedora}
%changelog
%autochangelog
%else
%changelog
* Mon May 22 2023 Nikola Forró <nforro@redhat.com>
- Initial package
%endif
