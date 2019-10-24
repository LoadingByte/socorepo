from socorepo.locators import github_tags, nexus3, pypi

LOCATOR_PARSERS = {
    "github_tags": github_tags.parse_locator,
    "nexus3": nexus3.parse_locator,
    "pypi": pypi.parse_locator
}
