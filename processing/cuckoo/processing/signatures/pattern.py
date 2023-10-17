# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import re
import hyperscan
import yaml

from cuckoo.common.strictcontainer import StrictContainer

from cuckoo.processing.signatures.signature import Levels

class PatternSignatureError(Exception):
    pass

# The flags used for each pattern that is added to a hyperscan database.
_PATTERN_HYPERSCAN_FLAGS = hyperscan.HS_FLAG_CASELESS | \
                           hyperscan.HS_FLAG_DOTALL | \
                           hyperscan.HS_FLAG_SINGLEMATCH
# The flags used for regexes that make up a safelist entry. Python re is
# used for this.
_SAFELIST_PYREGEX_FLAGS = re.IGNORECASE | re.DOTALL

class _LoadedPatternTypes:

    REGEX = "regex"
    INDICATOR = "indicator"

class LoadedPattern:
    """A LoadedPattern represents one regex from a trigger of a signature.
    an event must match the regex it has for a specific type of event,
    such as a file or registry write.
    E.G: 'file write: c:\\windows\\system32\\*\.exe'"""

    TYPE = _LoadedPatternTypes.REGEX

    def __init__(self, regex, pattern_id, eventkind, subtype=None):
        self.id = pattern_id
        self.regex = regex
        self.eventkind = eventkind
        self.subtype = subtype

    def __str__(self):
        return f"<id={self.id}, eventkind={self.eventkind}, " \
               f"regex={self.regex}>"

    def __repr__(self):
        return str(self)

class LoadedIndicatorPattern:
    """A LoadedIndicatorPattern represents the definition or usage of the
    'indicator' keyword in a trigger. An indicator is a labeled list of
    triggers that can be referenced from signature triggers or other
    indicators."""

    TYPE = _LoadedPatternTypes.INDICATOR

    def __init__(self, pattern_id, name):
        self.id = pattern_id
        self.name = name
        self.triggers = set()

    def __str__(self):
        return f"<id={self.id}, name={self.name}>"

    def __repr__(self):
        return str(self)

class TriggerSafelist:

    def __init__(self):
        self._images = set()
        self._eventkind_regex = {}

    def add_image(self, image_path):
        # Store lower case version of image path. It will be compared
        # To a normalized version of an image path, which will also be
        # lower case.
        self._images.add(image_path.lower())

    def add_regex(self, regex, eventkind, subtype=None):
        if subtype:
            key = f"{eventkind} {subtype}"
        else:
            key = eventkind

        if not isinstance(regex, bytes):
            regex = regex.encode()

        try:
            regex = re.compile(regex, _SAFELIST_PYREGEX_FLAGS)
        except re.error as e:
            raise PatternSignatureError(
                f"Failed to compile safelist regex: {regex!r}. Error: {e}"
            )

        self._eventkind_regex.setdefault(key, []).append(regex)

    def _matches_regexes(self, value, kind, subtypes=[]):
        # TODO think of a more clean way to do this. Most values are
        # strings, used regexes are loaded as bytes.
        if isinstance(value, str):
            # Ignore decoding errors for now.
            value = value.encode(errors="ignore")

        for regex in self._eventkind_regex.get(kind, []):
            if regex.match(value):
                return True

        if not subtypes:
            return False

        for subtype in subtypes:
            kind_subtype = f"{kind} {subtype}"
            for regex in self._eventkind_regex.get(kind_subtype, []):
                if regex.match(value):
                    return True

        return False

    def should_ignore(self, matchctx):
        if not self._eventkind_regex and not self._images:
            return False

        if self._images and matchctx.processing_ctx and matchctx.event:
            process = matchctx.processing_ctx.process_tracker.lookup_process(
                matchctx.event.procid
            )
            # If the process image is safelisted, but it has been injected,
            # ignore the safelist entry for this image.
            if process.injected:
                return False

            if process.normalized_image in self._images:
                return True

        for value_subtypes in matchctx.extra_safelistdata:
            if len(value_subtypes) < 2:
                value, subtypes = value_subtypes[0], None
            else:
                value, subtypes = value_subtypes

            if self._matches_regexes(value, matchctx.kind, subtypes):
                return True

        return self._matches_regexes(
            matchctx.matched_str, matchctx.kind, [matchctx.subtype]
        )


