import logging
import sys

import urllib3
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from socorepo import config
from socorepo.config.loader import load_config


def app_root_404(env, resp):
    resp("404", [("Content-Type", "text/plain")])
    return [b"404 The application root has been reconfigured."]


__version__ = "1.0.1"

# Load config.
load_config()

# Disable unverified TLS certificate warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging config
log_handlers = [logging.StreamHandler(sys.stderr)]
if config.EXTERNAL_CONFIG:
    log_handlers.append(logging.FileHandler(config.LOGFILE))
logging.basicConfig(level=logging.INFO,
                    handlers=log_handlers)

if not config.EXTERNAL_CONFIG:
    logging.warning("Running off internally stored default configuration files. This might not be what you want. "
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
