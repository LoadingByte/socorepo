import logging
import os
from typing import List
from urllib.parse import urljoin

from socorepo.locators.helpers import fetch_json
from socorepo.locators.nexus3 import Nexus3, Nexus3ComponentData
from socorepo.structs import ComponentPrototype, AssetPrototype

log = logging.getLogger("socorepo")


def fetch_component_prototypes(locator: Nexus3) -> List[ComponentPrototype]:
    if not locator.verify_tls_certificate:
        log.warning("As specified in the repository settings, will now connect to the HTTPS server '%s' without"
                    " verifying its TLS certificate.", locator.server)

    api_url = urljoin(locator.server,
                      "service/rest/v1/search"
                      f"?repository={locator.repository}"
                      f"&name={locator.component_name}"
                      + (f"&group={locator.component_group}" if locator.component_group is not None else ""))

    components = []
    continuation_token = -1  # -1 is a special value hinting the first iteration

    while continuation_token:
        query_url = api_url
        if continuation_token != -1:
            query_url += "&continuationToken=" + continuation_token

        try:
            json_resp = fetch_json(url=query_url, verify=locator.verify_tls_certificate)
        except IOError as e:
            log.error("Cannot fetch components. "
                      "Are you sure that the server URL '%s' is correct "
                      "and the repository '%s' actually exists? Exception is: %s",
                      locator.server, locator.repository, e)
            return []

        continuation_token = json_resp["continuationToken"]
        components += [_parse_component(locator, json_component) for json_component in json_resp["items"]]

    return components


def _parse_component(locator: Nexus3, json_component: dict) -> ComponentPrototype:
    nexus_version = json_component["version"]
    version = nexus_version

    # Special case for Maven repositories:
    # For snapshots, Nexus claims that the version contains a timestamp.
    # This code recovers the true version.
    if json_component["format"] == "maven2" and len(json_component["assets"]) != 0:
        sample_path = json_component["assets"][0]["path"]
        if "snapshot" in sample_path.lower():
            build_number = version[version.rindex("-") + 1:]
            version = sample_path.split("/")[-2] + "." + build_number

    assets = [_parse_asset(json_asset) for json_asset in json_component["assets"]
              if _is_relevant_asset(json_asset)]

    return ComponentPrototype(version=version, assets=assets,
                              locator_id=locator.id,
                              extra_data=Nexus3ComponentData(nexus_version=json_component["version"]))


# Filters out irrelevant checksum and PGP signature files.
def _is_relevant_asset(json_asset: dict) -> bool:
    file_ext = os.path.splitext(json_asset["path"])[1]
    return not any(s in file_ext for s in ["md5", "sha", "asc"])


def _parse_asset(json_asset: dict) -> AssetPrototype:
    filename = os.path.basename(json_asset["path"])

    # Special case for NuGet repositories.
    if json_asset["format"] == "nuget":
        filename = json_asset["path"].replace("/", ".") + ".nupkg"

    return AssetPrototype(filename=filename,
                          file_size=None,
                          url=json_asset["downloadUrl"],
                          checksums=json_asset["checksum"])