def _check_trigger(pattern_dict):
    if not isinstance(pattern_dict, dict):
        raise TypeError(
            "Triggers and safelists must be dictionaries. "
            f"Value {pattern_dict!r} is of type {type(pattern_dict)}"
        )

    for event_type, vals in pattern_dict.items():
        if not isinstance(event_type, str):
            raise TypeError(
                "Event type must be a string. Event type "
                f"{event_type!r} is {type(event_type)}"
            )

        if event_type == "safelist":
            _check_trigger(vals)
            continue

        invalid = False
        if isinstance(vals, str):
            continue
        if isinstance(vals, list):
            for val in vals:
                if not isinstance(val, str):
                    invalid = True
                    vals = val
                    break
        else:
            invalid = True

        if not invalid:
            continue

        raise PatternSignatureError(
            "The values of a trigger and safelist entries must be a "
            f"list of strings or a single string. "
            f"Entry: {event_type!r} with value {vals!r} is of "
            f"type: {type(vals)}"
        )

class LoadedSignature(StrictContainer):

    FIELDS = {
        "name": str,
        "short_description": str,
        "description": str,
        "family": str,
        "level": str,
        "score": int,
        "tags": list,
        "ttps": list,
        "triggers": list
    }
    ALLOW_EMPTY = ("tags", "ttps", "family", "level", "description")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not self.level:
            self.level = Levels.INFORMATIONAL
        if not self.description:
            self.description = self.short_description

    def check_constraints(self):
        for trigger in self.triggers:
            _check_trigger(trigger)

def _check_indicatorsdict(indicatorsdict):
    if not isinstance(indicatorsdict, dict):
        raise TypeError(
            "Indicators must be a dictionary of name keys"
        )

    for key, indicatordict in indicatorsdict.items():
        if not isinstance(indicatordict, dict):
            raise TypeError(
                f"Invalid indicator: {key!r}. Got a non-dictionary value. "
                "Expected a dictionary with a 'triggers' key.\n"
                "Each indicators entry must consist of name key, that has a "
                "triggers key. The triggers key must contain one or more "
                "'eventtype:valueslist' dictionaries"
                f"\n\nGot: {type(indicatordict)}. "
                f"Value: {indicatordict!r}"
            )

        triggers = indicatordict.get("triggers")
        if not triggers:
            raise KeyError(
                f"Missing 'triggers' dictionary list for indicator {key!r}"
            )

        if not isinstance(triggers, list):
            raise TypeError(
                "The value of 'triggers' must be a list of dictionaries. "
                f"Got {type(triggers)}. Values: {triggers!r}"
            )

        for trigger in triggers:
            _check_trigger(trigger)


