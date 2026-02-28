"""Unit tests for the Prompt Validator."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# ── Test utilities (no LLM needed) ───────────────────────────────────────────

from src.prompt_validator.schemas import ValidationIssue, ValidationResult
from src.prompt_validator.utils import generate_report, save_report


class TestSchemas(unittest.TestCase):
    """Ensure Pydantic schemas validate correctly."""

    def test_validation_issue_creation(self):
        issue = ValidationIssue(
            issue_type="Redundancy",
            description="Repeated phrasing detected.",
            suggestion="Remove the duplicate sentence.",
        )
        self.assertEqual(issue.issue_type, "Redundancy")

    def test_validation_result_empty(self):
        result = ValidationResult(issues=[])
        self.assertEqual(len(result.issues), 0)

    def test_validation_result_with_issues(self):
        result = ValidationResult(
            issues=[
                ValidationIssue(
                    issue_type="Contradiction",
                    description="Conflicting requirements.",
                    suggestion="Remove one of the conflicting statements.",
                ),
                ValidationIssue(
                    issue_type="Missing Section",
                    description="No success criteria.",
                    suggestion="Add measurable success criteria.",
                ),
            ]
        )
        self.assertEqual(len(result.issues), 2)
        self.assertEqual(result.issues[0].issue_type, "Contradiction")

    def test_invalid_issue_type_rejected(self):
        with self.assertRaises(Exception):
            ValidationIssue(
                issue_type="InvalidType",
                description="Bad type.",
                suggestion="Fix it.",
            )


class TestReportGeneration(unittest.TestCase):
    """Test the report utility functions."""

    SAMPLE_RESULTS = [
        {
            "file": "prompt1.txt",
            "issues": [
                {
                    "issue_type": "Redundancy",
                    "description": "Repeated content.",
                    "suggestion": "Remove duplicate lines.",
                }
            ],
            "suggestion": "Fixed prompt text here.",
            "status": "completed",
        },
        {
            "file": "prompt2.txt",
            "issues": [],
            "suggestion": None,
            "status": "completed",
        },
    ]

    def test_generate_report_json_format(self):
        report_json = generate_report(self.SAMPLE_RESULTS, output_format="json")
        data = json.loads(report_json)
        self.assertIn("summary", data)
        self.assertIn("details", data)
        self.assertEqual(data["summary"]["total_files"], 2)
        self.assertEqual(data["summary"]["files_with_issues"], 1)
        self.assertEqual(data["summary"]["total_issues"], 1)

    def test_save_report_creates_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            report_json = generate_report(self.SAMPLE_RESULTS, output_format="json")
            save_report(report_json, temp_path)
            self.assertTrue(os.path.exists(temp_path))

            with open(temp_path, "r") as f:
                content = json.loads(f.read())
            self.assertEqual(content["summary"]["total_files"], 2)
        finally:
            os.unlink(temp_path)


class TestValidatorFileHandling(unittest.TestCase):
    """Test file read/write operations in PromptValidator (mocked LLM)."""

    @patch("src.prompt_validator.validator.LLMHandler")
    def test_validate_prompt_file_reads_content(self, MockLLM):
        mock_handler = MagicMock()
        mock_handler.validate_prompt_with_llm.return_value = ValidationResult(issues=[])
        mock_handler.suggest_full_fix.return_value = ""
        MockLLM.return_value = mock_handler

        from src.prompt_validator.validator import PromptValidator

        validator = PromptValidator.__new__(PromptValidator)
        validator.llm_handler = mock_handler

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Test prompt content")
            temp_path = f.name

        try:
            result = validator.validate_prompt_file(temp_path)
            self.assertEqual(result["status"], "completed")
            mock_handler.validate_prompt_with_llm.assert_called_once_with(
                "Test prompt content"
            )
        finally:
            os.unlink(temp_path)

    @patch("src.prompt_validator.validator.LLMHandler")
    def test_validate_nonexistent_file_returns_error(self, MockLLM):
        mock_handler = MagicMock()
        MockLLM.return_value = mock_handler

        from src.prompt_validator.validator import PromptValidator

        validator = PromptValidator.__new__(PromptValidator)
        validator.llm_handler = mock_handler

        result = validator.validate_prompt_file("/nonexistent/path.txt")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any("File Error" in i["issue_type"] for i in result["issues"]))

    def test_update_prompt_file_writes_content(self):
        from src.prompt_validator.validator import PromptValidator

        validator = PromptValidator.__new__(PromptValidator)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("old content")
            temp_path = f.name

        try:
            validator.update_prompt_file(temp_path, "new content")
            with open(temp_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "new content")
        finally:
            os.unlink(temp_path)


class TestScoreCalculation(unittest.TestCase):
    """Test the score calculation in the API module."""

    def test_perfect_score(self):
        from api.index import _calculate_score

        score = _calculate_score([])
        self.assertEqual(score, 10.0)

    def test_deductions(self):
        from api.index import _calculate_score, ValidationIssue

        issues = [
            ValidationIssue(
                issue_type="Redundancy",
                description="d",
                suggestion="s",
            ),
            ValidationIssue(
                issue_type="Contradiction",
                description="d",
                suggestion="s",
            ),
        ]
        # 10 - 1.0 (redundancy) - 2.0 (contradiction) = 7.0
        score = _calculate_score(issues)
        self.assertEqual(score, 7.0)

    def test_minimum_score_is_zero(self):
        from api.index import _calculate_score, ValidationIssue

        issues = [
            ValidationIssue(issue_type="Prohibited Content", description="d", suggestion="s"),
            ValidationIssue(issue_type="Prohibited Content", description="d", suggestion="s"),
            ValidationIssue(issue_type="Prohibited Content", description="d", suggestion="s"),
            ValidationIssue(issue_type="Prohibited Content", description="d", suggestion="s"),
        ]
        score = _calculate_score(issues)
        self.assertEqual(score, 0.0)


if __name__ == "__main__":
    unittest.main()