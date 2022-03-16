Name:           test
Version:        0.1
Release:        1%{?dist}
Summary:        Test package

License:        MIT

Source0:        test.tar.bz2
Source1:        test.zip
Source2:        test.tar.xz
Source3:        test.tar.zst
Source4:        test.tar.lz
Source5:        test.tar.lrz
Source6:        test.tar.gz
Source7:        test.7z
Source8:        test.txt


%description
Test package


%prep
%autosetup -c
%autosetup -c -T -D -b 1
%autosetup -c -T -D -b 2
%autosetup -c -T -D -b 3
%autosetup -c -T -D -b 4
%autosetup -c -T -D -b 5
%autosetup -c -T -D -b 6
%autosetup -c -T -D -b 7
%autosetup -c -T -D -b 8


%changelog
* Thu Jun 07 2018 Nikola Forró <nforro@redhat.com> - 0.1-1
- first version