class LoadedSignatures:
    """Used to load the signatures and indicators from signature files.
    The triggers and their patterns all get their own numeric IDs.

    Hyperscan returns the matched pattern id of a pattern. The PatternScanner
    uses this id to find the correlating pattern in LoadedSignatures.

    The SigMatchTracker then uses this ID to find out type and subtype
    (file, reg, etc) pattern it is and to what signatures it belongs to.

    LoadedSignatures holds all the mappings of the pattern/indicatorpattern,
    trigger, and signature ids to each other.

    A trigger is a group of one or more regexes for a specific kind of event.
    If all regexes in a trigger match, this causes the signature or indicator
    it is part of to be matched.

    A LoadedPattern represents one regex from a trigger of a signature.
    an event must match the regex it has for a specific type of event,
    such as a file or registry write.
    E.G: 'file write: c:\\windows\\system32\\*\.exe'

    A LoadedIndicatorPattern represents the definition or usage of the
    'indicator' keyword in a trigger. An indicator is a labeled list of
    triggers that can be referenced from signature triggers or other
    indicators."""

    def __init__(self):

        # Used to find out what signatures a specific pattern belongs to
        self.pattern_id_sigids = {}
        # Used to find what patterns a specific trigger has.
        self.trigger_id_pattern_ids = {}
        # Used to find triggers a pattern belongs to. Used for quick lookups
        # to find safelisting entries mapped for a trigger.
        self.pattern_id_trigger_id = {}
        # Used to find out what triggers belong to a signature
        self.signature_id_trigger_ids = {}
        # Used to retrieve information about a signature, to be able to
        # create an object that tracks its matches.
        self.sigid_siginfo = {}

        # Used to perform lookups to find the LoadedPattern or
        # LoadedIndicatorPattern object.
        self.pattern_id_pattern = {}

        # Similar to signature_id_trigger_ids, it is used to find out
        # what triggers belong to a specific indicator.
        self.indicator_id_trigger_ids = {}

        # A mapping of pattern ids and the patterns that reference them.
        self.pattern_id_indicator = {}

        # A mapping of trigger ids to TriggerSafelist objects. Used to check
        # if a matched pattern should be ignore for the trigger it is mapped
        # to.
        self.trigger_id_safelist = {}
        
        self.name_indicator = {}

        self._pattern_count = 0

    def _make_pattern_id(self):
        self._pattern_count += 1
        return self._pattern_count

    def _find_pattern(self, regex, eventkind):
        """Searches for a pattern with the given regex and eventkind"""
        for pattern in self.pattern_id_pattern.values():
            if pattern.TYPE != _LoadedPatternTypes.REGEX:
                continue

            if pattern.eventkind != eventkind:
                continue

            if pattern.regex == regex:
                return pattern

        return None

    def _get_pattern(self, regex, eventkind, subtype=None):
        """Create a new pattern or retrieve an existing pattern"""
        # Find an existing pattern with the same regex for the same type
        # of event.
        loaded_pattern = self._find_pattern(regex, eventkind)
        if loaded_pattern:
            return loaded_pattern

        loaded_pattern = LoadedPattern(
            regex, self._make_pattern_id(), eventkind, subtype=subtype
        )

        # Add the loaded pattern to others of the same event kind and by id.
        # These are used to compile a per kind scandb. The id->pattern mapping
        # is used to retrieve the pattern if it matches.

        # Map the loaded pattern object to its id so it can be retrieved later.
        # This is also used to compile the hyperscan databases for each event
        # kind.
        self.pattern_id_pattern[loaded_pattern.id] = loaded_pattern

        return loaded_pattern

    def _get_indicator_pattern(self, indicator_name):
        """Finds an existing or creates a new LoadedIndicatorPattern
        for the given name and returns it."""
        if not self._indicator_exists(indicator_name):
            self._create_indicator_pattern(indicator_name)

        return self.name_indicator[indicator_name]

    def _read_trigger(self, trigger_dict):
        for entry, values in trigger_dict.items():
            if isinstance(values, str):
                values = [values]

            # Split the event to match in an event and subtype. Example:
            # 'file read' to 'file' and subtype 'read'.
            kind_subtype = tuple(filter(None, entry.split(" ", 1)))
            if len(kind_subtype) > 1:
                event_kind, subtype = kind_subtype
            else:
                event_kind, subtype = kind_subtype[0], None

            yield event_kind, subtype, values

    def _create_safelist(self, safelist_dict):
        safelist = TriggerSafelist()
        images = safelist_dict.pop("images", [])
        if images:
            if not isinstance(images, (list, str)):
                raise ValueError(
                    "Safelist images must be a list of string image paths"
                )

            if not isinstance(images, list):
                images = [images]

            for path in images:
                safelist.add_image(path)

        for eventkind, subtype, regexes in self._read_trigger(safelist_dict):
            for regex in regexes:
                safelist.add_regex(regex, eventkind, subtype=subtype)

        return safelist

    def _create_trigger(self, trigger_dict):
        """Create a new trigger from a trigger dictionary read from a
        signature dictionary"""
        trigger_id = len(self.trigger_id_pattern_ids) + 1
        pattern_ids = set()

        # A trigger consists of one or more 'events' to match. Each of these
        # events can contain one or more entries to match. Events can be
        # of many types, including 'indicators', which are basically a labeled
        # trigger that is not part of a signature.

        # Each trigger can contain one 'safelist' key. This is a collection
        # of events and regexes, like a trigger, but is used to ignore an
        # event if it matches a pattern in the trigger.
        safelist = None
        for event_kind, subtype, patterns in self._read_trigger(trigger_dict):
            # Get pattern ids for the patterns within this trigger.
            # A list of one or more patterns.
            for entry in patterns:
                if event_kind == "indicator":
                    p = self._get_indicator_pattern(entry)
                elif event_kind == "safelist":
                    # Set the safelist for this trigger and continue without
                    # adding any pattern IDs.
                    safelist = self._create_safelist(patterns)
                    break
                else:
                    p = self._get_pattern(
                        entry, event_kind, subtype=subtype
                    )

                pattern_ids.add(p.id)

        # Map all pattern ids to this new trigger id. This is later used
        # to find what patterns belong to a trigger.
        # Sigid->trigger ids->pattern ids.
        self.trigger_id_pattern_ids[trigger_id] = pattern_ids

        for pattern_id in pattern_ids:
            self.pattern_id_trigger_id.setdefault(pattern_id, set()).add(
                trigger_id
            )

        if safelist:
            self.trigger_id_safelist[trigger_id] = safelist

        return trigger_id, pattern_ids

    def _load_signatures(self, sigsdict):
        for signame, sigdict in sigsdict.items():
            # Use the key of this signature as the name of the signature.
            sigdict["name"] = signame
            sig = LoadedSignature(**sigdict)

            sigid = len(self.sigid_siginfo) + 1
            # A signature can contain multiple triggers and a pattern can
            # exist in multiple triggers over multiple signatures.
            # pattern ids are used to map a signature id to it.
            all_patterns = set()
            all_triggers = set()
            for triggger in sig.triggers:
                trigger_id, pattern_ids = self._create_trigger(triggger)
                all_patterns.update(pattern_ids)
                all_triggers.add(trigger_id)

            # Map each pattern id that is part of this signature to the
            # signature's id. This is later used to find what signatures
            # belong to a matched pattern.
            for pattern_id in all_patterns:
                self.pattern_id_sigids.setdefault(pattern_id, set()).add(sigid)

            # Map the signature id to a set the trigger ids that are part
            # of the signature.
            self.signature_id_trigger_ids[sigid] = all_triggers

            # Map the signature id to the loaded signature.
            # When a pattern is matched, this information is needed to create
            # a specific signature object that tracks all matches and also
            # has the signature name, description, etc.
            self.sigid_siginfo[sigid] = sig

    def _create_indicator_pattern(self, name):
        pattern = LoadedIndicatorPattern(self._make_pattern_id(), name)
        self.name_indicator[name] = pattern
        self.pattern_id_pattern[pattern.id] = pattern

    def _indicator_exists(self, name):
        return name in self.name_indicator

    def _load_indicators(self, indicatorsdict):
        """Load a dictionary of indicators. Indicators can be described
        as a list of triggers with a label. They can globally be used in
        signatures and other indicators."""
        for name, indicatordict in indicatorsdict.items():
            if not isinstance(indicatordict, dict):
                raise ValueError(
                    f"Indicator triggers must be dictionaries. "
                    f"Got {type(indicatordict)}. {indicatordict}."
                )

            triggers = indicatordict.get("triggers")
            if not triggers:
                raise KeyError(
                    f"Missing 'triggers' dictionary list for indicator {name}"
                )

            indicator = self._get_indicator_pattern(name)
            def _find_circular_reference(start_id, needle_id, first_run=True):
                """Search for a path where needle_id is referenced in such
                a way that it again reaches start_id, causing a circular
                reference. Returns bool, and a list of
                referrer->referenced LoadedIndicatorPattern objects"""

                needle_pattern = self.pattern_id_pattern[needle_id]
                # Only indicators can reference.
                if needle_pattern.TYPE != _LoadedPatternTypes.INDICATOR:
                    return False, []

                start_pattern = self.pattern_id_pattern[start_id]
                # This indicator refers to itself.
                if start_id == needle_id:
                    return True, [(start_pattern, needle_pattern)]

                referencers = self.pattern_id_indicator.get(start_id, [])
                path = []

                # Only append the starting patterns once to the path to get an
                # accurate path of the full circular reference.
                if first_run:
                    path.append((start_pattern, needle_pattern))
                    first_run = False

                # The needle id is referencing to start_id
                if needle_id in referencers:
                    path.append((needle_pattern, start_pattern))
                    return True, path

                for indicator_id in referencers:
                    found, retpath = _find_circular_reference(
                        indicator_id, needle_id, first_run
                    )
                    if found:
                        path.extend(retpath)
                        path.append(
                            (self.pattern_id_pattern[indicator_id],
                             start_pattern)
                        )
                        return True, path

                return False, []

            for trigger in triggers:
                trigger_id, pattern_ids = self._create_trigger(trigger)

                for pattern_id in pattern_ids:
                    # Find out if the current pattern will create a
                    # circular reference if it is added to the current
                    # indicator. This can happen as indicators can reference
                    # other indicators.
                    found, path = _find_circular_reference(
                        indicator.id, pattern_id
                    )
                    if found:
                        cause = self.pattern_id_pattern[pattern_id]
                        fmtpath = ', '.join(
                            [f'{p[0].name} -> {p[1].name}' for p in path]
                        )
                        raise PatternSignatureError(
                            f"Circular reference found. Indicator "
                            f"'{cause.name}' in indicator '{name}'. "
                            f"Full path: {fmtpath} -> ..."
                        )

                    # Add the indicator as a referencer of this pattern id.
                    self.pattern_id_indicator.setdefault(
                        pattern_id, set()
                    ).add(indicator.id)

                # Map all loaded triggers ids to this indicator. This
                # information is later used to create pattern and signature
                # objects that keep track of if an indicator fully matched
                # or not.
                self.indicator_id_trigger_ids.setdefault(
                    indicator.id, set()
                ).add(trigger_id)

    def _load_sigfile_dict(self, sigfiledict):
        # Load indicators first, if there are any in this dictionary.
        indicatorsdict = sigfiledict.get("indicators")
        if indicatorsdict:
            _check_indicatorsdict(indicatorsdict)

            self._load_indicators(indicatorsdict)

        sigsdict = sigfiledict.get("signatures")
        if not sigsdict:
            return

        if not isinstance(sigsdict, dict):
            raise TypeError("Signatures must be a dictionary of signatures")

        self._load_signatures(sigsdict)

    def load_from_file(self, file_path):
        """Load a signature YAML file"""
        with open(file_path, "r") as fp:
            try:
                sigfiledict = yaml.safe_load(fp)
            except yaml.YAMLError as e:
                raise PatternSignatureError(f"YAML error: {e}")

        self._load_sigfile_dict(sigfiledict)


