import logging
from typing import List
from urllib.parse import urljoin

from socorepo.consts import CLF_SOURCES
from socorepo.locators.helpers import fetch_json
from socorepo.locators.pypi import PyPI
from socorepo.structs import ComponentPrototype, AssetPrototype

log = logging.getLogger("socorepo")


def fetch_component_prototypes(locator: PyPI) -> List[ComponentPrototype]:
    if not locator.verify_tls_certificate:
        log.warning("As specified in the repository settings, will now connect to the HTTPS server '%s' without"
                    " verifying its TLS certificate.", locator.server)

    query_url = urljoin(locator.server, f"{locator.project}/json")

    try:
        json_resp = fetch_json(url=query_url, verify=locator.verify_tls_certificate)
    except IOError as e:
        log.error("Cannot fetch components. "
                  "Are you sure that the server URL '%s' is correct "
                  "and the project '%s' actually exists? Exception is: %s",
                  locator.server, locator.project, e)
        return []

    return [ComponentPrototype(version=version,
                               assets=[_parse_asset(json_asset) for json_asset in json_assets],
                               locator_id=locator.id)
            for version, json_assets in json_resp["releases"].items()]


def _parse_asset(json_asset: dict) -> AssetPrototype:
    forced_clfs = []
    if json_asset["packagetype"] == "sdist":
        forced_clfs.append(CLF_SOURCES)

    return AssetPrototype(filename=json_asset["filename"],
                          file_size=json_asset["size"],
                          url=json_asset["url"],
                          checksums=json_asset["digests"],
                          forced_clfs=forced_clfs)
