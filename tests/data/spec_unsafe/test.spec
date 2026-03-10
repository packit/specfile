%global upstream_version 2.18.4
%global upstream_majorver %(v=%{upstream_version}; echo ${v%%%%.*})
%global upstream_majorminorver %(echo %{upstream_version} | cut -d. -f1-2)
%global upstream_patchver %(awk -F. '{print $3}' <<< %{upstream_version})
%global patchver %(echo $((%{upstream_patchver}+2)))
%global datestring %(date +%Y%m%d)


Name:           test
Version:        %{upstream_majorver}.%{?upstream_minorver}%{!?upstream_minorver:0}.%{patchver}^%{datestring}
Release:        1%{?dist}
Summary:        Test package

License:        MIT


%description
Test package


%changelog
* Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 2.0.6^20180607-1
- first version
