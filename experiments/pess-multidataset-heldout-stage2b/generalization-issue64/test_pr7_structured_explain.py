from __future__ import annotations

import json
import hashlib
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forest10_runner import (
    PR58Forest10Backend,
    PR7StructuredExplainAdapter,
    parse_pr7_structured_explain,
)


RELATION_OID = 42001
STAT_OID = 42002


def explain_payload(*, status="complete", estimate=12.5, include_estimate=True):
    events = [
        {
            "sequence": 1,
            "type": "base_estimate",
            "relation_oid": RELATION_OID,
            "rte_index": 1,
            "rel_tuples": 1000,
            "selectivity": 0.0125,
            "nrows_preclamp": estimate,
            "rows_postclamp": 13,
        }
    ]
    if include_estimate:
        events.extend([
            {
                "sequence": 2,
                "type": "mcv_selection",
                "relation_oid": RELATION_OID,
                "stat_oid": STAT_OID,
                "key_count": 2,
            },
            {
                "sequence": 3,
                "type": "mcv_clause",
                "relation_oid": RELATION_OID,
                "stat_oid": STAT_OID,
                "clause_index": 0,
            },
            {
                "sequence": 4,
                "type": "mcv_estimate",
                "relation_oid": RELATION_OID,
                "stat_oid": STAT_OID,
                "clause_count": 1,
                "simple_sel": 0.1,
                "mcv_sel": 0.2,
                "mcv_basesel": 0.15,
                "mcv_totalsel": 0.3,
                "stat_sel": 0.25,
            },
        ])
    return json.dumps([{
        "Plan": {"Node Type": "Seq Scan", "Plan Rows": 13},
        "ESS Diagnostics": {
            "Status": status,
            "Event Count": len(events),
            "Events": events,
        },
    }])


