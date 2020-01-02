from typing import List, Dict

from markupsafe import Markup

from socorepo.config.toml_dict import TomlDict
from socorepo.structs import Project, VersionQualifier, AssetClfMatcher

EXTERNAL_CONFIG: bool

LOG_DIR: str
APPLICATION_ROOT: str
FETCH_INTERVAL: int

APPEARANCE_TITLE: str
APPEARANCE_HEADING: str
APPEARANCE_FAVICON_PATH: str
APPEARANCE_HOMEPAGE: Markup
APPEARANCE_FOOTER: Markup

VERSION_QUALIFIERS: List[VersionQualifier]
DEFAULT_VERSION_QUALIFIER: VersionQualifier

ASSET_CLFS: List[str]
ASSET_CLF_MATCHERS: List[AssetClfMatcher]

PROJECTS: Dict[str, Project]
