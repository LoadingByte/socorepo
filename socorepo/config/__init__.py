from typing import List, Dict

from markupsafe import Markup

from socorepo.config.toml_dict import TomlDict
from socorepo.structs import Project, VersionQualifier, AssetClfMatcher

EXTERNAL_CONFIG: bool

CONFIGURE_LOGGING: bool
LOG_DIR: str
APPLICATION_ROOT: str
FETCH_INTERVAL: int

APPEARANCE_BARE: bool
APPEARANCE_TITLE: str
APPEARANCE_HEADING: str
APPEARANCE_FAVICON_PATH: str
APPEARANCE_HOMEPAGES: Dict[str, Markup]  # per language
APPEARANCE_FOOTERS: Dict[str, Markup]  # per language

VERSION_QUALIFIERS: List[VersionQualifier]
DEFAULT_VERSION_QUALIFIER: VersionQualifier

ASSET_CLFS: List[str]
ASSET_CLF_MATCHERS: List[AssetClfMatcher]

PROJECTS: Dict[str, Project]
