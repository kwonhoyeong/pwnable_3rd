import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "common_lib" / "perplexity_parsers.py"
MODULE_SPEC = importlib.util.spec_from_file_location("perplexity_parsers", MODULE_PATH)
perplexity_parsers = importlib.util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC and MODULE_SPEC.loader
MODULE_SPEC.loader.exec_module(perplexity_parsers)  # type: ignore[arg-type]

parse_epss_response = perplexity_parsers.parse_epss_response
parse_cvss_response = perplexity_parsers.parse_cvss_response
parse_cve_mapping_response = perplexity_parsers.parse_cve_mapping_response
normalize_cve_ids = perplexity_parsers.normalize_cve_ids


class PerplexityParserTests(unittest.TestCase):
    def test_parse_epss_valid_score(self) -> None:
        raw = '{"epss_score": 0.72, "source": "https://epss.example.com/CVE-2024-1234"}'
        score, source = parse_epss_response(raw)
        self.assertEqual(score, 0.72)
        self.assertEqual(source, "https://epss.example.com/CVE-2024-1234")

    def test_parse_epss_invalid_json(self) -> None:
        score, source = parse_epss_response("not-json")
        self.assertIsNone(score)
        self.assertIsNone(source)

    def test_parse_cvss_valid_payload(self) -> None:
        raw = (
            '{"cvss_score": 7.5, "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", '
            '"source": "https://nvd.nist.gov/CVE-2024-1234"}'
        )
        score, vector, source = parse_cvss_response(raw)
        self.assertEqual(score, 7.5)
        self.assertEqual(vector, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
        self.assertEqual(source, "https://nvd.nist.gov/CVE-2024-1234")

    def test_parse_cvss_out_of_range(self) -> None:
        score, vector, source = parse_cvss_response('{"cvss_score": 12.1, "vector": null, "source": "not_found"}')
        self.assertIsNone(score)
        self.assertIsNone(vector)
        self.assertEqual(source, "not_found")

    def test_parse_cve_mapping_response(self) -> None:
        raw = '{"cve_ids": ["cve-2024-1234", "INVALID", "CVE-2024-1234", " CVE-2023-0001 "], "source": "https://nvd.nist.gov"}'
        cves, source = parse_cve_mapping_response(raw)
        self.assertEqual(cves, ["CVE-2024-1234", "CVE-2023-0001"])
        self.assertEqual(source, "https://nvd.nist.gov")

    def test_parse_cve_mapping_invalid_payload(self) -> None:
        cves, source = parse_cve_mapping_response('{"source": "missing"}')
        self.assertEqual(cves, [])
        self.assertEqual(source, "missing")

    def test_normalize_cve_ids(self) -> None:
        raw = ["cve-2024-1234", "INVALID", "CVE-2024-1234", " CVE-2023-0001 "]
        normalized = normalize_cve_ids(raw)
        self.assertEqual(normalized, ["CVE-2024-1234", "CVE-2023-0001"])

    def test_normalize_cve_ids_with_duplicates(self) -> None:
        raw = ["CVE-2024-1234", "cve-2024-1234", "CVE-2024-1234"]
        normalized = normalize_cve_ids(raw)
        self.assertEqual(normalized, ["CVE-2024-1234"])

    def test_normalize_cve_ids_empty(self) -> None:
        raw = ["NOT-CVE", "invalid", 123]
        normalized = normalize_cve_ids(raw)
        self.assertEqual(normalized, [])


if __name__ == "__main__":
    unittest.main()
