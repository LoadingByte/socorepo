import csv
import os

from flask import request
from flask.ctx import has_request_context


def _load_translations():
    dir_ = os.path.join(os.path.dirname(__file__), "l10n")
    for filename in os.listdir(dir_):
        dct = {}
        with open(os.path.join(dir_, filename), "r") as file_handle:
            reader = csv.reader(file_handle, delimiter="=")
            for row in reader:
                if len(row) == 0:
                    continue
                elif len(row) == 2:
                    dct[row[0]] = row[1]
                else:
                    raise ValueError(f"Each non-empty row in 'l10n/{filename}' must have one non-quoted '='.")
        lang = filename[:-len(".csv")]
        _translations[lang] = dct


_translations = {}
_load_translations()


def msg_lang():
    if not has_request_context():
        raise LookupError("Can't determine message language when not currently in a request context.")
    lang = getattr(request, "lang", None)
    if lang is None:
        lang = request.accept_languages.best_match(_translations.keys(), default="en")
        request.lang = lang
    return lang


def _(key, *args, **kwargs):
    return _translations[msg_lang()][key].format(*args, **kwargs)


def localized_of(variants: dict):
    if not has_request_context():
        raise LookupError("Can't select a localized variant when we're not currently in a request context.")
    lang = request.accept_languages.best_match(variants.keys(), default="")
    return variants[lang]
