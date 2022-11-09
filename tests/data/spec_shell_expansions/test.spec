%global upstream_version 1035.42
%global package_version %(printf "%'.4f" %{upstream_version})

%global numeric_locale %(locale | grep LC_NUMERIC)


Name:           test
Version:        %{package_version}
Release:        1%{?dist}
Summary:        Test package

License:        MIT


%description
Test package


%changelog
* Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 0.1-1
- first version
