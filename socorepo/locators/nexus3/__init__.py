from dataclasses import dataclass
from typing import Union, List, Dict
from urllib.parse import urljoin

from markupsafe import Markup

from socorepo.config.toml_dict import TomlDict
from socorepo.l10n import _
from socorepo.locators.helpers import ensure_trailing_slash
from socorepo.structs import Locator, ComponentPrototype, Component


@dataclass(frozen=True)
class Nexus3(Locator):
    server: str
    verify_tls_certificate: bool
    repository: str
    component_group: str
    component_name: str

    def fetch_component_prototypes(self) -> List[ComponentPrototype]:
        from . import fetcher  # avoid cyclic dependencies
        return fetcher.fetch_component_prototypes(self)

    def component_info_table(self, component: Component) -> Dict[str, Union[str, Markup]]:
        repository_url = urljoin(self.server, "#browse/browse:" + self.repository)

        comp_url = urljoin(self.server, "#browse/search/custom=repository_name%3D" + self.repository)
        coord_markup = ""
        if self.component_group:
            comp_url += "%20AND%20group.raw%3D" + self.component_group
            coord_markup += f'<a href="{comp_url}" target="_blank">{self.component_group}</a> &rightarrow; '
        comp_url += "%20AND%20name.raw%3D" + self.component_name
        coord_markup += f'<a href="{comp_url}" target="_blank">{self.component_name}</a> &rightarrow; '
        comp_url += "%20AND%20version%3D" + component.extra_data[self.id].nexus_version
        coord_markup += f'<a href="{comp_url}" target="_blank">{component.version}</a>'

        return {
            _("locator.source_type"): _("locator.nexus3.source_type"),
            _("locator.nexus3.repository"): Markup(
                f'<a href="{self.server}" target="_blank">{self.server}</a> &rightarrow; '
                f'<a href="{repository_url}" target="_blank">{self.repository}</a>'
            ),
            _("locator.nexus3.component_coordinates"): Markup(coord_markup)
        }


@dataclass(frozen=True)
class Nexus3ComponentData:
    nexus_version: str


def parse_locator(locator_id: str, toml_locator: TomlDict):
    return Nexus3(id=locator_id,
                  server=ensure_trailing_slash(toml_locator.req("server", str)),
                  verify_tls_certificate=toml_locator.opt("verify_tls_certificate", bool, fallback=True),
                  repository=toml_locator.req("repository", str),
                  component_group=toml_locator.opt("component_group", str),
                  component_name=toml_locator.req("component_name", str))
