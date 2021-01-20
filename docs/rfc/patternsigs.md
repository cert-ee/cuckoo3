Cuckoo 3 pattern sigs.

* Labeled groups regular expressions that match file, registry, process commandline etc events.

YAML format.

A signature file must have a 'signatures' key. This is a YAML dictionary, where each
key is a signature.

Each signature consists of: short_description, description, score, tags, ttps, family, triggers.
Both descriptions and family are strings. Tags and ttps are lists of strings, score is an integer.

Trigger is a list of trigger dictionaries.

A trigger is a dictionary where the keys are event names + optional subtypes. E.G: file, file write, registry, registry read, commandline. The values of these keys are a list of one or more regexes.

