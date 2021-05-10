import logging
from itertools import count
from typing import List
from typing import Optional

import requests

from socorepo.consts import CLF_SOURCES
from socorepo.locators.github_tags import GitHubTags, GitHubBasicAuth, GitHubOAuthToken, GitHubOAuthApp, \
    GitHubTagsComponentData
from socorepo.locators.helpers import fetch_json
from socorepo.structs import ComponentPrototype, AssetPrototype

log = logging.getLogger("socorepo")


def fetch_component_prototypes(locator: GitHubTags) -> List[ComponentPrototype]:
    json_tag_listing = fetch_json_from_endpoint(locator, endpoint="tags")
    json_release_listing = fetch_json_from_endpoint(locator, endpoint="releases")

    components = []

    for json_tag in json_tag_listing:
        json_release = next((jr for jr in json_release_listing if jr["tag_name"] == json_tag["name"]), None)
        components.append(_parse_component(locator, json_tag, json_release))

    return components


def fetch_json_from_endpoint(locator: GitHubTags, endpoint: str) -> list:
    api_url = f"https://api.github.com/repos/{locator.owner}/{locator.repository}/{endpoint}?"
    if isinstance(locator.auth, GitHubOAuthApp):
        api_url += f"client_id={locator.auth.client_id}&client_secret={locator.auth.client_secret}"
    api_url += "per_page=100&page="

    session = requests.Session()
    session.headers.update({"Accept": "application/vnd.github.v3+json"})
    if isinstance(locator.auth, GitHubBasicAuth):
        session.auth = (locator.auth.username, locator.auth.password)
    elif isinstance(locator.auth, GitHubOAuthToken):
        session.headers.update({"Authorization": f"token {session.auth.oauth_token}"})

    json_listing = []

    for page in count(1):
        try:
            json_resp = fetch_json(url=(api_url + str(page)), session=session)
        except IOError as e:
            log.error("Cannot fetch listing of %s: %s", endpoint, e)
            return []

        if not isinstance(json_resp, list):
            log.error("GitHub returned an invalid JSON response that is not a listing of %s. "
                      "Are you sure that the repository owner '%s' and repository name '%s' actually exist and "
                      "the (optional) authentication information is correct? "
                      "First 100 chars of server's response are: %.100s",
                      endpoint, locator.owner, locator.repository, json_resp)
            return []

        # Stop when we're past the last page.
        if len(json_resp) == 0:
            break

        json_listing += json_resp

    return json_listing


def _parse_component(locator: GitHubTags, json_tag: dict, json_release: Optional[dict]) -> ComponentPrototype:
    version = json_tag["name"]
    commit = json_tag["commit"]["sha"]

    assets = [
        AssetPrototype(filename=f"{locator.owner}-{locator.repository}-{version}.zip",
                       file_size=None,
                       url=json_tag["zipball_url"],
                       checksums={},
                       forced_clfs=[CLF_SOURCES]),
        AssetPrototype(filename=f"{locator.owner}-{locator.repository}-{version}.tar.gz",
                       file_size=None,
                       url=json_tag["tarball_url"],
                       checksums={},
                       forced_clfs=[CLF_SOURCES])
    ]

    if json_release:
        for json_asset in json_release["assets"]:
            assets.append(AssetPrototype(filename=json_asset["name"],
                                         file_size=json_asset["size"],
                                         url=json_asset["browser_download_url"],
                                         checksums={}))

    return ComponentPrototype(version=version, assets=assets,
                              locator_id=locator.id,
                              extra_data=GitHubTagsComponentData(commit=commit))
