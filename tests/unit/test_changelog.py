# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy
import datetime
from typing import List, Optional, Union

import pytest

from specfile.changelog import (
    _OPENSUSE_CHANGELOG_SEPARATOR,
    Changelog,
    ChangelogEntry,
    ChangelogStyle,
)
from specfile.sections import Section
from specfile.utils import EVR


@pytest.mark.parametrize(
    "header, evr",
    [
        ("* Thu Jan 04 2007 Michael Schwendt <mschwendt@fedoraproject.org>", None),
        ("* Thu Jan 04 2007 Michael Schwendt <mschwendt@fedora-project.org>", None),
        (
            "* Fri Jul 26 2024 Miroslav Suchý <msuchy@redhat.com> - ss981107-67",
            EVR(version="ss981107", release="67"),
        ),
        (
            "* Mon Jul 13 2020 Tom Stellard <tstellar@redhat.com> 4.0-0.4.pre2",
            EVR(version="4.0", release="0.4.pre2"),
        ),
        (
            "* Fri Jul 20 2018 Gwyn Ciesla <limburgher@gmail.com> - 0.52-6",
            EVR(version="0.52", release="6"),
        ),
        (
            "* Mon Feb 23 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> "
            "- 1.23-3.20081106gitbe42b4",
            EVR(version="1.23", release="3.20081106gitbe42b4"),
        ),
        (
            "* Thu Feb 04 2016 Marcin Zajaczkowski <mszpak ATT wp DOTT pl> - 1:0.9.10-6",
            EVR(epoch=1, version="0.9.10", release="6"),
        ),
        (
            "* Mon Jan 03 2022 Fedora Kernel Team <kernel-team@fedoraproject.org> [5.16-0.rc8.55]",
            EVR(version="5.16", release="0.rc8.55"),
        ),
        (
            "* Wed Jan 23 2002 Karsten Hopp <karsten@redhat.de> (4.6-1)",
            EVR(version="4.6", release="1"),
        ),
        (
            "* Thu Apr  9 2015 Jeffrey C. Ollie <jeff@ocjtech.us> - 13.3.2-1:",
            EVR(version="13.3.2", release="1"),
        ),
    ],
)
def test_entry_evr(header, evr: Optional[EVR]):
    assert evr == ChangelogEntry(header, [""]).evr


@pytest.mark.parametrize(
    "header, extended",
    [
        ("* Tue May 4 2021 Nikola Forró <nforro@redhat.com> - 0.1-1", False),
        ("* Tue May  4 2021 Nikola Forró <nforro@redhat.com> - 0.1-1", False),
        (
            "* Thu Jul 22 2021 Fedora Release Engineering <releng@fedoraproject.org> - 0.1-2",
            False,
        ),
        (
            "* Mon Oct 18 12:34:45 CEST 2021 Nikola Forró <nforro@redhat.com> - 0.2-1",
            True,
        ),
    ],
)
def test_entry_has_extended_timestamp(header, extended):
    assert ChangelogEntry(header, [""]).extended_timestamp == extended


@pytest.mark.parametrize(
    "header, padding",
    [
        ("* Tue May 4 2021 Nikola Forró <nforro@redhat.com> - 0.1-1", ""),
        ("* Tue May 04 2021 Nikola Forró <nforro@redhat.com> - 0.1-1", "0"),
        ("* Tue May  4 2021 Nikola Forró <nforro@redhat.com> - 0.1-1", " "),
        (
            "* Thu Jul 22 2021 Fedora Release Engineering <releng@fedoraproject.org> - 0.1-2",
            "",
        ),
        (
            "* Mon Oct  18 12:34:45 CEST 2021 Nikola Forró <nforro@redhat.com> - 0.2-1",
            " ",
        ),
    ],
)
def test_entry_day_of_month_padding(header, padding):
    assert ChangelogEntry(header, [""]).day_of_month_padding == padding


@pytest.mark.parametrize(
    "since, until, evrs",
    [
        (None, None, ["0.1-1", "0.1-2", "0.2-1", "0.2-2"]),
        ("0.1-1", None, ["0.1-1", "0.1-2", "0.2-1", "0.2-2"]),
        ("0.1-2", None, ["0.1-2", "0.2-1", "0.2-2"]),
        ("0.2-1", None, ["0.2-1", "0.2-2"]),
        (None, "0.2-2", ["0.1-1", "0.1-2", "0.2-1", "0.2-2"]),
        (None, "0.2-1", ["0.1-1", "0.1-2", "0.2-1"]),
        (None, "0.1-2", ["0.1-1", "0.1-2"]),
        ("0.1-1", "0.2-2", ["0.1-1", "0.1-2", "0.2-1", "0.2-2"]),
        ("0.1-2", "0.2-1", ["0.1-2", "0.2-1"]),
        ("0.2-1", "0.2-1", ["0.2-1"]),
        ("0.2-2", "0.1-1", []),
        ("0.0.1-1", None, ["0.1-1", "0.1-2", "0.2-1", "0.2-2"]),
        ("0.3-1", None, []),
        (None, "0.0.1-1", []),
        (None, "0.3-1", ["0.1-1", "0.1-2", "0.2-1", "0.2-2"]),
        ("0.0.1-1", "0.3-1", ["0.1-1", "0.1-2", "0.2-1", "0.2-2"]),
    ],
)
def test_filter(since, until, evrs):
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
                datetime.datetime(2021, 10, 18, 12, 34, 45),
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
    assert [e.evr for e in changelog.filter(since=since, until=until)] == [
        EVR.from_string(evr) for evr in evrs
    ]


