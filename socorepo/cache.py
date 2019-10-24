import logging
from threading import Timer
from typing import Dict

from socorepo import config
from socorepo.fetcher import fetch_components
from socorepo.structs import Component

component_cache: Dict[str, Dict[str, Component]] = {}


def _fetch_all_components():
    new_component_cache = {}

    for project in config.PROJECTS.values():
        logging.info("Now fetching components for project '%s' using %s locator...",
                     project.id, type(project.locator).__name__)

        try:
            new_component_cache[project.id] = fetch_components(project)
        except Exception:
            logging.exception("An unexpected and uncaught exception occurred while fetching. "
                              "Will continue with the next project shortly...")

    return new_component_cache


def _periodic():
    global component_cache

    # Schedule the next iteration.
    t = Timer(config.FETCH_INTERVAL, _periodic)
    t.daemon = True
    t.start()

    # Actually update the cache.
    logging.info("Will now start updating the component cache by fetching the components of all projects...")
    new_component_cache = _fetch_all_components()
    component_cache = new_component_cache
    logging.info("Finished updating the component cache.")


_periodic()
