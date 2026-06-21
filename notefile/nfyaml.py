import io
import re

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

YAML_UNPRINTABLE_RE = re.compile(
    r"[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]"
)


def _escape_unprintable_yaml_chars(text):
    """Replace YAML-unprintable characters with visible escape text."""

    def replace(match):
        char = match.group(0)
        codepoint = ord(char)
        if codepoint <= 0xFF:
            return f"\\x{codepoint:02X}"
        elif codepoint <= 0xFFFF:
            return f"\\u{codepoint:04X}"
        else:
            return f"\\U{codepoint:08X}"

    return YAML_UNPRINTABLE_RE.sub(replace, text)


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
        if YAML_UNPRINTABLE_RE.search(item):
            item = _escape_unprintable_yaml_chars(item)
        return PreservedScalarString(item)
    else:
        return item


# Note debug()that this will *still* not show with `--debug` since CLI hasn't
# been parsed. Set NOTEFILE_DEBUG to see it
yaml_safe = ruamel_yaml.YAML(typ="safe")


def load_ruamel_yaml(txt):
    return yaml_safe.load(txt)


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
        """pyyaml loader"""
        return pyyaml.load(txt, Loader=SafeLoader)

except ImportError:
    debug("no pyyaml. Fallback to ruamel_yaml to load")
    load_yaml = load_ruamel_yaml


def yamltxt(data):
    """Serialize a Python object to YAML text using the configured dumper."""
    with io.StringIO() as stream:
        yaml.dump(pss(data), stream)
        return stream.getvalue()
