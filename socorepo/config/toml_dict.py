from __future__ import annotations

import logging
import os
import re
import sys
from typing import List, Type, Pattern

import toml

log = logging.getLogger("socorepo")


class TomlDict:
    _filename: str
    _dict: dict
    _prefix: List[str]

    @staticmethod
    def load(file: str) -> TomlDict:
        return TomlDict(filename=os.path.basename(file), dict_=toml.load(file), prefix=[])

    def __init__(self, filename: str, dict_: dict, prefix: List[str]):
        self._filename = filename
        self._dict = dict_
        self._prefix = prefix

    def sub(self, key: str, *, split_key: bool = True) -> TomlDict:
        try:
            key_arr = key.split(".") if split_key else [key]
            return self._sub(key_arr)
        except LookupError as e:
            log.error(str(e))
            sys.exit()

    def sub_list(self, key: str, *, split_key: bool = True) -> List[TomlDict]:
        try:
            key_arr = key.split(".") if split_key else [key]
            return self._sub(key_arr[:-1])._sub_list(key_arr[-1])
        except LookupError as e:
            log.error(str(e))
            sys.exit()

    def req(self, key: str, type_: Type, *, split_key: bool = True, choices: list = None):
        try:
            key_arr = key.split(".") if split_key else [key]
            return self._sub(key_arr[:-1])._get(key_arr[-1], type_, choices)
        except LookupError as e:
            log.error(str(e))
            sys.exit()

    def opt(self, key: str, type_: Type, *, split_key: bool = True, choices: list = None, apply: callable = None,
            fallback=None):
        try:
            key_arr = key.split(".") if split_key else [key]
            val = self._sub(key_arr[:-1])._get(key_arr[-1], type_, choices)
            return apply(val) if apply else val
        except LookupError:
            return fallback

    def merge(self, other: TomlDict):
        for k, v2 in other._dict.items():
            if k not in self._dict:
                self._dict[k] = v2
            else:
                v1 = self._dict[k]
                if isinstance(v1, dict) and isinstance(v2, dict):
                    self.sub(k).merge(other.sub(k))
                elif isinstance(v1, list) and isinstance(v2, list):
                    v1 += v2

    def apply_templates(self, available_templates: TomlDict):
        while "__templates__" in self._dict:
            template_id = self._dict["__templates__"].pop(0)
            if template_id not in available_templates._dict:
                log.error("%s: Included template '%s' not found in '%s'.",
                          self.error_prefix, template_id, available_templates._filename)
                sys.exit()

            self.merge(available_templates.sub(template_id))
            if len(self._dict["__templates__"]) == 0:
                del self._dict["__templates__"]

        for k, v in self._dict.items():
            if isinstance(v, dict):
                self.sub(k).apply_templates(available_templates)

    @property
    def error_prefix(self):
        loc = f"In config file '{self._filename}'"
        if self._prefix:
            loc += f" under key prefix '" + ".".join(self._prefix) + "'"
        return loc

    def __iter__(self):
        return iter(self._dict)

    def _sub(self, key_arr: List[str]):
        if len(key_arr) == 0:
            return self

        # Check that the key exists.
        if key_arr[0] not in self._dict:
            raise LookupError(f"{self.error_prefix}: Expected key '{key_arr[0]}' is missing.")

        val = self._dict[key_arr[0]]

        # Check that the value is a dict.
        if not isinstance(val, dict):
            raise LookupError(f"{self.error_prefix}: Expected key '{key_arr[0]}' to be a table/dict. "
                              f"Found a value of type '{type(val).__name__}' instead.")

        next_dict = TomlDict(filename=self._filename, dict_=val, prefix=self._prefix + [key_arr[0]])
        return next_dict if len(key_arr) == 1 else next_dict._sub(key_arr[1:])

    def _sub_list(self, key: str):
        # Check that the key exists.
        if key not in self._dict:
            raise LookupError(f"{self.error_prefix}: Expected key '{key}' is missing.")

        val = self._dict[key]

        # Check that the value is a list.
        if not isinstance(val, list):
            raise LookupError(f"{self.error_prefix}: Expected key '{key}' to be a list. "
                              f"Found a value of type '{type(val).__name__}' instead.")

        # Check that each element of the list is a dict and wrap these dicts in TomlDicts.
        sub_dicts = []
        for idx, elem in enumerate(val):
            if not isinstance(elem, dict):
                raise LookupError(f"{self.error_prefix}: Expected all elements in key '{key}' to be tables/dicts. "
                                  f"Found a value of type '{type(elem).__name__}' at index {idx} instead.")
            sub_dicts.append(TomlDict(filename=self._filename, dict_=elem, prefix=self._prefix + [key, str(idx)]))
        return sub_dicts

    def _get(self, key: str, type_: Type, choices: list):
        # Check that the key exists.
        if key not in self._dict:
            raise LookupError(f"{self.error_prefix}: Expected key '{key}' is missing.")

        val = self._dict[key]
        val = self._parse_and_check_value(key, type_, choices, val)
        return val

    def _parse_and_check_value(self, key: str, type_: type, choices: list, val):
        if type_ == Pattern:
            # If the programmer requested a regex pattern, we try to parse it for him...
            if not isinstance(val, str):
                raise LookupError(f"{self.error_prefix}: Expected value behind key '{key}' to be a regex string. "
                                  f"Found a value of type '{type(val).__name__}' instead.")
            try:
                # Note that ALL regexes are considered to be case-insensitive!
                val = re.compile(val, re.IGNORECASE)
            except re.error as e:
                raise LookupError(f"{self.error_prefix}: Error while parsing regex behind key '{key}': {e}")
        else:
            # ... and otherwise, we just check whether the value is of the type requested by the programmer.
            # The actual type conversion has already been done internally by TOML.
            if not isinstance(val, type_):
                raise LookupError(f"{self.error_prefix}: Expected value behind key '{key}' to be of type "
                                  f"'{type_.__name__}'. Found a value of type '{type(val).__name__}' instead.")

        # Make sure that the value is not a dict, because in that case, the programmer would need to use sub().
        if isinstance(val, dict):
            raise LookupError(f"{self.error_prefix}: You cannot retrieve table/dict value behind key '{key}' "
                              "with req() or opt(). Use sub() instead.")

        # If the programmer specified a limited list of choices for the value,
        # make sure the value is one of those choices.
        if choices is not None and val not in choices:
            msg_choices = ", ".join(f"'{choice}'" for choice in choices)
            raise LookupError(f"{self.error_prefix}: Expected value behind key '{key}' to be one of {msg_choices}. "
                              f"Found value '{val}' instead.")

        # In case we modified the value, return the new one.
        return val