class MatchContext:
    """Holds the matched string, original string, and event object that
    caused a pattern to be matched."""

    def __init__(self, matched_str, orig_str, event, kind, processing_ctx,
                 subtype=None, extra_safelistdata=[]):
        self.matched_str = matched_str
        self.orig_str = orig_str
        self.event = event
        self.processing_ctx = processing_ctx

        # Record kind as an event kan have kinds with a different name than
        # the event kind. Such as the process event with the 'commandline'
        # kind
        self.kind = kind
        self.subtype = subtype

        if not extra_safelistdata and not isinstance(extra_safelistdata, list):
            extra_safelistdata = []

        if not isinstance(extra_safelistdata, list):
            self.extra_safelistdata = [extra_safelistdata]
        else:
            self.extra_safelistdata = extra_safelistdata


class PatternMatches:
    """A tracker that contains all matches for a specific pattern id."""

    def __init__(self, pattern_id):
        self.pattern_id = pattern_id
        self.matches = []

    @property
    def matched(self):
        return len(self.matches) > 0

    def add_match(self, matchctx):
        self.matches.append(matchctx)

class IndicatorPattern:
    """Similar to a trigger, but acts like a PatternMatches object. Is used
    to keep track of all triggers that are part of an indicator.

    Indicator patterns are used as if they are patterns and thus have a
    pattern id. They are not regexes and not directly part of a hyperscan db.

    This means we have to 'manually' check if any of its triggers are triggered
    """

    def __init__(self, pattern_id, triggers):
        self.pattern_id = pattern_id
        self.triggers = triggers

    @property
    def matched(self):
        for trigger in self.triggers:
            if trigger.triggered:
                return True

        return False

    @property
    def matches(self):
        iocs = []
        for trigger in self.triggers:
            if trigger.triggered:
                iocs.extend(trigger.get_iocs())

        return iocs


