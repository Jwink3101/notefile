import io

from . import debug

#### Set up YAML
# ruamel_yaml is does a nice job with formatting but it is slow to load YAML.
# pyyaml is faster to load YAML anyway and *much* faster with CLoader if it
# is available.
#
# The biggest reason to still use ruamel_yaml over pyyaml is
# https://github.com/yaml/pyyaml/issues/121
# However I do not want to make pyyaml *also* a requirement so it will use it
# if it can or fall back
try:
    import ruamel_yaml
    from ruamel_yaml.scalarstring import LiteralScalarString as PreservedScalarString
except ImportError:
    import ruamel.yaml as ruamel_yaml
    from ruamel.yaml.scalarstring import LiteralScalarString as PreservedScalarString

yaml = ruamel_yaml.YAML()


def pss(item):
    """Convert multiline strings into YAML literal scalars recursively.

    Lists and tuples are traversed element-by-element, with tuples converted to
    lists for YAML emission. Dictionaries are copied before their values are
    transformed.
    """
    if isinstance(item, (list, tuple)):
        return [pss(i) for i in item]  # Convert tuples to lists for parsing
    elif isinstance(item, dict):
        item = item.copy()
        for key, val in item.items():
            item[key] = pss(val)
        return item
    elif isinstance(item, str) and "\n" in item:
        return PreservedScalarString(item)
    else:
        return item


# Note debug()that this will *still* not show with `--debug` since CLI hasn't
# been parsed. Set NOTEFILE_DEBUG to see it
try:
    import yaml as pyyaml

    debug("loaded pyyaml")
    try:
        from yaml import CSafeLoader as SafeLoader

        debug("got CSafeLoader")
    except ImportError:
        debug("no CSafeLoader")
        from yaml import SafeLoader

    def load_yaml(txt):
        return pyyaml.load(txt, Loader=SafeLoader)

except ImportError:
    debug("no pyyaml. Fallback to ruamel_yaml to load")
    yaml_safe = ruamel_yaml.YAML(typ="safe")

    def load_yaml(txt):
        return yaml_safe.load(txt)


def yamltxt(data):
    """Serialize a Python object to YAML text using the configured dumper."""
    with io.StringIO() as stream:
        yaml.dump(pss(data), stream)
        return stream.getvalue()
