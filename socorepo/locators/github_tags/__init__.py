from __future__ import annotations

from dataclasses import dataclass
from typing import Union, List, Dict
from urllib.parse import urljoin

from markupsafe import Markup

from socorepo.config.toml_dict import TomlDict
from socorepo.l10n import _
from socorepo.structs import Locator, ComponentPrototype, Component


@dataclass(frozen=True)
class GitHubTags(Locator):
    owner: str
    repository: str
    auth: Union[GitHubBasicAuth, GitHubOAuthToken, GitHubOAuthApp]

    def fetch_component_prototypes(self) -> List[ComponentPrototype]:
        from . import fetcher  # avoid cyclic dependencies
        return fetcher.fetch_component_prototypes(self)

    def component_info_table(self, component: Component) -> Dict[str, Union[str, Markup]]:
        owner_url = urljoin("https://github.com", self.owner)
        repository_url = owner_url + "/" + self.repository
        tag_url = repository_url + "/releases/tag/" + component.version
        commit_url = repository_url + "/commit/" + component.extra_data[self.id].commit

        return {
            _("locator.source_type"): _("locator.github_tags.source_type"),
            _("locator.github_tags.repository"): Markup(
                f'<a href="{owner_url}" target="_blank">{self.owner}</a> / '
                f'<a href="{repository_url}" target="_blank">{self.repository}</a>',
            ),
            _("locator.github_tags.tag_and_commit"): Markup(
                f'<a href="{tag_url}" target="_blank">{component.version}</a> / '
                f'<a href="{commit_url}" target="_blank">{component.extra_data[self.id].commit:.7}</a>'
            )
        }


@dataclass(frozen=True)
class GitHubBasicAuth:
    username: str
    password: str


@dataclass(frozen=True)
class GitHubOAuthToken:
    oauth_token: str


@dataclass(frozen=True)
class GitHubOAuthApp:
    client_id: str
    client_secret: str


@dataclass(frozen=True)
class GitHubTagsComponentData:
    commit: str


def parse_locator(locator_id: str, toml_locator: TomlDict):
    auth = None

    if "login" in toml_locator:
        auth = GitHubBasicAuth(username=toml_locator.req("login.username", str),
                               password=toml_locator.req("login.password", str))
    elif "oauth_token" in toml_locator:
        auth = GitHubOAuthToken(oauth_token=toml_locator.req("oauth_token", str))
    elif "oauth_app" in toml_locator:
        auth = GitHubOAuthApp(client_id=toml_locator.req("oauth_app.client_id", str),
                              client_secret=toml_locator.req("oauth_app.client_secret", str))

    return GitHubTags(id=locator_id,
                      owner=toml_locator.req("owner", str),
                      repository=toml_locator.req("repository", str),
                      auth=auth)
