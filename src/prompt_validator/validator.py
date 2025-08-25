# src/prompt_validator/validator.py

import os
from typing import Dict, List, Any
from .llm_handler import LLMHandler

class PromptValidator:
    def __init__(self):
        """Initializes the validator with an LLM handler."""
        self.llm_handler = LLMHandler()

    def validate_prompt_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validates a single prompt file using the LLM-based handler.

        Args:
            file_path: The path to the prompt file.

        Returns:
            A dictionary containing the validation results.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {
                "file": os.path.basename(file_path),
                "issues": [{"issue_type": "File Error", "description": f"Could not read file: {e}", "suggestion": "Check file permissions and encoding."}],
                "suggestion": None,
                "status": "error"
            }

        # Use the LLM handler to get a structured validation result
        validation_result = self.llm_handler.validate_prompt_with_llm(content)
        
        issues = [issue.dict() for issue in validation_result.issues]
        suggestion = None

        if issues:
            # If issues are found, get a suggestion for a full fix
            suggestion = self.llm_handler.suggest_full_fix(content, validation_result.issues)

        return {
            "file": os.path.basename(file_path),
            "issues": issues,
            "suggestion": suggestion, # This will hold the full corrected prompt text
            "status": "completed"
        }

    def validate_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """
        Validates all .txt prompt files in a given directory.

        Args:
            directory_path: The path to the directory containing prompt files.

        Returns:
            A list of validation result dictionaries for each file.
        """
        results = []
        for filename in os.listdir(directory_path):
            if filename.endswith('.txt'):
                file_path = os.path.join(directory_path, filename)
                result = self.validate_prompt_file(file_path)
                results.append(result)
        return results

    def update_prompt_file(self, file_path: str, new_content: str):
        """
        Overwrites a prompt file with new, corrected content.

        Args:
            file_path: The path to the file to update.
            new_content: The new content to write to the file.
        """

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except Exception as e:
            print(f"Error updating file {file_path}: {e}")