class Trigger:
    """Maps all created PatternMatches/IndicatorPattern objects to a
     trigger id. Used to see if a specific trigger was matched and to
     retrieve the matched events/iocs."""

    def __init__(self, trigger_id, patterns, safelist=None):
        self.trigger_id = trigger_id
        self.patterns = patterns
        self.safelist = safelist
        self._triggered = None
        self._pattern_iocs = []

    def _filter_safelisted_iocs(self, pattern):
        iocs = []
        for match in pattern.matches:
            if not self.safelist.should_ignore(match):
                iocs.append(match)

        return iocs

    @property
    def triggered(self):
        if self._triggered is not None:
            return self._triggered

        all_iocs = []
        for pattern in self.patterns:
            if not pattern.matched:
                self._triggered = False
                break

            if self.safelist:

                # Filter out matches that are safelisted. If any are left,
                # the pattern was still matched.
                iocs = self._filter_safelisted_iocs(pattern)
                if not iocs:
                    self._triggered = False
                    break
                all_iocs.extend(iocs)
            else:
                # No safelist, use all matches.
                all_iocs.extend(pattern.matches)

            self._triggered = True
            self._pattern_iocs = all_iocs

        return self._triggered

    def get_iocs(self):
        if not self.triggered:
            return []

        return self._pattern_iocs

