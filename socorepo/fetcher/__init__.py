import logging
from collections import OrderedDict
from typing import Optional, List, Dict

from socorepo import config
from socorepo.fetcher.versions import get_version_qualifier, sort_components_by_version
from socorepo.structs import Project, AssetTypeMatcher, ComponentPrototype, AssetPrototype, Component, Asset, AssetType

log = logging.getLogger("socorepo")


def fetch_components(project: Project):
    log.info("Now fetching components for project '%s'...", project.id)
    comp_proto_list = []
    for locator in project.locators:
        log.info("Now fetching components for project '%s' using %s locator '%s'...",
                 project.id, type(locator).__name__, locator.id)
        comp_proto_list += locator.fetch_component_prototypes()
    return _new_component_dict(project, comp_proto_list)


def _new_component_dict(project: Project, comp_proto_list: List[ComponentPrototype]) -> Dict[str, Component]:
    # Group the component prototypes by version. This is necessary when multiple locators are used.
    comp_proto_groups = {}
    for comp_proto in comp_proto_list:
        version = comp_proto.version
        # Apply version substitutions if there are any.
        for pattern, replacement in project.version_substitutions:
            version = pattern.sub(replacement, version)
        comp_proto_groups.setdefault(version, []).append(comp_proto)

    # Convert the grouped component prototypes to actual components.
    comp_list = [_new_component(project, version, comp_proto_group)
                 for version, comp_proto_group in comp_proto_groups.items()]

    # Sort components in order of decreasing version.
    sorted_comp_list = sort_components_by_version(comp_list)

    # Transform the list of components into a dict which maps from a version to a component.
    return OrderedDict([(comp.version, comp) for comp in sorted_comp_list])


def _new_component(project: Project, version: str, comp_proto_group: List[ComponentPrototype]) -> Component:
    # Collect all asset prototypes of all component prototypes in the group.
    asset_protos = [asset for comp_proto in comp_proto_group for asset in comp_proto.assets]

    # Determine the type (i.e., a list of asset clfs) of each asset prototype.
    asset_types = {asset_proto: _determine_asset_type(project, asset_proto)
                   for asset_proto in asset_protos}

    # Sort the asset prototypes by (1) clfs as ordered in the config file and (2) filename.
    sorted_asset_protos = sorted(asset_protos,
                                 key=lambda asset_proto: (
                                     [config.ASSET_CLFS.index(clf) for clf in asset_types[asset_proto].clfs],
                                     asset_proto.filename)
                                 )

    # For each asset prototype, find the featured asset type matcher which matches it.
    # Note that each matcher can only match one asset and is taken out of the game afterwards.
    # Given that, it is important to know that the assets are matched in sorted order.
    #
    # Example: If a matcher matches "Py*", only the asset with the highest python version will be matched by it,
    #          since the "Py<version>" clfs are defined in order of decreasing version
    #          (at least in the default asset_classifiers.toml).
    asset_matchers = {}
    remaining_matchers = project.featured_asset_type_matchers.copy()
    for asset_proto in sorted_asset_protos:
        matcher = _find_matching_matcher(project, remaining_matchers, version, asset_proto, asset_types[asset_proto])
        asset_matchers[asset_proto] = matcher
        if matcher is not None:
            remaining_matchers.remove(matcher)

    # Convert the asset prototypes to actual assets using the obtained information.
    sorted_assets = [_new_asset(asset_proto, asset_types[asset_proto], asset_matchers[asset_proto])
                     for asset_proto in sorted_asset_protos]

    return Component(version=version,
                     qualifier=get_version_qualifier(version),
                     assets=sorted_assets,
                     extra_data={comp_proto.locator_id: comp_proto.extra_data for comp_proto in comp_proto_group})


def _determine_asset_type(project: Project, asset_proto: AssetPrototype) -> AssetType:
    # Note that this selection preserves the order of the clfs as they are defined in the config file.
    return AssetType([matcher.clf for matcher in config.ASSET_CLF_MATCHERS
                      if (matcher.matches(asset_proto.filename) or matcher.clf in asset_proto.forced_clfs)
                      and matcher.clf not in project.excluded_asset_clfs])


def _find_matching_matcher(project: Project, matchers: List[AssetTypeMatcher], version: str,
                           asset_proto: AssetPrototype, type_: AssetType) -> Optional[AssetTypeMatcher]:
    matching_matchers = [m for m in matchers if m.matches(type_)]
    if len(matching_matchers) > 1:
        log.warning("In project '%s', component with version '%s': "
                    "Asset with filename '%s' matches multiple featured asset types: %s. "
                    "This is discouraged. All but the first match will now be ignored. "
                    "Try to rewrite your featured asset types such that each asset only matches one of them.",
                    project.id, version, asset_proto.filename,
                    ", ".join(f"'{m.pattern}'" for m in matching_matchers))
    return next(iter(matching_matchers), None)


def _new_asset(asset_proto: AssetPrototype, type_: AssetType, matcher: AssetTypeMatcher) -> Asset:
    return Asset(filename=asset_proto.filename,
                 file_size=asset_proto.file_size,
                 url=asset_proto.url,
                 checksums=OrderedDict(sorted(asset_proto.checksums.items())),
                 type=type_,
                 featured=matcher is not None,
                 matcher_causing_featuring=matcher)
