# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import datetime
import dateutil.parser
import json

def deserialize_disk_json(obj):
    if "__isodt__" in obj:
        try:
            return dateutil.parser.parse(obj["__isodt__"])
        except (ValueError, OverflowError) as e:
            raise json.decoder.JSONDecodeError(
                "Failed to decode ISO format datetime: {e}"
            ).with_traceback(e.__traceback__)
    return obj

def serialize_disk_json(obj):
    if isinstance(obj, bytes):
        return obj.decode()
    if isinstance(obj, datetime.datetime):
        return {"__isodt__": obj.isoformat()}
    return obj

def serialize_api_json(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    return obj


class StrictContainer:

    FIELDS = {}
    ALLOW_EMPTY = ("")
    PARENT_KEYVAL = ("", "")

    def __init__(self, **kwargs):
        if kwargs:
            self.loaded = kwargs
            self._load()
        else:
            self.loaded = {}

    def _verify_keys(self):
        missing = []
        for key in self.FIELDS:
            if key not in self.loaded:
                if key not in self.ALLOW_EMPTY:
                    missing.append(key)
                else:
                    # Create the key and empty value of the type of the
                    # missing key. If the expected type is one or more
                    # StrictContainers, initialize the key with an empty dict
                    expected_type = self.FIELDS[key]

                    if isinstance(expected_type, tuple):
                        self.loaded[key] = {}
                    elif issubclass(expected_type, StrictContainer):
                        self.loaded[key] = {}
                    else:
                        self.loaded[key]= self.FIELDS[key]()

        if missing:
            raise KeyError(f"{', '.join(missing)}")

    def _verify_key_types(self):
        errors = []
        for key, expected_type in self.FIELDS.items():
            type_instance = self.loaded[key]

            # If the expected type is a Cuckoo JSON file or tuple
            # (multiple possible Cuckoo JSON files), set the type to verify to
            # a dict, as the type should still currently be a dict as we have
            # not created its expected type object yet.
            if not isinstance(type_instance, expected_type):
                if isinstance(expected_type, tuple):
                    expected_type = dict
                elif issubclass(expected_type, StrictContainer):
                    expected_type = dict

            if not isinstance(type_instance, expected_type):
                errors.append(
                    f"Value of key '{key}' must be {expected_type}. "
                    f"Found {type_instance.__class__.__name__}"
                )

        if errors:
            print(self.loaded)
            raise TypeError(f"{', '.join(errors)}")

    def _create_child_type(self, child_type, key):
        try:
            self.loaded[key] = child_type(**self.loaded[key])
        except KeyError as e:
            raise KeyError(
                f"Key '{key}' is missing subkeys: {e}"
            ).with_traceback(e.__traceback__)
        except TypeError as e:
            raise TypeError(
                f"Key '{key}' has subkeys with invalid values: {e}"
            ).with_traceback(e.__traceback__)

    def _create_child_types(self):
        # For each expected type we have, verify if it is another Cuckoo JSON
        # file type. If it is, create an instance of it using the dictionary
        # with data that currently resides in its key. Replace the dict with
        # the type instance. Do the same for all its children
        for key, expected_type in self.FIELDS.items():
            type_instance = self.loaded[key]

            # If the value is already an instance of the type, skip it.
            if isinstance(type_instance, expected_type):
                continue

            # If a key is and is allowed to be empty, skip it.
            if not type_instance and key in self.ALLOW_EMPTY:
                continue

            # If a key can have more than 1 type, it must be in a tuple. If
            # a field can have more than 1 type, these types must specify
            # the key and value that decide what type must be chosen in their
            # PARENT_KEYVAL attribute.
            if isinstance(expected_type, tuple):
                for type_entry in expected_type:
                    if issubclass(type_entry, StrictContainer):

                        # Find the value of the key specified by this potential
                        # child key type. If it matches, choose this type class
                        parent_key, parent_val = type_entry.PARENT_KEYVAL
                        if self.loaded[parent_key] == parent_val:
                            self._create_child_type(type_entry, key)

            elif issubclass(expected_type, StrictContainer):
                self._create_child_type(expected_type, key)

    def _load(self):
        # First verify if all keys exist
        self._verify_keys()
        # Verify if all types are the expected type
        self._verify_key_types()
        # Load al CuckooJSONFile subtypes
        self._create_child_types()

    @classmethod
    def from_file(cls, filepath):
        try:
            with open(filepath, "r") as fp:
                loaded = json.load(
                    fp, object_hook=deserialize_disk_json
                )
        except json.decoder.JSONDecodeError as e:
            raise ValueError(f"JSON decoding error: {e}")

        return cls(**loaded)

    def check_constraints(self):
        pass

    def to_dict(self):
        return {
            k: v.to_dict() if isinstance(v, StrictContainer) else v for k, v in
            self.loaded.items()
        }

    def to_api_json(self):
        return json.dumps(self.to_dict(), default=serialize_api_json)

    def to_file(self, path):
        with open(path, "w") as fp:
            json.dump(self.to_dict(), fp, default=serialize_disk_json)

    def __getattr__(self, item):
        try:
            return self.loaded[item]
        except KeyError:
            raise AttributeError(
                f"type object '{self.__class__.__name__}' has no attribute "
                f"'{item}'"
            )


class Settings(StrictContainer):

    FIELDS = {
        "timeout": int,
        "enforce_timeout": bool,
        "dump_memory": bool,
        "priority": int,
        "options": dict,
        "machine_tags": list,
        "platforms": list,
        "machines": list,
        "manual": bool
    }

class SubmittedFile(StrictContainer):

    # Look at the parent dict and find the category key. Use this class if
    # the value is 'file'
    PARENT_KEYVAL = ("category", "file")
    FIELDS = {
        "filename": str,
        "size": int,
        "md5": str,
        "sha1": str,
        "sha256": str,
        "media_type": str,
        "type": str,
        "category": str
    }

class SubmittedURL(StrictContainer):

    # Look at the parent dict and find the category key. Use this class if
    # the value is 'file'
    PARENT_KEYVAL = ("category", "url")
    FIELDS = {
        "url": str,
        "category": str
    }

class Analysis(StrictContainer):

    FIELDS = {
        "id": str,
        "settings": Settings,
        "created_on": datetime.datetime,
        "category": str,
        "submitted": (SubmittedFile, SubmittedURL)
    }


class Errors(StrictContainer):

    FIELDS = {
        "errors": list,
        "fatal": dict
    }

class TargetFile(StrictContainer):

    PARENT_KEYVAL = ("category", "file")
    FIELDS = {
        "filename": str,
        "platform": str,
        "size": int,
        "filetype": str,
        "media_type": str,
        "sha256": str,
        "extrpath": list,
        "container": bool
    }
    ALLOW_EMPTY = ("extrpath",)

class TargetURL(StrictContainer):

    PARENT_KEYVAL = ("category", "url")

class Identification(StrictContainer):

    FIELDS = {
        "selected": bool,
        "target": (TargetFile, TargetURL),
        "category": str,
        "ignored": list,
        "parent": str,
        "errors": Errors
    }
    ALLOW_EMPTY = ("target", "parent", "ignored")
