# Socorepo

Socorepo, the SOftware COmponent REPOsitory exPOser, is a lightweight Python webapp that pulls
software component listings from a variety of different sources and presents them as intuitive download sites
to end users.

A production instance of the webapp is permanently hosted at https://loadingbyte.com/dl. Try it out!

## Features

* Pulls software components from Nexus 3, GitHub, or PyPI repositories.
* "Just works": Listings are sorted and classified by sensible and generic (yet configurable) standards.
* Extremely lightweight: No external services like databases required.
* Configured fully by simple config files.
* Features a REST API.
* 100% JavaScript-free. Doesn't employ any JavaScript in the browser.

## Install

Socorepo can be installed from PyPI:

    $ pip install socorepo

You can then quickly deploy Socorepo, e.g., using [Gunicorn](https://gunicorn.org/):

    $ pip install gunicorn
    $ gunicorn -b 127.0.0.1:4000 socorepo:app

## Configure

When you just fire up Socorepo, it uses the default configuration files that it ships with.
You probably want to edit these files.
To do that, first extract the default configuration files using:

    $ socorepo-default-config

This will copy the default configuration files into a new `config/` folder in your shell's current directory.
Now put that folder wherever you want.
When you start Socorepo in the future, simply supply the path to your new config directory
in the environment variable `SOCOREPO_CONFIG_DIR`:

    $ SOCOREPO_CONFIG_DIR=/path/to/config/ gunicorn -b 127.0.0.1:4000 socorepo:app

All configuration files use the [TOML](https://github.com/toml-lang/toml) configuration format.

The `settings.toml` file contains straightforward general settings which are explained in detail by the comments in that file.
Meanwhile, the `projects.toml` file defines the software projects for which Socorepo presents download pages.
When configuring Socorepo for the first time, start with these two files and use the extensive comments as a guide.
The remaining `.toml` files you probably won't need to touch for starters.
