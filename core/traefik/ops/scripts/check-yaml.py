#!/usr/bin/env python3
"""Parse Traefik's rendered YAML and refuse a file Traefik would reject.

    check-yaml.py FILE...

Traefik's file provider rejects the whole directory when one file does not
parse, keeps serving the configuration it had, and starts without every
@file middleware and TLS option the next time it is created: every router
answers 404 (a duplicated key in config/dynamic/crowdsec.yml).
PyYAML keeps the last of two equal keys without a word, so the loader below
treats a repeated key in one mapping as the error Traefik makes of it.

Exit 0 when every file parses, 1 with one line per problem, 2 when PyYAML is
missing — the check is then not done, and says so.
"""
import sys

try:
    import yaml
except ImportError:
    print("NOT VERIFIED: python3-yaml is missing — the rendered YAML was not parsed")
    sys.exit(2)


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node, deep=False):
    seen = {}
    for key_node, _ in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            continue
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None,
                f'mapping key "{key}" already defined at line {seen[key] + 1}',
                key_node.start_mark)
        seen[key] = key_node.start_mark.line
    return loader.construct_mapping(node, deep=deep)


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)

failed = 0
for path in sys.argv[1:]:
    try:
        with open(path, encoding="utf-8") as fh:
            list(yaml.load_all(fh, Loader=UniqueKeyLoader))
    except (OSError, yaml.YAMLError) as exc:
        print(f"ERROR: {path}: {' '.join(str(exc).split())}")
        failed = 1
sys.exit(failed)
