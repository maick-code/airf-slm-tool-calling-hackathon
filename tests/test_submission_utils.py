import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from submission_utils import (
    answer_from_training_row,
    coerce_prediction,
    parse_model_json,
    validate_prediction_map,
    write_submission_zip,
)


SCHEMAS = {
    "send_money": {
        "parameters": {
            "recipient": "string",
            "amount": "number",
            "currency": "string",
            "provider": "string",
        }
    },
    "check_balance": {"parameters": {"provider": "string"}},
    "get_weather": {"parameters": {"location": "string", "date": "string"}},
}


class SubmissionUtilsTests(unittest.TestCase):
    def test_single_call_completes_missing_fields_and_coerces_types(self):
        answer, used_fallback = coerce_prediction(
            '```json\n{"tool":"send_money","parameters":{"recipient":" Ada ","amount":"5,000"}}\n```',
            ["send_money", "check_balance"],
            SCHEMAS,
        )
        self.assertFalse(used_fallback)
        self.assertEqual(
            answer,
            {
                "tool": "send_money",
                "parameters": {
                    "recipient": "Ada",
                    "amount": 5000,
                    "currency": None,
                    "provider": None,
                },
            },
        )

    def test_multi_call_order_is_preserved(self):
        answer, used_fallback = coerce_prediction(
            [
                {"tool": "check_balance", "parameters": {"provider": "M-Pesa"}},
                {
                    "tool": "send_money",
                    "parameters": {
                        "recipient": "Otieno",
                        "amount": 500,
                        "currency": "KES",
                        "provider": "M-Pesa",
                    },
                },
            ],
            ["send_money", "check_balance"],
            SCHEMAS,
        )
        self.assertFalse(used_fallback)
        self.assertEqual([call["tool"] for call in answer], ["check_balance", "send_money"])

    def test_unoffered_tool_uses_complete_offered_fallback(self):
        answer, used_fallback = coerce_prediction(
            {"tool": "buy_airtime", "parameters": {}},
            ["check_balance", "send_money"],
            SCHEMAS,
        )
        self.assertTrue(used_fallback)
        self.assertEqual(answer, {"tool": "check_balance", "parameters": {"provider": None}})

    def test_non_numeric_amount_becomes_null_not_a_guess(self):
        answer, used_fallback = coerce_prediction(
            {"tool": "send_money", "parameters": {"amount": "five k"}},
            ["send_money"],
            SCHEMAS,
        )
        self.assertFalse(used_fallback)
        self.assertIsNone(answer["parameters"]["amount"])

    def test_large_integer_amount_string_keeps_exact_digits(self):
        answer, used_fallback = coerce_prediction(
            {"tool": "send_money", "parameters": {"amount": "9007199254740993"}},
            ["send_money"],
            SCHEMAS,
        )
        self.assertFalse(used_fallback)
        self.assertEqual(answer["parameters"]["amount"], 9007199254740993)

    def test_json_can_be_extracted_after_prose(self):
        self.assertEqual(
            parse_model_json('Here is the answer:\n[ {"tool":"check_balance","parameters":{}} ]'),
            [{"tool": "check_balance", "parameters": {}}],
        )

    def test_one_call_training_lists_are_canonicalized(self):
        row = {"id": "train-1", "tool_calls": [{"tool": "check_balance", "parameters": {"provider": None}}]}
        self.assertEqual(answer_from_training_row(row), row["tool_calls"][0])

    def test_zip_has_one_root_level_predictions_file_and_exact_ids(self):
        rows = [
            {"id": "dev-1", "tools": ["check_balance"]},
            {"id": "dev-2", "tools": ["get_weather"]},
        ]
        predictions = {
            "dev-1": {"tool": "check_balance", "parameters": {"provider": None}},
            "dev-2": {"tool": "get_weather", "parameters": {"location": "Kigali", "date": None}},
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            json_path, zip_path = write_submission_zip(
                rows,
                predictions,
                SCHEMAS,
                zip_path=root / "submission.zip",
                json_path=root / "predictions.json",
            )
            validate_prediction_map(rows, json.loads(json_path.read_text()), SCHEMAS)
            with zipfile.ZipFile(zip_path) as archive:
                self.assertEqual(archive.namelist(), ["predictions.json"])
                self.assertEqual(json.loads(archive.read("predictions.json")), predictions)


if __name__ == "__main__":
    unittest.main()