class Signature:
    """Maps all Trigger objects to itself. Should be created with information
    from LoadedSignature objects. There is minimal difference between these,
    except that this object keeps check if its triggers are triggered
    and can retrieve what events triggered them."""

    def __init__(self, triggers, name, short_description, description, score,
                 family="", tags=[], ttps=[]):

        self.triggers = triggers
        self.name = name
        self.short_description = short_description
        self.description = description
        self.score = score
        self.family = family
        self.tags = tags
        self.ttps = ttps

    @property
    def matched(self):
        for trigger in self.triggers:
            if trigger.triggered:
                return True

        return False

    def get_iocs(self):
        iocs = []
        for trigger in self.triggers:
            if trigger.triggered:
                iocs.extend(trigger.get_iocs())

        return iocs

    def __str__(self):
        return f"<name={self.name}, tags={self.tags}, " \
               f"short_description={self.short_description}>"

    def __repr__(self):
        return str(self)

class SigMatchTracker:
    """This is meant as a context object tracks each matched pattern.
    When a pattern matches, it looks up what triggers and signatures it
    belongs to and creates the Signature, Trigger, and
    (Indicator)PatternMatches objects needed to keep track of (partially)
    matched signatures."""

    def __init__(self, loaded_signatures):
        # A LoadedSignatures object used to find all loaded signatures,
        # triggers, patterns that are needed when a hyperscan pattern matches
        self.loaded_sigs = loaded_signatures

        # A mapping of pattern ids to PatternMatches objects.
        self.pattern_id_pattern = {}
        self.trigger_id_trigger = {}
        self.sigid_sig = {}

    def _is_indicator(self, pattern_id):
        return pattern_id in self.loaded_sigs.indicator_id_trigger_ids

    def _pattern_exists(self, pattern_id):
        return pattern_id in self.pattern_id_pattern

    def _create_pattern(self, pattern_id):
        pattern = PatternMatches(pattern_id)
        self.pattern_id_pattern[pattern_id] = pattern
        return pattern

    def _get_pattern(self, pattern_id):
        if self._pattern_exists(pattern_id):
            return self.pattern_id_pattern[pattern_id]

        if self._is_indicator(pattern_id):
            pattern = self._create_indicator(pattern_id)
        else:
            pattern = self._create_pattern(pattern_id)

        return pattern

    def _create_triggers(self, trigger_ids):
        """Creates the trigger objects and the PatternMatches or
        IndicatorPattern objects that belong to it."""
        triggers = []
        for trigger_id in trigger_ids:
            pattern_ids = self.loaded_sigs.trigger_id_pattern_ids[trigger_id]
            patterns = []

            for pattern_id in pattern_ids:
                patterns.append(self._get_pattern(pattern_id))

            triggers.append(
                Trigger(
                    trigger_id, patterns,
                    self.loaded_sigs.trigger_id_safelist.get(trigger_id)
                )
            )

        return triggers

    def _create_signature(self, sigid):
        """Create a Signature object and all of its triggers and patterns."""
        triggers_ids = self.loaded_sigs.signature_id_trigger_ids[sigid]

        loaded_sig = self.loaded_sigs.sigid_siginfo[sigid]
        self.sigid_sig[sigid] = Signature(
            triggers=self._create_triggers(triggers_ids), name=loaded_sig.name,
            short_description=loaded_sig.short_description,
            description=loaded_sig.description, score=loaded_sig.score,
            family=loaded_sig.family, tags=loaded_sig.tags,
            ttps=loaded_sig.ttps
        )

    def _create_indicator(self, indicator_id):
        """Creates the indicator and all indicators and signatures that
         use it."""
        trigger_ids = self.loaded_sigs.indicator_id_trigger_ids[indicator_id]

        indicator = IndicatorPattern(
            indicator_id, self._create_triggers(trigger_ids)
        )
        self.pattern_id_pattern[indicator_id] = indicator

        # Create indicators that reference this indicator.
        refs = self.loaded_sigs.pattern_id_indicator.get(indicator_id, [])
        for referencing_pattern in refs:
            if not self._pattern_exists(referencing_pattern):
                self._create_indicator(referencing_pattern)

        # Create all signatures that use this indicator, because these are now
        # also partially triggered.
        for sigid in self.loaded_sigs.pattern_id_sigids.get(indicator_id, []):
            if not self._signature_exists(sigid):
                self._create_signature(sigid)

        return indicator

    def _signature_exists(self, sig_id):
        return sig_id in self.sigid_sig

    def add_match(self, pattern_id, matchctx):
        # All signatures the matched pattern is a part of.
        sig_ids = self.loaded_sigs.pattern_id_sigids.get(
            pattern_id, []
        )

        # All indicators the matched pattern is a part of.
        indicator_ids = self.loaded_sigs.pattern_id_indicator.get(
            pattern_id, []
        )

        # If the signature this pattern is part of does not yet exist, create
        # it so it can later be checked if it was fully matched.
        for sig_id in sig_ids:
            if not self._signature_exists(sig_id):
                self._create_signature(sig_id)

        # Create each indicator that has this pattern and does not yet exist.
        for indicator_id in indicator_ids:
            if not self._pattern_exists(indicator_id):
                self._create_indicator(indicator_id)

        # Add the match context to the pattern that matched.
        self.pattern_id_pattern[pattern_id].add_match(matchctx)

    def get_matches(self):
        matched = []
        for sig in self.sigid_sig.values():
            if sig.matched:
                matched.append(sig)

        return matched

