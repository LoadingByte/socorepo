import logging

import urllib3
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from socorepo import config
from socorepo.config.loader import load_general_settings, load_remaining_config
from socorepo.log import setup_logging


def app_root_404(env, resp):
    resp("404", [("Content-Type", "text/plain")])
    return [b"404 The application root has been reconfigured."]


__version__ = "1.2.0"

# Disable unverified TLS certificate warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load the basic config, which we require for setting up logging.
load_general_settings()

if config.CONFIGURE_LOGGING:
    setup_logging(config.LOG_DIR if config.EXTERNAL_CONFIG else None)

# Now, we can load the remaining config. Any errors here will be logged to the logfile.
load_remaining_config()

if not config.EXTERNAL_CONFIG:
    logging.getLogger("socorepo").warning(
        "Running off internally stored default configuration files. This might not be what you want. "
        "See README for more information on how to use your own configuration.")

# Create the app.
app = Flask(__name__)
app.config["WTF_CSRF_ENABLED"] = False

# Change the application root if configured.
if config.APPLICATION_ROOT != "/":
    app.config["APPLICATION_ROOT"] = config.APPLICATION_ROOT
    app.wsgi_app = DispatcherMiddleware(app_root_404, {config.APPLICATION_ROOT: app.wsgi_app})

# Initialize routes.
from . import views

# Start the cache scheduler.
from . import cache
