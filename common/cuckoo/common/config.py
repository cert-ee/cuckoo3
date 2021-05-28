# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import json
import platform

from copy import deepcopy

import yaml

from .utils import parse_bool

class ConfigurationError(Exception):
    pass

class ConfigurationIncompleteError(ConfigurationError):
    pass

class MissingValueError(ConfigurationError):
    pass

class IncorrectTypeError(ConfigurationError):
    pass

class ConstraintViolationError(ConfigurationError):
    pass

class MissingConfigurationFileError(ConfigurationError):
    pass


_YAML_NULL = "null"

# The configuration cache. This is were loaded configuration values are stored
_cache = {}

class TypeLoader:

    EMPTY_VALUE = _YAML_NULL

    IS_CONTAINER = False

    def __init__(self, value=None, default_val=None, required=True,
                 allow_empty=False, sensitive=False):
        self.required = required
        self.allow_empty = allow_empty
        self.sensitive = sensitive
        self.default = default_val

        self.value = default_val if not value else value

    @property
    def yaml_value(self):
        if self.value is None:
            return self.EMPTY_VALUE
        return self.value

    @property
    def usable_value(self):
        return self.value

    def is_empty(self, value):
        return value is None

    def parse(self, value):
        """Parse raw value to value of desired type and return.
        Return None if value is None. If incorrect type,
        raise IncorrectTypeError"""
        raise NotImplementedError

    def constraints(self, value):
        """The constraints for this type. Must raise a
        ConstraintViolationError is constraint is violated."""
        raise NotImplementedError

    def check_constraints(self, value):
        """Verify the the type is empty and potential constraints """
        if self.is_empty(value):
            if self.allow_empty:
                return

            raise MissingValueError()

        self.constraints(value)

class String(TypeLoader):
    def is_empty(self, value):
        return value is None or value == ""

    def parse(self, value):
        if value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        return value.strip()

    def constraints(self, value):
        if not isinstance(value, str):
            raise IncorrectTypeError(
                f"Expected type string, got {type(value).__name__}"
            )

class Int(TypeLoader):

    def __init__(self, value=None, default_val=None, required=True,
                 allow_empty=False, sensitive=False, min_value=None,
                 max_value=None):
        self.min_value = min_value
        self.max_value = max_value

        super().__init__(value=value, default_val=default_val,
                         required=required, allow_empty=allow_empty,
                         sensitive=sensitive)

    def parse(self, value):
        if value is None:
            return None

        if isinstance(value, int):
            return value

        try:
            return int(value)
        except (ValueError, TypeError):
            raise IncorrectTypeError(
                f"Expected type integer, got {type(value).__name__}"
            )

    def constraints(self, value):
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise IncorrectTypeError(
                f"Expected type integer, got {type(value).__name__}"
            )

        if self.min_value and value < self.min_value:
            raise ConstraintViolationError(
                f"Value {value} is lower than minimum value "
                f"of {self.min_value}"
            )
        if self.max_value and value > self.max_value:
            raise ConstraintViolationError(
                f"Value {value} is larger than maximum value "
                f"of {self.max_value}"
            )

class FilePath(String):

    def __init__(self, value=None, default_val=None, required=True,
                 allow_empty=False, sensitive=False, must_exist=False,
                 readable=False, writable=False):
        self.must_exist = must_exist
        self.readable = readable
        self.writable = writable

        super().__init__(value=value, default_val=default_val,
                         required=required, allow_empty=allow_empty,
                         sensitive=sensitive)

    def constraints(self, value):
        super().constraints(value)

        if self.must_exist and not os.path.isfile(value):
            raise ConstraintViolationError(
                f"Filepath {value} does not exist or is not a file."
            )

        if self.readable and not os.access(value, os.R_OK):
            raise ConstraintViolationError(f"Filepath {value} is not readable")

        if self.writable and not os.access(value, os.W_OK):
            raise ConstraintViolationError(f"Filepath {value} is not writable")

class Boolean(TypeLoader):

    def parse(self, value):
        try:
            return parse_bool(value)
        except (ValueError, TypeError):
            raise IncorrectTypeError(
                f"Expected type boolean, got {type(value).__name__}"
            )

    def constraints(self, value):
        try:
            parse_bool(value)
        except (ValueError, TypeError):
            raise IncorrectTypeError(
                f"Expected type boolean, got {type(value).__name__}"
            )