def test_parse():
    changelog = Changelog.parse(
        Section(
            "changelog",
            data=[
                "* Fri Jan 27 2023 Nikola Forró <nforro@redhat.com> - 0.4-1",
                "",
                "* this is also a valid entry",
                "",
                "* Fri Jan 27 2023 Nikola Forró <nforro@redhat.com> - 0.3-2",
                "* this is a valid entry",
                "",
                "* Mon Nov 21 2022 Nikola Forró <nforro@redhat.com> - 0.3-1",
                "- this is a formatted",
                "  changelog entry",
                "",
                "- here is another item",
                "",
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
    assert len(changelog) == 7
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
    assert (
        changelog[4].header
        == "* Mon Nov 21 2022 Nikola Forró <nforro@redhat.com> - 0.3-1"
    )
    assert changelog[4].content == [
        "- this is a formatted",
        "  changelog entry",
        "",
        "- here is another item",
    ]
    assert not changelog[4].extended_timestamp
    assert (
        changelog[5].header
        == "* Fri Jan 27 2023 Nikola Forró <nforro@redhat.com> - 0.3-2"
    )
    assert changelog[5].content == [
        "* this is a valid entry",
    ]
    assert not changelog[5].extended_timestamp
    assert (
        changelog[6].header
        == "* Fri Jan 27 2023 Nikola Forró <nforro@redhat.com> - 0.4-1"
    )
    assert changelog[6].content == [
        "",
        "* this is also a valid entry",
    ]
    assert not changelog[6].extended_timestamp

    assert all(
        changelog_entry.style == ChangelogStyle.standard
        for changelog_entry in changelog
    )


def test_suse_style_changelog_parse():
    changelog = Changelog.parse(
        Section(
            "changelog",
            data=[
                "-------------------------------------------------------------------",
                "Tue Dec 17 14:21:37 UTC 2024 - Dan Čermák <dan.cermak@cgc-instruments.com>",
                "",
                "- First version",
                "",
                "-------------------------------------------------------------------",
                "Mon Nov  4 17:47:23 UTC 2024 - Dan Čermák <dan.cermak@cgc-instruments.com>",
                "",
                "- # [0.9.37] - September 4th, 2024",
                "",
                "-------------------------------------------------------------------",
                "Fri May 17 09:14:20 UTC 2024 - Dominique Leuenberger <dimstar@opensuse.org>",
                "",
                "- Use %patch -P N instead of deprecated %patchN syntax.",
                "",
                "-------------------------------------------------------------------",
                "Mon Oct 10 13:27:24 UTC 2022 - Stephan Kulow <coolo@suse.com>",
                "",
                "updated to version 0.9.28",
                " see installed CHANGELOG.md",
                "",
                "",
                "-------------------------------------------------------------------",
                "Fri Jun 25 07:31:34 UTC 2021 - Dan Čermák <dcermak@suse.com>",
                "",
                "- New upstream release 0.9.26",
                "",
                "  - Add support for Ruby 3.0 and fix tests",
                "  - Fix support for `frozen_string_literal: false`"
                " magic comments (#1363)",
                "",
                "",
            ],
        )
    )

    assert isinstance(changelog, Changelog)
    assert len(changelog) == 5

    for changelog_entry, hdr, content in zip(
        changelog,
        reversed(
            (
                "Tue Dec 17 14:21:37 UTC 2024 - Dan Čermák <dan.cermak@cgc-instruments.com>",
                "Mon Nov  4 17:47:23 UTC 2024 - Dan Čermák <dan.cermak@cgc-instruments.com>",
                "Fri May 17 09:14:20 UTC 2024 - Dominique Leuenberger <dimstar@opensuse.org>",
                "Mon Oct 10 13:27:24 UTC 2022 - Stephan Kulow <coolo@suse.com>",
                "Fri Jun 25 07:31:34 UTC 2021 - Dan Čermák <dcermak@suse.com>",
            )
        ),
        reversed(
            (
                ["- First version"],
                ["- # [0.9.37] - September 4th, 2024"],
                ["- Use %patch -P N instead of deprecated %patchN syntax."],
                ["updated to version 0.9.28", " see installed CHANGELOG.md"],
                [
                    "- New upstream release 0.9.26",
                    "",
                    "  - Add support for Ruby 3.0 and fix tests",
                    "  - Fix support for `frozen_string_literal: false`"
                    " magic comments (#1363)",
                ],
            )
        ),
    ):

        assert isinstance(changelog_entry, ChangelogEntry)
        assert changelog_entry.evr is None
        assert changelog_entry.header == _OPENSUSE_CHANGELOG_SEPARATOR + "\n" + hdr
        assert changelog_entry.content == [""] + content
        assert changelog_entry.extended_timestamp
        assert changelog_entry.style == ChangelogStyle.openSUSE


@pytest.mark.parametrize(
    "timestamp,author,content,entry",
    (
        [
            (
                datetime.datetime(2021, 6, 25, 7, 31, 34),
                "Dan Čermák <dcermak@suse.com>",
                ["", "New upstream release 0.9.26"],
                ChangelogEntry(
                    header=(
                        _OPENSUSE_CHANGELOG_SEPARATOR
                        + "\n"
                        + "Fri Jun 25 07:31:34 UTC 2021 - Dan Čermák <dcermak@suse.com>"
                    ),
                    content=["", "New upstream release 0.9.26"],
                ),
            ),
            (
                datetime.date(2021, 6, 25),
                "Dan Čermák <dcermak@suse.de>",
                [
                    "",
                    "New upstream release 0.26",
                    "Fixed a major regression in Foo",
                ],
                ChangelogEntry(
                    header=(
                        _OPENSUSE_CHANGELOG_SEPARATOR
                        + "\n"
                        + "Fri Jun 25 12:00:00 UTC 2021 - Dan Čermák <dcermak@suse.de>"
                    ),
                    content=[
                        "",
                        "New upstream release 0.26",
                        "Fixed a major regression in Foo",
                    ],
                ),
            ),
        ]
    ),
)
def test_create_opensuse_changelog_assemble(
    timestamp: Union[datetime.datetime, datetime.date],
    author: str,
    content: List[str],
    entry: ChangelogEntry,
) -> None:
    assert (
        ChangelogEntry.assemble(
            timestamp,
            author,
            content,
            style=ChangelogStyle.openSUSE,
            append_newline=False,
        )
        == entry
    )


def test_get_raw_section_data():
    tzinfo = datetime.timezone(datetime.timedelta(hours=2), name="CEST")
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
                datetime.datetime(2021, 10, 18, 12, 34, 45, tzinfo=tzinfo),
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
            ChangelogEntry.assemble(
                datetime.date(2022, 11, 21),
                "Nikola Forró <nforro@redhat.com>",
                [
                    "- this is a formatted",
                    "  changelog entry",
                    "",
                    "- here is another item",
                ],
                "0.3-1",
            ),
            ChangelogEntry.assemble(
                datetime.date(2023, 1, 27),
                "Nikola Forró <nforro@redhat.com>",
                [
                    "* this is a valid entry",
                ],
                "0.3-2",
            ),
            ChangelogEntry.assemble(
                datetime.date(2023, 1, 27),
                "Nikola Forró <nforro@redhat.com>",
                [
                    "",
                    "* this is also a valid entry",
                ],
                "0.4-1",
            ),
        ]
    )
    assert changelog.get_raw_section_data() == [
        "* Fri Jan 27 2023 Nikola Forró <nforro@redhat.com> - 0.4-1",
        "",
        "* this is also a valid entry",
        "",
        "* Fri Jan 27 2023 Nikola Forró <nforro@redhat.com> - 0.3-2",
        "* this is a valid entry",
        "",
        "* Mon Nov 21 2022 Nikola Forró <nforro@redhat.com> - 0.3-1",
        "- this is a formatted",
        "  changelog entry",
        "",
        "- here is another item",
        "",
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


def test_copy_changelog():
    changelog = Changelog(
        [
            ChangelogEntry.assemble(
                datetime.date(2021, 5, 4),
                "Nikola Forró <nforro@redhat.com>",
                ["- first version", "  resolves: #999999999"],
                "0.1-1",
                append_newline=False,
            ),
        ]
    )
    shallow_copy = copy.copy(changelog)
    assert shallow_copy == changelog
    assert shallow_copy is not changelog
    assert shallow_copy[0] is changelog[0]
    deep_copy = copy.deepcopy(changelog)
    assert deep_copy == changelog
    assert deep_copy is not changelog
    assert deep_copy[0] is not changelog[0]
