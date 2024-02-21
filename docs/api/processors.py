# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import dataclasses
import re
from typing import List, Optional

import docspec
from pydoc_markdown.interfaces import Processor, Resolver


@dataclasses.dataclass
class EscapeBracketsProcessor(Processor):
    """
    Processor that escapes curly brackets in Python template placeholders
    and RPM macros as they have special meaning in MDX files.
    """

    def process(
        self, modules: List[docspec.Module], resolver: Optional[Resolver]
    ) -> None:
        docspec.visit(modules, self._process)

    def _process(self, obj: docspec.ApiObject) -> None:
        if not obj.docstring:
            return
        obj.docstring.content = re.sub(
            r"(%|\$)\{(.+?)\}",
            r"\g<1>\{\g<2>\}",
            obj.docstring.content,
        )