class HTTPUrl(String):

    def constraints(self, value):
        super().constraints(value)

        if not value.lower().startswith(("http://", "https://")):
            raise ConstraintViolationError(
                "HTTP url must start with http:// or https://"
            )

class List(TypeLoader):

    IS_CONTAINER = True

    def __init__(self, element_class, value=None, default_val=None,
                 required=True, allow_empty=False):
        self.element_class = element_class

        super().__init__(value=value, default_val=default_val,
                         required=required, allow_empty=allow_empty)

    @property
    def usable_value(self):
        if self.is_empty(self.value):
            return []

        return [
            val.usable_value if isinstance(val, TypeLoader)
            else val for val in self.value
        ]

    def is_empty(self, value):
        return not value or value is None

    def parse(self, value):
        if value is None:
            return None

        if isinstance(value, str):
            loader = self.element_class(value=value)
            parsed = loader.parse(value)
            loader.value = parsed
            return [loader]

        if isinstance(value, list):
            elements = []
            for item in value:
                if not item:
                    continue

                loader = self.element_class(value=item)
                parsed = loader.parse(item)
                loader.value = parsed

                elements.append(loader)

            return elements

        raise IncorrectTypeError(
            f"Expected type list, got {type(value).__name__}"
        )

    def constraints(self, value):
        if not isinstance(value, list):
            raise IncorrectTypeError(
                f"Expected type list, got {type(value).__name__}"
            )

        for element in value:
            element.check_constraints(element.value)

class Dict(TypeLoader):

    def __init__(self, element_class, value=None, default_val=None,
                 required=True, allow_empty=False):

        self.element_class = element_class

        super().__init__(value=value, default_val=default_val,
                         required=required, allow_empty=allow_empty)

    @property
    def usable_value(self):
        if self.is_empty(self.value):
            return {}

        return self.value

    def is_empty(self, value):
        return not value or value is None

    def parse(self, value):
        if value is None:
            return None

        if not isinstance(value, dict):
            raise IncorrectTypeError(
                f"Expected type dict, got {type(value).__name__}"
            )

        # If the given typeloader is also a container, it must be a class
        # instance instead of a class, as to pass its typeloader to it.
        # Create the dictionary values using the given element class
        # and its element class
        kv = {}
        if self.element_class.IS_CONTAINER:
            element_class = self.element_class.__class__
            container_content_class = self.element_class.element_class

            for k, v in value.items():
                loader = element_class(container_content_class, v)
                parsed = loader.parse(v)
                loader.value = parsed
                kv[k] = loader

            return kv

        for k, v in value.items():
            loader = self.element_class(v)
            parsed = loader.parse(v)
            loader.value = parsed
            kv[k] = loader

        return kv

    def constraints(self, value):
        if not isinstance(value, dict):
            raise IncorrectTypeError(
                f"Expected type dict, got {type(value).__name__}"
            )


class DictList(TypeLoader):

    def __init__(self, child_typeloaders, value=None, default_val=None,
                 required=True, allow_empty=False):
        self.child_typeloaders = child_typeloaders

        super().__init__(value=value, default_val=default_val,
                         required=required, allow_empty=allow_empty)

    @property
    def usable_value(self):
        if self.is_empty(self.value):
            return []

        return self.value

    def is_empty(self, value):
        return not value or value is None

    def parse(self, value):
        if not isinstance(value, list):
            raise IncorrectTypeError(
                f"Expected type list, got {type(value).__name__}"
            )

        dict_list = []
        for entry in value:
            if not isinstance(entry, dict):
                raise IncorrectTypeError(
                    f"Entry in dictionary list must be type dict, "
                    f"got {type(value).__name__}"
                )

            dict_entry = {}
            for k, v in entry.items():
                typeloader = self.child_typeloaders.get(k)
                if not typeloader:
                    continue

                dict_entry[k] = typeloader.__class__(value=v)

            dict_list.append(dict_entry)

        return dict_list

    def constraints(self, value):
        if not isinstance(value, list):
            raise IncorrectTypeError(
                f"Expected type list, got {type(value).__name__}"
            )

        for entry in value:
            if not isinstance(entry, dict):
                raise IncorrectTypeError(
                    f"Entry in dictionary list must be type dict, "
                    f"got {type(value).__name__}"
                )

            for k, v in entry.items():
                typeloader = self.child_typeloaders.get(k)
                if not typeloader:
                    continue

                typeloader.check_constraints(v.value)