class PR7StructuredExplainTests(unittest.TestCase):
    def parse(self, output, *, stats=None):
        return parse_pr7_structured_explain(
            output,
            query_id="arecel:forest10:valid:000005",
            relation_oid=RELATION_OID,
            expected_stat_oids=stats if stats is not None else {STAT_OID: "e00_01"},
        )

    def test_parses_complete_preclamp_and_matches_mcv_oid_clause_to_candidate(self):
        parsed = self.parse(explain_payload())
        self.assertEqual(parsed["query_id"], "arecel:forest10:valid:000005")
        self.assertEqual(parsed["estimate_preclamp"], "12.5")
        self.assertEqual(parsed["mcv_diagnostics_status"], "VERIFIED")
        self.assertEqual(parsed["selected_statistic_ids"], ["e00_01"])
        self.assertEqual(parsed["mcv_records"][0]["clause_indexes"], [0])

    def test_reports_no_mcv_events_without_claiming_coverage(self):
        parsed = self.parse(explain_payload(include_estimate=False), stats={})
        self.assertEqual(parsed["mcv_diagnostics_status"], "NO_MCV_EVENTS")
        self.assertEqual(parsed["selected_statistic_ids"], [])

    def test_rejects_incomplete_or_noncomplete_status(self):
        with self.assertRaisesRegex(ValueError, "status"):
            self.parse(explain_payload(status="incomplete"))
        with self.assertRaisesRegex(ValueError, "status"):
            self.parse(explain_payload(status="empty"))

    def test_rejects_missing_fields_nonpositive_and_nonfinite_preclamp(self):
        missing = json.loads(explain_payload())
        del missing[0]["ESS Diagnostics"]["Events"][0]["nrows_preclamp"]
        with self.assertRaisesRegex(ValueError, "nrows_preclamp"):
            self.parse(json.dumps(missing))
        for value in (0, -1, "NaN", "Infinity"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "positive"):
                self.parse(explain_payload(estimate=value))

    def test_rejects_missing_top_level_fields_and_event_count_mismatch(self):
        missing = json.loads(explain_payload())
        del missing[0]["ESS Diagnostics"]
        with self.assertRaisesRegex(ValueError, "ESS Diagnostics"):
            self.parse(json.dumps(missing))
        mismatch = json.loads(explain_payload())
        mismatch[0]["ESS Diagnostics"]["Event Count"] += 1
        with self.assertRaisesRegex(ValueError, "Event Count"):
            self.parse(json.dumps(mismatch))

    def test_rejects_missing_mcv_numeric_field(self):
        missing = json.loads(explain_payload())
        del missing[0]["ESS Diagnostics"]["Events"][3]["stat_sel"]
        with self.assertRaisesRegex(ValueError, "stat_sel"):
            self.parse(json.dumps(missing))

    def test_rejects_unmapped_oid_relation_or_clause_correspondence(self):
        with self.assertRaisesRegex(ValueError, "configured OID ledger"):
            self.parse(explain_payload(), stats={999: "e00_01"})
        wrong_relation = json.loads(explain_payload())
        wrong_relation[0]["ESS Diagnostics"]["Events"][1]["relation_oid"] += 1
        with self.assertRaisesRegex(ValueError, "configured OID ledger"):
            self.parse(json.dumps(wrong_relation))
        wrong_clause_count = json.loads(explain_payload())
        wrong_clause_count[0]["ESS Diagnostics"]["Events"][3]["clause_count"] = 2
        with self.assertRaisesRegex(ValueError, "clause_count"):
            self.parse(json.dumps(wrong_clause_count))

    def test_rejects_reordered_sequence_and_unmatched_clause(self):
        wrong_sequence = json.loads(explain_payload())
        wrong_sequence[0]["ESS Diagnostics"]["Events"][0]["sequence"] = 2
        with self.assertRaisesRegex(ValueError, "sequence"):
            self.parse(json.dumps(wrong_sequence))
        orphan = json.loads(explain_payload())
        orphan[0]["ESS Diagnostics"]["Events"][2]["stat_oid"] += 10
        with self.assertRaisesRegex(ValueError, "differs"):
            self.parse(json.dumps(orphan))

    def test_adapter_issues_opt_in_json_explain_and_preserves_query_identity(self):
        calls = []

        def psql(prefix, socket_dir, port, sql, env, *, tuples=False):
            calls.append((prefix, socket_dir, port, sql, tuples))
            return explain_payload()

        helpers = SimpleNamespace(os=os, psql=psql)
        adapter = PR7StructuredExplainAdapter(
            helpers,
            Path("/private/install"),
            {"socket_dir": Path("/private/socket"), "port": 55432},
            RELATION_OID,
            [{"oid": STAT_OID, "statistic_name": "ess_issue64_forest10_e00_01"}],
            {"ess_issue64_forest10_e00_01": "e00_01"},
        )
        result = adapter.explain({
            "query_id": "arecel:forest10:valid:000005",
            "sql": "SELECT * FROM public.forest10 WHERE \"Elevation\" = 1",
        })
        self.assertEqual(result["query_id"], "arecel:forest10:valid:000005")
        self.assertEqual(len(calls), 1)
        self.assertIn("EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON, SUMMARY OFF)", calls[0][3])
        self.assertTrue(calls[0][4])

    def test_formal_backend_uses_only_json_preclamp_and_records_no_mcv(self):
        calls = []
        sample = Path(__file__).with_name("synthetic-sample.tmp")
        sample.write_bytes(b"sample")
        self.addCleanup(sample.unlink, missing_ok=True)
        digest = hashlib.sha256(b"sample").hexdigest()
        header = {
            "relation_identity": "6:public8:forest10",
            "server_version": "16.14",
            "natts": 10,
            "relation_oid": RELATION_OID,
        }

        def psql(prefix, socket_dir, port, sql, env, *, tuples=False):
            calls.append(sql)
            return explain_payload(include_estimate=False)

        helpers = SimpleNamespace(
            os=os,
            psql=psql,
            run_query=lambda *args, **kwargs: self.fail("legacy trace path must not be called"),
            sample_header=lambda path: header,
            sha256_file=lambda path: digest,
        )
        identity = {"table": "public.forest10", "header": header, "sha256": digest}
        backend = PR58Forest10Backend(
            helpers,
            Path("/private/install"),
            {"socket_dir": Path("/private/socket"), "port": 55432},
            [{"id": "e00_01", "statistic_name": "ess_issue64_forest10_e00_01"}],
            sample,
            identity,
        )
        estimate = backend.preclamp_estimate(
            {"query_id": "arecel:forest10:valid:000005", "sql": "SELECT * FROM public.forest10"},
            [{"oid": STAT_OID, "statistic_name": "ess_issue64_forest10_e00_01"}],
            "ignored-legacy-marker",
        )
        self.assertEqual(str(estimate), "12.5")
        self.assertEqual(backend.last_observation["mcv_diagnostics_status"], "NO_MCV_EVENTS")
        self.assertIn("EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON, SUMMARY OFF)", calls[0])
        self.assertNotIn("ignored-legacy-marker", calls[0])


if __name__ == "__main__":
    unittest.main()
