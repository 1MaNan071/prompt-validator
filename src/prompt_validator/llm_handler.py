

import os
from typing import List
from groq import Groq
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from .schemas import ValidationResult, ValidationIssue

load_dotenv()

class LLMHandler:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")
        
        self.llm = ChatGroq(
            temperature=0,
            model_name="llama-3.1-8b-instant",
            api_key=self.api_key,
        )
        self.structured_llm = self.llm.with_structured_output(ValidationResult)

    def validate_prompt_with_llm(self, prompt_content: str) -> ValidationResult:
        
        system_prompt = """You are an expert prompt engineering assistant. Analyze the given prompt and \
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
        
        human_prompt = "Please validate the following prompt text:\n\n---\n\n{prompt_text}"
        
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ]
        )
        
        chain = prompt | self.structured_llm
        
        try:
            validation_result = chain.invoke({"prompt_text": prompt_content})
            return validation_result
        except Exception as e:
            print(f"An error occurred during LLM validation: {e}")
            return ValidationResult(issues=[])

    def suggest_full_fix(self, prompt_content: str, issues: List[ValidationIssue]) -> str:
        if not issues:
            return prompt_content

        issue_summary = "\n".join(f"- **{issue.issue_type}**: {issue.description}" for issue in issues)

        
        system_prompt = """
        You are an expert prompt engineer tasked with rewriting a flawed prompt.
        Your goal is to fix all the identified issues while strictly adhering to the Prompt Strategy Compliance rules.
        The corrected prompt MUST be structured with the following markdown headings:
        
        ### Task
        (A clear, direct description of the task.)

        ### Success Criteria
        (A list of measurable, verifiable conditions for completion.)

        ### Examples with Edge Cases
        (At least one clear example and one edge case. Ensure no PII is present.)

        ### CoT/TOT Steps (if required)
        (If the task is complex, include a 'Chain of Thought' section with step-by-step reasoning instructions. If not needed, omit this section.)
        
        Rewrite the user's original prompt to be a perfect, compliant, and effective prompt.
        Return ONLY the full, corrected prompt text using the specified markdown structure, without any preamble or explanation.
        """

        human_prompt = (
            "Please rewrite the following prompt to fix the issues listed below, ensuring the new version is fully compliant with the required structure.\n\n"
            "**Original Prompt:**\n---\n{original_prompt}\n---\n\n"
            "**Identified Issues:**\n{issues}\n\n"
            "**Corrected, Compliant Prompt:**"
        )
        
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ]
        )
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "original_prompt": prompt_content,
                "issues": issue_summary
            })
            return response.content.strip()
        except Exception as e:
            print(f"Error generating full fix: {e}")
            return "Could not generate a fix due to an error."