"""Quick test of cache serialization helpers."""
import json
import datetime
import decimal
import re
from typing import Any


def _json_default(o):
    """Convert common non-JSON types to JSON-serializable values."""
    if isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
        try:
            return o.isoformat()
        except Exception:
            return str(o)
    if isinstance(o, decimal.Decimal):
        # preserve integer-y decimals as int when possible
        try:
            if o % 1 == 0:
                return int(o)
        except Exception:
            pass
        return float(o)
    # fallback: stringify unknown types
    return str(o)


def _parse_iso_datetime(s: str) -> datetime.datetime | str:
    """Try to parse ISO 8601 datetime string; return original string if parse fails."""
    if not isinstance(s, str):
        return s
    # Simple ISO 8601 pattern: YYYY-MM-DDTHH:MM:SS[.ffffff][+HH:MM|Z]
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', s):
        try:
            # Python 3.7+ supports fromisoformat
            return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
        except Exception:
            return s
    return s


def _restore_datetimes(obj: Any) -> Any:
    """Recursively walk a deserialized JSON object and restore datetime objects from ISO strings."""
    if isinstance(obj, dict):
        return {k: _restore_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_restore_datetimes(item) for item in obj]
    elif isinstance(obj, str):
        return _parse_iso_datetime(obj)
    return obj


if __name__ == "__main__":
    # Test serialization
    test_obj = {
        'timestamp': datetime.datetime.now(datetime.timezone.utc),
        'rows': [
            {'value': decimal.Decimal('123.0')},
            {'value': decimal.Decimal('45.67')}
        ],
        'date': datetime.date.today()
    }

    # Should work now
    result = json.dumps(test_obj, default=_json_default, ensure_ascii=False)
    print("✓ Serialization successful")
    print("JSON:", result[:100], "...")

    # Test deserialization and restoration
    restored = json.loads(result)
    restored = _restore_datetimes(restored)
    print("✓ Restoration successful")
    print("Restored timestamp type:", type(restored['timestamp']))
    print("✓ All tests passed!")
