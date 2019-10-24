import string
from itertools import dropwhile
from typing import Union, List

from socorepo import config
from socorepo.structs import Component, VersionQualifier


def get_version_qualifier(version: str) -> VersionQualifier:
    for sec in _split_version(version):
        if isinstance(sec, VersionQualifier):
            return sec

    return config.DEFAULT_VERSION_QUALIFIER


def sort_components_by_version(components: List[Component]) -> List[Component]:
    return sorted(components, reverse=True,
                  key=_create_key(lambda component: _split_version(component.version),
                                  _less_than_for_split_versions))


# Splits a version into sections where either
# - a special character marks a new section or
# - a change in character class (numeric/lowercase/uppercase/other) occurs.
# Also converts numeric sections to ints.
# For example, 1.3.9-RC2b is split into [1, 3, 9, "RC", 2, "b"].
def _split_version(version: str) -> List[Union[str, int, VersionQualifier]]:
    sections = []
    start = 0
    for idx, char in enumerate(version):
        if char in string.punctuation:
            sections.append(version[start:idx])
            start = idx + 1
        elif version[start].isnumeric() != char.isnumeric():
            sections.append(version[start:idx])
            start = idx
    sections.append(version[start:])

    return list(map(_parse_version_section, sections))


def _parse_version_section(sec: str):
    if sec.isnumeric():
        return int(sec)
    else:
        for qualifier in config.VERSION_QUALIFIERS:
            if qualifier.matches(sec):
                return qualifier
        return sec


def _create_key(convert: callable, less_than: callable) -> callable:
    class Key(object):
        __slots__ = ['obj']  # RAM optimization

        def __init__(self, obj):
            self.obj = convert(obj)

        # Python guarantees to only use __lt__ when sorting.
        def __lt__(self, other):
            return less_than(self.obj, other.obj)

    return Key


# This is a slightly modified version of standard __lt__ on lists.
def _less_than_for_split_versions(split_ver_1: list, split_ver_2: list) -> bool:
    disparity = dropwhile(lambda secs: secs[0] == secs[1], zip(split_ver_1, split_ver_2))

    try:
        # --- CASE 1: The two versions differ somewhere. ---
        sec_1, sec_2 = next(disparity)

        # Special case: If the two versions differ at a section where one of the versions features a qualifier
        # and the other one doesn't, the version with the qualifier is always SMALLER (e.g., 0.3-ALPHA < 0.3.1).
        if isinstance(sec_1, VersionQualifier) and not isinstance(sec_2, VersionQualifier):
            return True
        if not isinstance(sec_1, VersionQualifier) and isinstance(sec_2, VersionQualifier):
            return False

        try:
            return sec_1 < sec_2
        except TypeError:  # in case one of the sections is a str and the other one is a number
            return str(sec_1) < str(sec_2)
    except StopIteration:
        # --- CASE 2: One version is a prefix of the other one (e.g., 0.3 and 0.3.1). ---

        # Special case: If the common prefix is immediately followed by a qualifier (e.g., 0.3 and 0.3-ALPHA),
        # the version with the qualifier is considered SMALLER, even though
        # it is longer (in contrast to standard behavior).
        if len(split_ver_1) > len(split_ver_2) and isinstance(split_ver_1[len(split_ver_2)], VersionQualifier):
            return True
        if len(split_ver_1) < len(split_ver_2) and isinstance(split_ver_2[len(split_ver_1)], VersionQualifier):
            return False

        # Standard behavior: The shorter version is considered SMALLER.
        return len(split_ver_1) < len(split_ver_2)
