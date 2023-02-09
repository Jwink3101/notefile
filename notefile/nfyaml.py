from . import debug

import io

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
    """
    Convert strings with '\n' to PreservedScalarString
    and recurse into dicts and lists (and tuples which are converted to lists).
    """
    if isinstance(
        item,
        (
            list,
            tuple,
        ),
    ):
        return [pss(i) for i in item]  # Convert tuples to lists for parsing
    elif isinstance(item, dict):
        item = item.copy()
        for key, val in item.items():
            item[key] = pss(val)
        return item
    elif (
        isinstance(
            item,
            str,
        )
        and "\n" in item
    ):
        return PreservedScalarString(item)
    else:
        return item


# Note debug()that this will *still* not show with `--debug` since CLI hasn't
# been parsed. Set NOTEFILE_DEBUG to see it
try:
    import yaml as pyyaml

    debug("loaded pyyaml")
    try:
        from yaml import CLoader as Loader

        debug("got CLoader")
    except ImportError:
        debug("no CLoader")
        from yaml import Loader

    def load_yaml(txt):
        return pyyaml.load(
            txt,
            Loader=Loader,
        )

except ImportError:
    debug("no pyyaml. Fallback to ruamel_yaml to load")

    def load_yaml(txt):
        return yaml.load(txt)


def yamltxt(data):
    with io.StringIO() as stream:
        yaml.dump(pss(data), stream)
        return stream.getvalue()
