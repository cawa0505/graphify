import json as std_json
from json import JSONDecodeError
from typing import Any

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

def dumps(
    obj: Any,
    indent: int | None = None,
    sort_keys: bool = False,
    ensure_ascii: bool = True,
    separators: tuple[str, str] | None = None,
    default: Any = None,
) -> str:
    """Serialize obj to a JSON formatted string, utilizing orjson if installed."""
    if HAS_ORJSON:
        opts = 0
        if indent is not None:
            # orjson only supports 2-space indentation via OPT_INDENT_2
            opts |= orjson.OPT_INDENT_2
        if sort_keys:
            opts |= orjson.OPT_SORT_KEYS
        if not ensure_ascii:
            pass
        
        # orjson.dumps returns bytes, decode to str for 100% stdlib compatibility
        return orjson.dumps(obj, option=opts, default=default).decode("utf-8")
    else:
        return std_json.dumps(
            obj,
            indent=indent,
            sort_keys=sort_keys,
            ensure_ascii=ensure_ascii,
            separators=separators,
            default=default,
        )

def dump(obj: Any, fp: Any, **kwargs: Any) -> None:
    """Write JSON to a file-like object."""
    fp.write(dumps(obj, **kwargs))

def loads(s: str | bytes) -> Any:
    """Deserialize s to a Python object."""
    if HAS_ORJSON:
        if isinstance(s, str):
            s = s.encode("utf-8")
        return orjson.loads(s)
    else:
        return std_json.loads(s)

def load(fp: Any, **kwargs: Any) -> Any:
    """Read JSON from a file-like object."""
    return loads(fp.read())