class NestedDictionary:

    def __init__(self, parentkey, child_typeloaders, required=True):

        self.parentkey = parentkey
        self.child_typeloaders = child_typeloaders
        self.required = required
        self.default = child_typeloaders
        self.value = {}

    @property
    def yaml_value(self):
        if not self.value:
            return {
                self.parentkey: self.child_typeloaders
            }

        return self.value

    @property
    def usable_value(self):
        return self.value

    def make_typeloaders(self, conf_values):
        if not conf_values:
            raise MissingValueError()

        typeloaders = {}
        # Create a copy of the typeloaders dict for each section in the
        # configuration, so that its values can be read and verified.
        for section, values in conf_values.items():
            typeloaders[section] = deepcopy(self.child_typeloaders)
        return typeloaders

def platformconditional(default, **kwargs):
    plat = platform.system().lower()
    plat_val = kwargs.get(plat)
    if plat_val:
        return plat_val
    return default

def typeloaders_to_templatedict(config_dictionary, filter_sensitive=True):
    def _typeloader_to_yamlval(obj):
        if isinstance(obj, set):
            raise ConfigurationError(
                "Configuration value object cannot be a set"
            )

        if isinstance(obj, TypeLoader):
            if obj.sensitive and filter_sensitive:
                return "*"*8

            return obj.yaml_value

        elif isinstance(obj, NestedDictionary):
            return obj.yaml_value

        return obj

    # HACKY: A bit hacky.. But works well enough for now.
    return json.loads(
        json.dumps(config_dictionary, default=_typeloader_to_yamlval)
    )

def render_config(template_path, typeloaders, write_to):
    if os.path.exists(write_to):
        raise ConfigurationError(f"Path {write_to} exists")

    if not os.path.isfile(template_path):
        raise ConfigurationError(
            f"Configuration template path: {template_path} does not exist"
        )

    values = typeloaders_to_templatedict(typeloaders, filter_sensitive=False)

    import jinja2
    with open(template_path, "r") as fp:
        template = jinja2.Template(
            fp.read(), lstrip_blocks=True, trim_blocks=True
        )

    rendered = template.render(values)
    with open(write_to, "w") as fp:
        fp.write(rendered)

def cfg(file, *args, subpkg="", load_missing=False):
    """Read the specified config args from cache of file of (optional)subpkg.
    Load missing loads a configuration file if not present in the cache"""
    if not file.endswith(".yaml"):
        file = f"{file}.yaml"

    if subpkg:
        cached_pkg = _cache.get(subpkg, {})
        file_values = cached_pkg.get(file)
    else:
        file_values = _cache.get(file)

    if not file_values:
        if not load_missing:
            raise ConfigurationError(
                f"Configuration file {file} is not loaded. "
                f"Cannot read values from it."
            )

        from .storage import Paths
        load_config(Paths.config(file=file, subpkg=subpkg), subpkg=subpkg)
        return cfg(file, *args, subpkg=subpkg)

    if not args:
        return file_values

    val = None
    for k in args:
        try:
            if val:
                val = val[k]
            else:
                val = file_values[k]
        except (KeyError, TypeError):
            raise ConfigurationError(
                f"Configuration file {file} "
                f"{f'in package folder {subpkg}' if subpkg else ''} "
                f"does not have configuration key {k}."
            )

    if isinstance(val, TypeLoader):
        return val.usable_value

    return val

def _dump_to_cache(loaded_values, filename, subpkg):
    def _typeloader_to_val(obj):
        if isinstance(obj, (TypeLoader, NestedDictionary)):
            return obj.usable_value

        return obj

    # HACKY: A bit hacky.. But works well enough for now.
    values_dict = json.loads(
        json.dumps(loaded_values, default=_typeloader_to_val)
    )

    if subpkg:
        if subpkg not in _cache:
            _cache[subpkg] = {}

        _cache[subpkg][filename] = values_dict

    else:
        _cache[filename] = values_dict

