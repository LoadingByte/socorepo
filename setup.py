import os
import re

from setuptools import setup, find_packages

DIR = os.path.dirname(__file__)

with open(os.path.join(DIR, "socorepo", "__init__.py"), encoding="utf-8") as f:
    version_file = f.read()
version_match = re.search(r'^__version__ = "([^"]*)"', version_file, re.M)
if not version_match:
    raise RuntimeError("Unable to find version string.")
VERSION = version_match.group(1)

with open(os.path.join(DIR, "README.md"), encoding="utf-8") as f:
    # Skip the first two lines since they are just the heading and look weird on PyPI.
    next(f)
    next(f)
    README = f.read()

setup(
    name="socorepo",
    version=VERSION,
    description="A webapp that fetches software version listings and presents them as download sites.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/LoadingByte/socorepo",
    author="LoadingByte",
    author_email="hello@loadingbyte.com",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Internet"
    ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.7",
    install_requires=[
        "toml",
        "requests",
        "Flask",
        "Flask-WTF"
    ],
    entry_points={
        "console_scripts": [
            "socorepo-default-config=socorepo_cli:default_config"
        ]
    }
)
