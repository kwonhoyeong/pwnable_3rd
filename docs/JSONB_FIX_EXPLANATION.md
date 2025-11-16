# JSONB Serialization Fix Explanation

## Problem

The threat agent pipeline was failing with:

```
asyncpg.exceptions.DataError: invalid input for query argument $4:
[{'source': 'https://example.com/...'}]
('list' object has no attribute 'encode')
```

This error occurred in asyncpg's JSONB encoder:

```python
# asyncpg/protocol/codecs/base.pyx, line 189
# sqlalchemy/dialects/postgresql/asyncpg.py, line 1220
def _jsonb_encoder(value):
    return b"\x01" + str_value.encode()  # ❌ Assumes value is already a string
    # AttributeError: 'list' object has no attribute 'encode'
```

## Root Cause

The issue had **two layers**:

### Layer 1: Non-JSON-serializable Pydantic types (Fixed first)
- `ThreatCase.source` is a Pydantic `HttpUrl` object
- `ThreatCase.collected_at` is a `datetime` object
- These needed conversion to JSON-safe strings

**Solution**: Added `_serialize_case_for_jsonb()` using `pydantic_encoder`

### Layer 2: SQLAlchemy not recognizing JSONB type (This fix)
- Even with JSON-safe values, asyncpg was calling `.encode()` on the Python list
- This happens when SQLAlchemy treats the parameter as `TEXT` instead of `JSONB`
- asyncpg's JSONB encoder expects to receive a **JSON string**, not a Python object

**Solution**: Explicitly bind the `cases` parameter as `JSONB` type

## The Fix

### Before

```python
query = text("""
    INSERT INTO threat_cases (cve_id, package, version_range, cases)
    VALUES (:cve_id, :package, :version_range, :cases)
    ...
""")

await session.execute(query, {
    "cases": serialized_cases,  # Python list - SQLAlchemy guesses it's TEXT
})
```

**What happened**:
1. SQLAlchemy sees a list but has no type information for `:cases`
2. It defaults to treating it as TEXT
3. asyncpg's TEXT encoder tries to call `str(list).encode()` → fails

### After

```python
from sqlalchemy import bindparam
from sqlalchemy.dialects.postgresql import JSONB

query = text("""
    INSERT INTO threat_cases (cve_id, package, version_range, cases)
    VALUES (:cve_id, :package, :version_range, :cases)
    ...
").bindparams(bindparam("cases", type_=JSONB))  # ✅ Explicit JSONB type

await session.execute(query, {
    "cases": serialized_cases,  # Python list - SQLAlchemy knows it's JSONB
})
```

**What happens now**:
1. SQLAlchemy sees `bindparam("cases", type_=JSONB)`
2. It uses asyncpg's JSONB encoder properly
3. The encoder JSON-encodes the Python list/dict and prepends `\x01` byte
4. PostgreSQL receives valid JSONB data

## Data Flow

```
Pydantic ThreatCase objects
  ↓
[_serialize_case_for_jsonb]  ← Converts HttpUrl/datetime to strings
  ↓
Python list of JSON-safe dicts
  ↓
[SQLAlchemy + bindparam(type_=JSONB)]  ← Tells asyncpg to use JSONB encoder
  ↓
JSON string with \x01 prefix
  ↓
PostgreSQL JSONB column
```

## Files Changed

- `threat_agent/app/repository.py`:
  - Added imports: `bindparam`, `JSONB`
  - Added `.bindparams(bindparam("cases", type_=JSONB))` to the query
  - Added explanatory comments

## Database Schema

The `threat_cases` table (from `database/init-db.sql`):

```sql
CREATE TABLE IF NOT EXISTS threat_cases (
    id SERIAL PRIMARY KEY,
    cve_id TEXT NOT NULL,
    package TEXT NOT NULL,
    version_range TEXT NOT NULL,
    cases JSONB NOT NULL DEFAULT '[]'::JSONB,  -- ← JSONB column
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (cve_id, package, version_range)
);
```

## Example Stored Data

After this fix, the database contains:

```sql
SELECT cases FROM threat_cases WHERE cve_id = 'CVE-FAKE-LODASH-0001';
```

```json
[
  {
    "source": "https://example.com/prototype-case",
    "title": "Fallback case for CVE-FAKE-LODASH-0001",
    "date": "2025-11-16",
    "summary": "AI API 호출 실패로 인해 기본 설명...",
    "collected_at": "2025-11-16T03:41:46.144946"
  }
]
```

All values are JSON-safe primitives (strings, numbers, booleans, nulls).

## Testing

Run the pipeline:

```bash
python3 main.py --package lodash
```

Expected: No more `'list' object has no attribute 'encode'` errors.

## References

- SQLAlchemy docs: [Type-specific bind parameters](https://docs.sqlalchemy.org/en/14/core/sqlelement.html#sqlalchemy.sql.expression.text.bindparams)
- PostgreSQL JSONB: [JSON Types](https://www.postgresql.org/docs/current/datatype-json.html)
- asyncpg protocol: Uses `\x01` + JSON string for JSONB encoding