def load_config(filepath, subpkg="", cache_config=True):
    if not os.path.isfile(filepath):
        raise MissingConfigurationFileError(
            f"Configuration file {filepath} not found."
        )

    if subpkg:
        pkgname = f"cuckoo.{subpkg}"
    else:
        pkgname = "cuckoo"

    from importlib import import_module
    try:
        cuckoopkg = import_module(pkgname)
    except ModuleNotFoundError:
        raise ConfigurationError(
            f"Cannot read configuration from non-existing package: {pkgname}"
        )

    from .packages import get_conf_typeloaders
    loaders, _ = get_conf_typeloaders(cuckoopkg)

    filename = os.path.basename(filepath)
    loader = loaders.get(filename)
    if not loader:
        raise ConfigurationError(
            f"Unknown configuration file {filename}. "
            f"Cannot load configuration as no type loaders are available. "
            f"Loaders are available for: {loaders.keys()}"
        )

    with open(filepath, "r") as fp:
        try:
            conf = yaml.safe_load(fp)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {filepath}. {e}")

    # Copy the typeloaders are we do not want to overwrite values of the
    # original.
    loadercopy = deepcopy(loader)

    try:
        load_values(conf, loadercopy, check_constraints=True)
    except ConfigurationError as e:
        raise ConfigurationError(
            f"Error in config file: {filepath}. {e}"
        )

    # Assign the loaded values under the subpkg key and filename in the cache
    if cache_config:
        _dump_to_cache(loadercopy, filename, subpkg)

    return loadercopy

def load_values(conf_data_dict, type_loader_dict, check_constraints=True):
    if not isinstance(conf_data_dict, dict):
        raise ConfigurationError(
            f"Currently, only key value configurations are supported. "
            f"Can't load {conf_data_dict}"
        )

    # If the enabled key is present and false, we do not need to check the
    # constraints that belong to that section.
    if "enabled" in conf_data_dict:
        if not Boolean(value=conf_data_dict["enabled"]).value:
            check_constraints = False

    for key, loader in type_loader_dict.items():

        if key not in conf_data_dict:

            # Stop reading the configuration if the missing key is
            # marked as required
            if isinstance(loader, (TypeLoader, NestedDictionary)):
                if not loader.required:
                    continue

                raise ConfigurationIncompleteError(
                    f"Missing required key {key}"
                )

            raise ConfigurationIncompleteError(
                f"Missing configuration section: {key}"
            )

        confval = conf_data_dict[key]

        # If the loader for the current key is a NestedDictionary, it contains
        # an unknown number of key->dictionary pairs. Use the NestedDictionary
        # instance to make a typeloader dictionary for each key->dictionary.
        # Lastly, re-run load_values so that all values in each dict are
        # properly type checked and loaded. If it passes, assign its value
        # to the NestedDictionary so it can be read later.
        if isinstance(loader, NestedDictionary):
            try:
                nested_loaders = loader.make_typeloaders(confval)
            except MissingValueError as e:
                raise ConfigurationError(
                    f"Key '{key}' cannot be empty. {e}",
                )

            load_values(confval, nested_loaders)
            loader.value = nested_loaders
            continue

        # We cannot check constraints of any else than a typeloader. Re-run
        # load_values on the current configuration values and value of loader
        if not isinstance(loader, TypeLoader):
            load_values(confval, loader, check_constraints)
            continue

        # Let the typeloader 'parse' the value to whatever the format of the
        # value should be and check its constraints with that parsed value.
        try:
            parsed = loader.parse(confval)
            if check_constraints:
                loader.check_constraints(parsed)
        except ConstraintViolationError as e:
            raise ConfigurationError(
                f"Constraint violation for key {key}: {e}"
            )
        except MissingValueError as e:
            raise ConfigurationError(
                f"Key '{key}' cannot be empty. {e}",
            )
        except IncorrectTypeError as e:
            raise ConfigurationError(
                f"Value of key '{key}' has an incorrect type. {e}"
            )

        loader.value = parsed
