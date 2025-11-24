import asyncio
import httpx
import asyncpg
import json
import sys

# Configuration
DB_DSN = "postgresql://postgres:postgres@localhost:15432/npm_threat_db"
QUERY_API_URL = "http://localhost:8004/api/v1/query"
API_KEY = "dev-api-key-123"

async def verify_fixes():
    print("🚀 Starting verification of critical bug fixes...")

    # 1. DB 직접 주입 (Test Setup)
    print("\n[Step 1] Injecting test data into DB...")
    try:
        conn = await asyncpg.connect(DB_DSN)
        
        # Clean up existing data for lodash to ensure clean state
        await conn.execute("DELETE FROM analysis_results WHERE cve_id = 'CVE-TEST-LODASH'")
        await conn.execute("DELETE FROM package_cve_mapping WHERE package = 'lodash' AND version_range = '4.17.20'")

        # Insert mapping
        await conn.execute("""
            INSERT INTO package_cve_mapping (package, version_range, ecosystem, cve_ids)
            VALUES ('lodash', '4.17.20', 'npm', ARRAY['CVE-TEST-LODASH'])
            ON CONFLICT (package, version_range, ecosystem) DO UPDATE 
            SET cve_ids = ARRAY['CVE-TEST-LODASH']
        """)

        # Insert analysis result with High Risk Score (9.5)
        # This verifies the schema change (risk_score column) and data persistence
        await conn.execute("""
            INSERT INTO analysis_results (cve_id, risk_level, risk_score, recommendations, analysis_summary, generated_at)
            VALUES (
                'CVE-TEST-LODASH',
                'High',
                9.5,
                ARRAY['Upgrade immediately'],
                'Critical vulnerability for testing.',
                NOW()
            )
            ON CONFLICT (cve_id) DO UPDATE 
            SET risk_score = 9.5, risk_level = 'High'
        """)
        
        # Insert CVSS/EPSS for completeness (optional but good for full response)
        await conn.execute("""
            INSERT INTO cvss_scores (cve_id, cvss_score, collected_at)
            VALUES ('CVE-TEST-LODASH', 9.8, NOW())
            ON CONFLICT (cve_id) DO NOTHING
        """)
        
        await conn.close()
        print("✅ Test data injected successfully.")

    except Exception as e:
        print(f"❌ DB Injection failed: {e}")
        sys.exit(1)

    # 2. API 조회 (Verification)
    print("\n[Step 2] Querying API for 'lodash'...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                QUERY_API_URL, 
                params={"package": "lodash", "version": "4.17.20"},
                headers={"x-api-key": API_KEY}
            )
            
            if response.status_code != 200:
                print(f"❌ API Request failed: {response.status_code} - {response.text}")
                sys.exit(1)
                
            data = response.json()
            # print(json.dumps(data, indent=2)) # Debug

        except Exception as e:
            print(f"❌ API Request failed with exception: {e}")
            sys.exit(1)

    # 3. 검증 (Assertion)
    print("\n[Step 3] Asserting results...")
    
    cve_list = data.get("cve_list", [])
    target_cve = next((c for c in cve_list if c["cve_id"] == "CVE-TEST-LODASH"), None)

    if not target_cve:
        print("❌ CVE-TEST-LODASH not found in response.")
        sys.exit(1)

    risk_score = target_cve.get("risk_score")
    risk_label = target_cve.get("risk_label")

    print(f"   - Found risk_score: {risk_score}")
    print(f"   - Found risk_label: {risk_label}")

    # Check 1: risk_score should be 9.5
    if risk_score != 9.5:
        print(f"❌ Assertion Failed: Expected risk_score 9.5, got {risk_score}")
        sys.exit(1)
    else:
        print("✅ risk_score is correct (9.5).")

    # Check 2: risk_label should be 'P1' (since 9.5 >= 8.0)
    if risk_label != "P1":
        print(f"❌ Assertion Failed: Expected risk_label 'P1', got '{risk_label}'")
        sys.exit(1)
    else:
        print("✅ risk_label is correct ('P1').")

    # 4. 결과 출력
    print("\n\033[92m[SUCCESS] Bug Fixes Verified! Ready for Demo.\033[0m")

if __name__ == "__main__":
    asyncio.run(verify_fixes())
