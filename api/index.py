"""
Prompt Validator API — FastAPI serverless function for Vercel.
Validates prompts against 4 conditions and generates fixes using Groq LLM.
"""

import os
import json
from pathlib import Path
from typing import List, Optional, Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

load_dotenv()

# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Prompt Validator API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Schemas ──────────────────────────────────────────────────────────────────

IssueType = Literal[
    "Redundancy",
    "Contradiction",
    "Missing Section",
    "Prohibited Content",
    "Missing CoT/TOT",
]


class ValidationIssue(BaseModel):
    issue_type: IssueType = Field(..., description="The category of the issue.")
    description: str = Field(..., description="A detailed description of the issue.")
    suggestion: str = Field(..., description="A concrete suggestion to fix the issue.")


class LLMValidationResult(BaseModel):
    issues: List[ValidationIssue] = Field(default_factory=list)


class PromptInput(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=50000)
    api_key: Optional[str] = Field(
        None, description="Optional Groq API key. Uses server key if not provided."
    )


class IssueResponse(BaseModel):
    issue_type: str
    description: str
    suggestion: str


class ValidateResponse(BaseModel):
    status: str
    score: float
    issues: List[IssueResponse]
    fixed_prompt: Optional[str] = None
    summary: dict
    original_prompt: str


# ─── Constants ────────────────────────────────────────────────────────────────

MODEL_NAME = "llama-3.1-8b-instant"

ISSUE_WEIGHTS = {
    "Redundancy": 1.0,
    "Contradiction": 2.0,
    "Missing Section": 1.5,
    "Prohibited Content": 3.0,
    "Missing CoT/TOT": 0.5,
}

VALIDATION_SYSTEM_PROMPT = """\
You are an expert prompt engineering assistant. Analyze the given prompt and \
validate it against these rules. Identify ALL issues — do not skip any.

**Validation Rules (4 categories):**

1. **Redundancy** — Flag repetitive phrases, duplicate instructions, or \
   unnecessarily verbose wording that adds no value.

2. **Contradiction** — Flag conflicting requirements or instructions that \
   cannot both be true (e.g., "be brief" + "write 10,000 words").

3. **Missing Section** — A complete prompt MUST contain these sections. Flag \
   any that are absent:
   - Task: A clear description of what to do.
   - Success Criteria: Measurable, verifiable conditions for completion.
   - Examples with Edge Cases: At least one example, including an edge case.
   - CoT/TOT Steps (if required): Chain of Thought / Tree of Thought steps \
     for complex tasks.

4. **Prohibited Content** — Flag any PII (names, emails, phone numbers, \
   addresses) or secrets (API keys, passwords, credentials).

For each issue found, provide a clear description and a concrete suggestion. \
If no issues are found, return an empty list."""

FIX_SYSTEM_PROMPT = """\
You are an expert prompt engineer. Rewrite the flawed prompt to fix ALL \
identified issues while strictly following this structure:

### Task
(A clear, direct description of the task.)

### Success Criteria
(A list of measurable, verifiable conditions for completion.)

### Examples with Edge Cases
(At least one clear example and one edge case. Remove ALL PII.)

### CoT/TOT Steps (if required)
(If the task is complex, include step-by-step reasoning instructions. \
If not needed, omit this section entirely.)

Return ONLY the corrected prompt using the structure above. \
No preamble, no explanation — just the prompt."""


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_llm(api_key: str) -> ChatGroq:
    return ChatGroq(temperature=0, model_name=MODEL_NAME, api_key=api_key)


def _calculate_score(issues: List[ValidationIssue]) -> float:
    deductions = sum(ISSUE_WEIGHTS.get(i.issue_type, 1.0) for i in issues)
    return max(0.0, round(10.0 - deductions, 1))


def _validate_with_llm(prompt_text: str, api_key: str) -> LLMValidationResult:
    llm = _get_llm(api_key)
    structured_llm = llm.with_structured_output(LLMValidationResult)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", VALIDATION_SYSTEM_PROMPT),
            (
                "human",
                "Please validate the following prompt text:\n\n---\n\n{prompt_text}",
            ),
        ]
    )

    chain = prompt | structured_llm
    result = chain.invoke({"prompt_text": prompt_text})
    return result


def _generate_fix(
    prompt_text: str, issues: List[ValidationIssue], api_key: str
) -> str:
    llm = _get_llm(api_key)
    issue_summary = "\n".join(
        f"- **{issue.issue_type}**: {issue.description}" for issue in issues
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", FIX_SYSTEM_PROMPT),
            (
                "human",
                "Rewrite the following prompt to fix all listed issues.\n\n"
                "**Original Prompt:**\n---\n{original_prompt}\n---\n\n"
                "**Identified Issues:**\n{issues}\n\n"
                "**Corrected, Compliant Prompt:**",
            ),
        ]
    )

    chain = prompt | llm
    response = chain.invoke(
        {"original_prompt": prompt_text, "issues": issue_summary}
    )
    return response.content.strip()


# ─── Routes ───────────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "model": MODEL_NAME}


@app.post("/api/validate", response_model=ValidateResponse)
async def validate(data: PromptInput):
    # Resolve API key
    api_key = data.api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="No API key provided. Set GROQ_API_KEY in environment or pass api_key in the request body.",
        )

    prompt_text = data.prompt.strip()
    if not prompt_text:
        raise HTTPException(status_code=400, detail="Prompt text cannot be empty.")

    try:
        # Step 1: Validate with LLM
        validation_result = _validate_with_llm(prompt_text, api_key)
        issues = validation_result.issues

        # Step 2: Calculate score
        score = _calculate_score(issues)

        # Step 3: Generate fix if there are issues
        fixed_prompt = None
        if issues:
            fixed_prompt = _generate_fix(prompt_text, issues, api_key)

        # Step 4: Build summary
        categories: dict = {}
        for issue in issues:
            categories[issue.issue_type] = categories.get(issue.issue_type, 0) + 1

        return ValidateResponse(
            status="success",
            score=score,
            issues=[
                IssueResponse(
                    issue_type=i.issue_type,
                    description=i.description,
                    suggestion=i.suggestion,
                )
                for i in issues
            ],
            fixed_prompt=fixed_prompt,
            summary={"total_issues": len(issues), "categories": categories},
            original_prompt=prompt_text,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


# ─── Static Files (local dev — Vercel serves public/ automatically) ──────────

_public_dir = Path(__file__).resolve().parent.parent / "public"

if _public_dir.is_dir():

    @app.get("/")
    async def serve_ui():
        return FileResponse(str(_public_dir / "index.html"))

    app.mount("/", StaticFiles(directory=str(_public_dir)), name="static")
