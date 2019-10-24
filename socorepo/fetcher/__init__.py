import logging
from collections import OrderedDict
from typing import Optional, List, Dict

from socorepo import config
from socorepo.fetcher.versions import get_version_qualifier, sort_components_by_version
from socorepo.structs import Project, AssetTypeMatcher, ComponentPrototype, AssetPrototype, Component, Asset, AssetType


def fetch_components(project: Project):
    comp_proto_list = project.locator.fetch_component_prototypes()
    return _new_component_dict(project, comp_proto_list)


def _new_component_dict(project: Project, comp_proto_list: List[ComponentPrototype]) -> Dict[str, Component]:
    # Convert the component prototypes to actual components.
    comp_list = [_new_component(project, comp_proto) for comp_proto in comp_proto_list]

    # Sort components in order of decreasing version.
    sorted_comp_list = sort_components_by_version(comp_list)

    # Transform the list of components into a dict which maps from a version to a component.
    return OrderedDict([(comp.version, comp) for comp in sorted_comp_list])


def _new_component(project: Project, comp_proto: ComponentPrototype) -> Component:
    asset_protos = comp_proto.assets

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
        matcher = _find_matching_matcher(project, remaining_matchers, comp_proto, asset_proto, asset_types[asset_proto])
        asset_matchers[asset_proto] = matcher
        if matcher is not None:
            remaining_matchers.remove(matcher)

    # Convert the asset prototypes to actual assets using the obtained information.
    sorted_assets = [_new_asset(asset_proto, asset_types[asset_proto], asset_matchers[asset_proto])
                     for asset_proto in sorted_asset_protos]

    return Component(version=comp_proto.version,
                     qualifier=get_version_qualifier(comp_proto.version),
                     assets=sorted_assets,
                     extra_data=comp_proto.extra_data)


def _determine_asset_type(project: Project, asset_proto: AssetPrototype) -> AssetType:
    # Note that this selection preserves the order of the clfs as they are defined in the config file.
    return AssetType([matcher.clf for matcher in config.ASSET_CLF_MATCHERS
                      if (matcher.matches(asset_proto.filename) or matcher.clf in asset_proto.forced_clfs)
                      and matcher.clf not in project.excluded_asset_clfs])


def _find_matching_matcher(project: Project, matchers: List[AssetTypeMatcher], comp_proto: ComponentPrototype,
                           asset_proto: AssetPrototype, type_: AssetType) -> Optional[AssetTypeMatcher]:
    matching_matchers = [m for m in matchers if m.matches(type_)]
    if len(matching_matchers) > 1:
        logging.warning("In project '%s', component with version '%s': "
                        "Asset with filename '%s' matches multiple featured asset types: %s. "
                        "This is discouraged. All but the first match will now be ignored. "
                        "Try to rewrite your featured asset types such that each asset only matches one of them.",
                        project.id, comp_proto.version, asset_proto.filename,
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
