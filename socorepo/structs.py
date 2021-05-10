from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Union, Optional, List, Tuple, Dict, Pattern

from markupsafe import Markup


# ======================
# === Config objects ===
# ======================

@dataclass(frozen=True)
class Project:
    id: str
    label: str
    descriptions: Dict[str, Markup]
    version_substitutions: List[Tuple[Pattern, str]]
    excluded_asset_clfs: List[str]
    featured_asset_type_matchers: List[AssetTypeMatcher]
    locators: List[Locator]


@dataclass(frozen=True)
class Locator(ABC):
    id: str

    @abstractmethod
    def fetch_component_prototypes(self) -> List[ComponentPrototype]:
        raise NotImplementedError

    def component_info_table(self, component: Component) -> Dict[str, Union[str, Markup]]:
        raise NotImplementedError


@dataclass(frozen=True, order=True)
class VersionQualifier:
    ordinal: int  # has to be the first attribute so it influences sorting
    name: str
    color: str
    version_section_regex: Optional[Pattern]  # present if and only if default = False
    default: bool
    stable: bool

    def matches(self, version_section: str) -> bool:
        return self.version_section_regex and self.version_section_regex.search(version_section) is not None


@dataclass(frozen=True)
class AssetClfMatcher:
    clf: str
    filename_regex: Pattern

    def matches(self, version: str) -> bool:
        return self.filename_regex.search(version) is not None


@dataclass(frozen=True)
class AssetTypeMatcher:
    pattern: str
    _req_clf_regexes: List[Pattern] = field(default_factory=list, init=False, repr=False, compare=False)
    _opt_clf_regexes: List[Pattern] = field(default_factory=list, init=False, repr=False, compare=False)

    def __post_init__(self):
        for clf_pattern in self.pattern.split(" "):
            req = True
            if clf_pattern.startswith("?"):
                req = False
                clf_pattern = clf_pattern[1:]

            if "?" in clf_pattern:
                raise ValueError(f"While parsing pattern {self.pattern}: The asset clf {clf_pattern} contains '?' "
                                 f"at a position that is not the beginning of the string. This is disallowed.")

            regex = re.compile(re.escape(clf_pattern).replace(r"\*", ".*").replace(r"\|", "|"), re.IGNORECASE)
            (self._req_clf_regexes if req else self._opt_clf_regexes).append(regex)

    def matches(self, type_: AssetType):
        matched_regexes = set()
        matched_clfs = set()

        for regex in self._req_clf_regexes + self._opt_clf_regexes:
            for clf in type_.clfs:
                if regex.match(clf):
                    matched_regexes.add(regex)
                    matched_clfs.add(clf)

        # Returns true iff every required patterns has matched with a clf and every clf has matched with any pattern.
        return len(set(self._req_clf_regexes).difference(matched_regexes)) == 0 and matched_clfs == set(type_.clfs)


# =====================
# === Fetched stuff ===
# =====================

@dataclass(frozen=True)
class ComponentPrototype:
    version: str
    assets: List[AssetPrototype]
    locator_id: str
    extra_data: Any = None  # optional


@dataclass(frozen=True)
class AssetPrototype:
    filename: str
    file_size: Optional[int]  # in bytes
    url: str
    # compare=False implies hash=False and that's necessary as lists and dicts aren't easily hashable.
    # Instances of this class need to be hashable because the fetcher procedure puts them in a dict.
    checksums: Dict[str, str] = field(compare=False)
    forced_clfs: List[str] = field(default_factory=list, compare=False)


@dataclass(frozen=True)
class Component:
    version: str
    qualifier: VersionQualifier
    assets: List[Asset]
    # Extra data for each locator by locator ID. Each locator which contributed to this component is present as a key,
    # but the value may be null if there's no extra data for that locator.
    extra_data: Dict[str, Any]


@dataclass(frozen=True)
class Asset:
    filename: str
    file_size: Optional[int]  # in bytes
    url: str
    checksums: Dict[str, str]
    type: AssetType
    featured: bool
    matcher_causing_featuring: Optional[AssetTypeMatcher]


@dataclass(frozen=True)
class AssetType:
    clfs: List[str]

    def __str__(self):
        return " ".join(self.clfs)
