"""Standalone test for JSONB serialization fix."""
from datetime import datetime
from typing import Any
import json


def _serialize_case_for_jsonb(case: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a threat case dict to a JSON-serializable format for JSONB storage.

    Handles:
    - HttpUrl objects -> str
    - datetime objects -> ISO-8601 string
    - Other Pydantic types -> appropriate JSON-safe formats
    """
    serialized = {}
    for key, value in case.items():
        if value is None:
            serialized[key] = None
        elif isinstance(value, datetime):
            # Convert datetime to ISO-8601 string
            serialized[key] = value.isoformat()
        elif hasattr(value, '__str__') and type(value).__module__ == 'pydantic.networks':
            # Handle Pydantic HttpUrl and other network types
            serialized[key] = str(value)
        elif isinstance(value, (str, int, float, bool)):
            # Primitive JSON types
            serialized[key] = value
        elif isinstance(value, (list, dict)):
            # Nested structures (shouldn't happen in current schema, but handle anyway)
            serialized[key] = value
        else:
            # Fallback: convert to string
            serialized[key] = str(value)
    return serialized


# Mock HttpUrl for testing
class MockHttpUrl:
    """Mock HttpUrl object that mimics Pydantic v1 HttpUrl behavior."""

    def __init__(self, url):
        self.url = url
        self.__class__.__module__ = 'pydantic.networks'

    def __str__(self):
        return self.url


def test_serialization():
    """Test that case dicts serialize correctly for JSONB storage."""

    # Simulate what case.dict() returns in Pydantic v1 with HttpUrl and datetime
    case_dict = {
        'source': MockHttpUrl('https://example.com/prototype-case'),
        'title': 'Fallback case for CVE-FAKE-LODASH-0001',
        'date': '2025-11-16',
        'summary': 'AI API 호출 실패로 인해 기본 설명(Default narrative due to AI error).',
        'collected_at': datetime(2025, 11, 16, 3, 41, 46, 144946),
    }

    print("=" * 60)
    print("Testing JSONB Serialization Fix")
    print("=" * 60)
    print()

    print("Original case dict:")
    print(f"  source type: {type(case_dict['source']).__name__}")
    print(f"  source value: {case_dict['source']}")
    print(f"  collected_at type: {type(case_dict['collected_at']).__name__}")
    print(f"  collected_at value: {case_dict['collected_at']}")
    print()

    # Try to JSON-encode the original (should fail)
    print("Attempting to serialize original dict to JSON...")
    try:
        json.dumps([case_dict])
        print("  ✓ Original dict is JSON-serializable (unexpected)")
    except (TypeError, AttributeError) as e:
        print(f"  ✗ Original dict is NOT JSON-serializable: {type(e).__name__}")
        print(f"    Error: {str(e)[:80]}")
    print()

    # Serialize for JSONB
    serialized = _serialize_case_for_jsonb(case_dict)

    print("Serialized case dict:")
    print(f"  source type: {type(serialized['source']).__name__}")
    print(f"  source value: {serialized['source']}")
    print(f"  collected_at type: {type(serialized['collected_at']).__name__}")
    print(f"  collected_at value: {serialized['collected_at']}")
    print()

    # Verify it's JSON-serializable
    print("Attempting to serialize fixed dict to JSON...")
    try:
        json_str = json.dumps([serialized])
        print("  ✓ Successfully serialized to JSON")
        print()
        print("JSON output:")
        print("  " + json_str[:120] + "...")
        print()

        # Verify it can be deserialized
        deserialized = json.loads(json_str)[0]
        print("✓ Successfully deserialized from JSON:")
        print(f"  source: {deserialized['source']}")
        print(f"  collected_at: {deserialized['collected_at']}")
        print()

        print("=" * 60)
        print("✓ ALL TESTS PASSED - Fix should work correctly!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"✗ Serialization failed: {e}")
        print()
        print("=" * 60)
        print("✗ TESTS FAILED")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = test_serialization()
    exit(0 if success else 1)
