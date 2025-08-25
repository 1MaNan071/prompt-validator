# src/prompt_validator/schemas.py

from pydantic import BaseModel, Field
from typing import List, Literal

# Define the type of issue found
IssueType = Literal[
    "Redundancy",
    "Contradiction",
    "Missing Section",
    "Prohibited Content",
    "Missing CoT/TOT"  # Added to fully cover compliance rules
]

class ValidationIssue(BaseModel):
    """A single validation issue found in the prompt."""
    issue_type: IssueType = Field(..., description="The category of the issue.")
    description: str = Field(..., description="A detailed description of the specific issue found.")
    suggestion: str = Field(..., description="A concrete suggestion on how to fix this specific issue.")

class ValidationResult(BaseModel):
    """The overall validation result for a prompt, containing a list of all issues."""
    issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="A list of validation issues found in the prompt text."
    )