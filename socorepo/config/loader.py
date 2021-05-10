import logging
import os
import re
import sys
from typing import Pattern

from markupsafe import Markup

from socorepo import config
from socorepo.config.toml_dict import TomlDict
from socorepo.consts import COLORS
from socorepo.locators import LOCATOR_PARSERS
from socorepo.structs import Project, VersionQualifier, AssetClfMatcher, AssetTypeMatcher

log = logging.getLogger("socorepo")

# Determine the config dir. Make the path absolute to avoid relative path confusion.
config.EXTERNAL_CONFIG = "SOCOREPO_CONFIG_DIR" in os.environ
config_dir = os.path.abspath(os.environ["SOCOREPO_CONFIG_DIR"] if config.EXTERNAL_CONFIG
                             else os.path.join(os.path.dirname(__file__), "..", "default_config"))


def load_general_settings():
    toml_settings = TomlDict.load(os.path.join(config_dir, "settings.toml"))

    config.CONFIGURE_LOGGING = toml_settings.req("configure_logging", bool)
    config.LOG_DIR = os.path.join(config_dir, toml_settings.req("log_dir", str))
    config.APPLICATION_ROOT = toml_settings.req("application_root", str)
    config.FETCH_INTERVAL = toml_settings.req("fetch_interval", int)

    config.APPEARANCE_BARE = toml_settings.req("appearance.bare", bool)
    config.APPEARANCE_TITLE = toml_settings.req("appearance.title", str)
    config.APPEARANCE_HEADING = toml_settings.req("appearance.heading", str)
    config.APPEARANCE_FAVICON_PATH = os.path.join(config_dir, toml_settings.req("appearance.favicon", str))

    config.APPEARANCE_HOMEPAGES = _load_one_markup_file_per_lang(toml_settings.req("appearance.homepage", str))
    config.APPEARANCE_FOOTERS = _load_one_markup_file_per_lang(toml_settings.req("appearance.footer", str))


def _load_one_markup_file_per_lang(root_file):
    dir_ = os.path.dirname(os.path.join(config_dir, root_file))

    prefix = os.path.basename(root_file)
    if "." in prefix:
        prefix = prefix[:prefix.rindex(".")]

    per_lang = {}
    for filename in os.listdir(dir_):
        if filename.startswith(prefix):
            lang = filename[len(prefix):]
            if "." in lang:
                lang = lang[:lang.rindex(".")]
            lang = lang[1:]  # remove _ between prefix and language if it exists
            with open(os.path.join(dir_, filename), "r") as f:
                per_lang[lang] = Markup(f.read())
    if "" not in per_lang:
        log.error("Must supply a default '%s' file without a language suffix, used when no lang matches.", root_file)
        sys.exit()
    return per_lang


def load_remaining_config():
    _load_version_qualifiers()
    _load_asset_clfs()
    _load_projects()


def _load_version_qualifiers():
    config.VERSION_QUALIFIERS = []

    toml_qualifiers = TomlDict.load(os.path.join(config_dir, "version_qualifiers.toml"))
    for ordinal, name in enumerate(toml_qualifiers):
        toml_qualifier = toml_qualifiers.sub(name)

        if toml_qualifier.opt("default", bool, fallback=False) == ("version_section_regex" in toml_qualifier):
            log.error("%s: The 'version_section_regex' of a version qualifier must be present "
                      "if and only if default = false.", toml_qualifier.error_prefix)
            sys.exit()

        default = toml_qualifier.opt("default", bool, fallback=False)
        config.VERSION_QUALIFIERS.append(VersionQualifier(
            ordinal=ordinal,
            name=name,
            color=toml_qualifier.req("color", str, choices=COLORS),
            version_section_regex=None if default else toml_qualifier.req("version_section_regex", Pattern),
            default=default,
            stable=toml_qualifier.opt("stable", bool, fallback=False)
        ))

    # Make sure there is exactly one default version qualifier.
    defaults = [qualifier for qualifier in config.VERSION_QUALIFIERS if qualifier.default]
    if len(defaults) == 1:
        config.DEFAULT_VERSION_QUALIFIER = defaults[0]
    else:
        msg = "%s: There has to be exactly one default version classifier."
        if len(defaults) > 1:
            msg += f" You have defined {len(defaults)}: " + _quote_and_join(q.name for q in defaults)
        log.error(msg, toml_qualifiers.error_prefix)
        sys.exit()