class PatternScanner:
    """The pattern scanner can load YAML signature files that contain
    signature and indicator declarations. The patterns from these signatures
    and indicators added to a hyperscan database.

    Pattern matches are passed to the SigMatchTracker it currently has.
    Call new_tracker() to reset/create a new tracker. This must be done
    before any scans can be performed.

    The compile() function must be called before any scans can be performed.
    After compiling, no more signature files can be loaded.
    """

    def __init__(self):
        self._eventkind_scandb = {}

        self._sigs = LoadedSignatures()
        self.matchtracker = None

    def _create_scandb(self, eventkind, pattern_list):
        if eventkind in self._eventkind_scandb:
            raise KeyError(
                f"Scan db for event kind '{eventkind}' already exists"
            )

        expressions, pattern_ids, flags = zip(*[
            (pattern.regex.encode(), pattern.id, _PATTERN_HYPERSCAN_FLAGS)
            for pattern in pattern_list
        ])

        hyperscan_db = hyperscan.Database()
        try:
            hyperscan_db.compile(
                expressions=expressions, ids=pattern_ids,
                elements=len(expressions), flags=flags
            )
        except hyperscan.error as e:
            raise PatternSignatureError(
                f"Failed to compile Hyperscan database. Error: {e}"
            ).with_traceback(e.__traceback__)

        self._eventkind_scandb[eventkind] = hyperscan_db

    def load_sigfile(self, sigfile_path):
        self._sigs.load_from_file(sigfile_path)

    def compile(self):
        """Compile a hyperscan database for each kind of event using
        the patterns from the LoadedSignatures"""
        eventkind_patterns = {}
        for loadedpattern in self._sigs.pattern_id_pattern.values():
            if loadedpattern.TYPE != _LoadedPatternTypes.REGEX:
                continue

            eventkind_patterns.setdefault(
                loadedpattern.eventkind, []
            ).append(loadedpattern)

        for eventkind, patterns in eventkind_patterns.items():
            # Map all pattern for a specific event kind to its pattern id
            # and create a scandb with this mapping.
            self._create_scandb(eventkind, patterns)

    def _on_match(self, pattern_id, matched_from, matched_to, flags, ctx):
        loaded_pattern = self._sigs.pattern_id_pattern.get(pattern_id)

        # Regex matched, now verify if the pattern expects this event to be of
        # a of a certain subtype. E.g: Only file delete or must it match all
        # file events.
        if loaded_pattern.subtype and loaded_pattern.subtype != ctx[5]:
            return

        # Pass the original string and full event obj to match tracker.
        self.matchtracker.add_match(
            pattern_id, MatchContext(
                matched_str=ctx[0], orig_str=ctx[1], event=ctx[2],
                kind=ctx[3], processing_ctx=ctx[4], subtype=ctx[5],
                extra_safelistdata=ctx[6]
            )
        )

    def new_tracker(self):
        """Create a new SigMatchTracker that will receive all pattern
        matches."""
        self.matchtracker = SigMatchTracker(self._sigs)
        return self.matchtracker

    def clear(self):
        """Clear out the current SigMatchTracker"""
        self.matchtracker = None

    def scan(self, scan_str, orig_str, event, event_kind, processing_ctx=None,
             event_subtype=None, extra_safelistdata=None):
        """Scan the given 'scan_str' on the 'event_kind' database.
        A subtype of an event can be given to ignore a pattern match that does
        not match the subtype. E.G 'file write', instead of 'file'.

        The 'orig_str' and 'event'(NormalizedEvent) are passed to the
        SigMatchTracker and added to the IOCs of matched patterns.
        """
        if not self.matchtracker:
            raise ValueError(
                "No scan can be performed if no tracker was created"
            )

        scandb = self._eventkind_scandb.get(event_kind)
        if not scandb:
            return

        if not isinstance(scan_str, bytes):
            scan_str = scan_str.encode("utf-8")

        scandb.scan(
            scan_str, self._on_match,
            context=(scan_str, orig_str, event, event_kind, processing_ctx,
                     event_subtype, extra_safelistdata)
        )
