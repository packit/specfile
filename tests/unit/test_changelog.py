# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import datetime

import dateutil.tz

from specfile.changelog import Changelog, ChangelogEntry
from specfile.sections import Section


def test_parse():
    changelog = Changelog.parse(
        Section(
            "changelog",
            [
                "* Thu Jan 13 08:12:41 UTC 2022 Nikola Forró <nforro@redhat.com> - 0.2-2",
                "- rebuilt",
                "",
                "* Mon Oct 18 12:34:45 CEST 2021 Nikola Forró <nforro@redhat.com> - 0.2-1",
                "- new upstream release",
                "",
                "* Thu Jul 22 2021 Fedora Release Engineering <releng@fedoraproject.org> - 0.1-2",
                "- Rebuilt for https://fedoraproject.org/wiki/Fedora_35_Mass_Rebuild",
                "",
                "* Tue May 04 2021 Nikola Forró <nforro@redhat.com> - 0.1-1",
                "- first version",
                "  resolves: #999999999",
            ],
        )
    )
    assert len(changelog) == 4
    assert (
        changelog[0].header
        == "* Tue May 04 2021 Nikola Forró <nforro@redhat.com> - 0.1-1"
    )
    assert changelog[0].content == ["- first version", "  resolves: #999999999"]
    assert not changelog[0].extended_timestamp
    assert (
        changelog[1].header
        == "* Thu Jul 22 2021 Fedora Release Engineering <releng@fedoraproject.org> - 0.1-2"
    )
    assert changelog[1].content == [
        "- Rebuilt for https://fedoraproject.org/wiki/Fedora_35_Mass_Rebuild"
    ]
    assert not changelog[1].extended_timestamp
    assert (
        changelog[2].header
        == "* Mon Oct 18 12:34:45 CEST 2021 Nikola Forró <nforro@redhat.com> - 0.2-1"
    )
    assert changelog[2].content == ["- new upstream release"]
    assert changelog[2].extended_timestamp
    assert (
        changelog[3].header
        == "* Thu Jan 13 08:12:41 UTC 2022 Nikola Forró <nforro@redhat.com> - 0.2-2"
    )
    assert changelog[3].content == ["- rebuilt"]
    assert changelog[3].extended_timestamp


def test_get_raw_section_data():
    changelog = Changelog(
        [
            ChangelogEntry.assemble(
                datetime.date(2021, 5, 4),
                "Nikola Forró <nforro@redhat.com>",
                ["- first version", "  resolves: #999999999"],
                "0.1-1",
                append_newline=False,
            ),
            ChangelogEntry.assemble(
                datetime.date(2021, 7, 22),
                "Fedora Release Engineering <releng@fedoraproject.org>",
                ["- Rebuilt for https://fedoraproject.org/wiki/Fedora_35_Mass_Rebuild"],
                "0.1-2",
            ),
            ChangelogEntry.assemble(
                datetime.datetime(
                    2021, 10, 18, 12, 34, 45, tzinfo=dateutil.tz.gettz("CET")
                ),
                "Nikola Forró <nforro@redhat.com>",
                ["- new upstream release"],
                "0.2-1",
            ),
            ChangelogEntry.assemble(
                datetime.datetime(2022, 1, 13, 8, 12, 41),
                "Nikola Forró <nforro@redhat.com>",
                ["- rebuilt"],
                "0.2-2",
            ),
        ]
    )
    assert changelog.get_raw_section_data() == [
        "* Thu Jan 13 08:12:41 UTC 2022 Nikola Forró <nforro@redhat.com> - 0.2-2",
        "- rebuilt",
        "",
        "* Mon Oct 18 12:34:45 CEST 2021 Nikola Forró <nforro@redhat.com> - 0.2-1",
        "- new upstream release",
        "",
        "* Thu Jul 22 2021 Fedora Release Engineering <releng@fedoraproject.org> - 0.1-2",
        "- Rebuilt for https://fedoraproject.org/wiki/Fedora_35_Mass_Rebuild",
        "",
        "* Tue May 04 2021 Nikola Forró <nforro@redhat.com> - 0.1-1",
        "- first version",
        "  resolves: #999999999",
    ]