def _load_asset_clfs():
    toml_asset_clfs = TomlDict.load(os.path.join(config_dir, "asset_classifiers.toml"))

    config.ASSET_CLF_MATCHERS = [
        # Note: Don't split the key as it might contain dots!
        AssetClfMatcher(clf=clf, filename_regex=toml_asset_clfs.req(clf, Pattern, split_key=False))
        for clf in toml_asset_clfs
    ]

    config.ASSET_CLFS = [matcher.clf for matcher in config.ASSET_CLF_MATCHERS]

    # Make sure the asset clfs do not contain any whitespace or question marks.
    clfs_with_whitespace = [clf for clf in config.ASSET_CLFS if re.search(r"[\s?]", clf)]
    if clfs_with_whitespace:
        log.error("%s: Asset classifiers are not allowed to contain any whitespace or question marks. "
                  "The following classifiers violate that rule: %s",
                  toml_asset_clfs.error_prefix, _quote_and_join(clfs_with_whitespace))
        sys.exit()


def _load_projects():
    config.PROJECTS = {}

    toml_available_templates = TomlDict.load(os.path.join(config_dir, "project_templates.toml"))
    toml_projects = TomlDict.load(os.path.join(config_dir, "projects.toml"))

    for project_id in toml_projects:
        toml_project = toml_projects.sub(project_id)

        # Recursively resolve included templates.
        toml_project.apply_templates(toml_available_templates)

        descriptions = {}
        for key in toml_project:
            if key.startswith("description"):
                lang = key[len("description_"):]
                descriptions[lang] = Markup(toml_project.req(key, str))
        if descriptions and "" not in descriptions:
            log.error("%s: Must supply a default description without a language suffix, used when no lang matches.",
                      toml_project.error_prefix)
            sys.exit()

        # Parse optional version substitutions.
        version_substitutions = []
        if "version_substitutions" in toml_project:
            for toml_version_sub in toml_project.sub_list("version_substitutions"):
                pattern = toml_version_sub.req("pattern", Pattern)
                repl = toml_version_sub.req("repl", str)
                version_substitutions.append((pattern, repl))

        excluded_asset_clfs = toml_project.opt("excluded_asset_clfs", list, fallback=[])

        try:
            featured_asset_type_matchers = [AssetTypeMatcher(pattern) for pattern
                                            in toml_project.opt("featured_asset_types", list, fallback=[])]
        except ValueError as e:
            log.error("%s: Error while parsing featured asset types: %s",
                      toml_project.error_prefix, e)
            sys.exit()

        # Make sure the referenced excluded clfs are actually defined.
        undefined_asset_clfs = set(excluded_asset_clfs).difference(config.ASSET_CLFS)
        if undefined_asset_clfs:
            log.error("%s: These asset classifiers are referenced in value behind key 'excluded_asset_clfs' "
                      "even though they have not been defined in 'asset_classifiers.toml': %s",
                      toml_project.error_prefix, _quote_and_join(undefined_asset_clfs))
            sys.exit()

        # Parse locators.
        locators = []
        for locator_id in toml_project.sub("locators"):
            toml_locator = toml_project.sub(f"locators.{locator_id}")
            locator_type = toml_locator.req("type", str, choices=LOCATOR_PARSERS)
            locator = LOCATOR_PARSERS[locator_type](locator_id, toml_locator)
            locators.append(locator)

        # Parse the rest of the project and register it to the config module.
        project = Project(
            id=project_id,
            label=toml_project.req("label", str),
            descriptions=descriptions,
            version_substitutions=version_substitutions,
            excluded_asset_clfs=excluded_asset_clfs,
            featured_asset_type_matchers=featured_asset_type_matchers,
            locators=locators
        )
        config.PROJECTS[project_id] = project


def _quote_and_join(objs):
    return ", ".join(f"'{obj}'" for obj in objs)
