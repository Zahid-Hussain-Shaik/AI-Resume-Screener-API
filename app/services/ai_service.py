"""
AI Service — provider-agnostic interface for resume analysis.
Supports OpenAI and Anthropic with structured output, retry logic, and timeout handling.
"""

import json
import logging
from abc import ABC, abstractmethod

import openai
import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  System Prompts
# ──────────────────────────────────────────────

MATCH_PROMPT = """You are an expert resume analyst and career coach. Your task is to analyze how well a resume matches a specific job description.

You MUST respond with valid JSON matching this exact schema — no markdown, no extra text:

{
  "match_score": <number 0-100>,
  "missing_skills": ["skill1", "skill2", ...],
  "rewrite_suggestions": [
    {
      "section": "<section name, e.g. Summary, Experience — Company Name>",
      "original": "<exact text from the resume>",
      "suggested": "<improved version of the text>",
      "rationale": "<why this change helps match the job description>"
    }
  ]
}

Scoring guidelines:
- 90-100: Near-perfect match. Resume strongly aligns with all key requirements.
- 70-89: Good match. Most requirements met, minor gaps.
- 50-69: Moderate match. Several important skills or experiences missing.
- 30-49: Weak match. Major gaps in required qualifications.
- 0-29: Poor match. Resume is for a very different role.

Rules:
1. Be specific about missing skills — list actual technologies, certifications, or experience levels.
2. Provide 3-5 actionable rewrite suggestions. Quote the EXACT original text and provide a concrete improvement.
3. Focus suggestions on sections that would have the highest impact on matching the job description.
4. Do not invent skills the candidate doesn't have — only suggest better phrasing of existing experience.
5. Return ONLY the JSON object — no preamble, no explanation, no markdown fences."""

ATS_PROMPT = """You are an expert Applicant Tracking System (ATS) and professional resume reviewer. Your task is to analyze a resume for overall quality, formatting, and impact.

You MUST respond with valid JSON matching this exact schema — no markdown, no extra text:

{
  "overall_score": <number 0-100>,
  "formatting_score": <number 0-100>,
  "readability_score": <number 0-100>,
  "keyword_score": <number 0-100>,
  "missing_sections": ["Section Name", ...],
  "weak_bullet_points": [
    {
      "original": "<exact text>",
      "issue": "<why it's weak, e.g. lack of metrics>",
      "suggested": "<improved version>"
    }
  ],
  "keyword_analysis": ["keyword1", "keyword2", ...],
  "improvement_suggestions": ["suggestion1", "suggestion2", ...]
}

Scoring guidelines:
- Formatting: Check for consistency, standard headings, and machine readability.
- Readability: Check for clear structure, concise language, and professional tone.
- Keyword Quality: Check for industry-standard skills and action verbs.

Rules:
1. Identify missing standard sections (e.g., Contact, Summary, Experience, Skills, Education).
2. Find "weak" bullet points that lack quantification or impact.
3. Suggest 5-10 keywords that are relevant to the candidate's field but missing.
4. Return ONLY the JSON object — no preamble, no explanation, no markdown fences."""

USER_PROMPT_MATCH = """Analyze the following resume against the job description.

=== RESUME ===
{resume_text}

=== JOB DESCRIPTION ===
{job_description}

Return ONLY the JSON analysis."""

USER_PROMPT_ATS = """Analyze the following resume for ATS optimization and overall quality.

=== RESUME ===
{resume_text}

Return ONLY the JSON analysis."""


# ──────────────────────────────────────────────
#  Base class
# ──────────────────────────────────────────────

class AIService(ABC):
    """Abstract base class for AI analysis providers."""

    @abstractmethod
    async def analyze(
        self, 
        resume_text: str, 
        job_description: str | None = None,
        scan_type: str = "match"
    ) -> dict:
        """
        Analyze a resume (either against a JD or for general ATS).

        Returns:
            dict with analysis results
        """
        ...

    def _build_prompts(self, resume_text: str, job_description: str | None, scan_type: str) -> tuple[str, str]:
        if scan_type == "ats":
            return ATS_PROMPT, USER_PROMPT_ATS.format(resume_text=resume_text)
        else:
            return MATCH_PROMPT, USER_PROMPT_MATCH.format(
                resume_text=resume_text,
                job_description=job_description or "N/A"
            )

    def _parse_response(self, raw: str) -> dict:
        """Parse and validate the AI response JSON."""
        # Strip markdown code fences if the model wraps its response
        text = raw.strip()
        if text.startswith("```"):
            # Remove opening fence (```json or ```)
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI response as JSON: %s", e)
            logger.debug("Raw response: %s", raw[:500])
            raise ValueError(f"AI returned invalid JSON: {e}") from e

        # Validate required keys (basic check for common keys)
        if "overall_score" not in data and "match_score" not in data:
             # If it's ATS but has no overall_score, try to map match_score or vice versa
             if "match_score" in data:
                 data["overall_score"] = data["match_score"]
             elif "overall_score" in data:
                 data["match_score"] = data["overall_score"]
             else:
                 raise ValueError("AI response missing score field")

        # Clamp scores
        if "match_score" in data:
            data["match_score"] = max(0, min(100, float(data["match_score"])))
        if "overall_score" in data:
            data["overall_score"] = max(0, min(100, float(data["overall_score"])))

        return data


# ──────────────────────────────────────────────
#  OpenAI Implementation
# ──────────────────────────────────────────────

class OpenAIService(AIService):
    """Resume analysis using OpenAI's chat completion API."""

    def __init__(self, settings: Settings):
        self.client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.AI_TIMEOUT,
        )
        self.model = settings.OPENAI_MODEL
        self.max_retries = settings.AI_MAX_RETRIES

    @retry(
        retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def analyze(
        self, 
        resume_text: str, 
        job_description: str | None = None,
        scan_type: str = "match"
    ) -> dict:
        logger.info("Calling OpenAI (%s) for %s analysis...", self.model, scan_type)
        sys_prompt, user_prompt = self._build_prompts(resume_text, job_description, scan_type)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        return self._parse_response(raw)


# ──────────────────────────────────────────────
#  Anthropic Implementation
# ──────────────────────────────────────────────

class AnthropicService(AIService):
    """Resume analysis using Anthropic's Claude API."""

    def __init__(self, settings: Settings):
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=settings.AI_TIMEOUT,
        )
        self.model = settings.ANTHROPIC_MODEL
        self.max_retries = settings.AI_MAX_RETRIES

    @retry(
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def analyze(
        self, 
        resume_text: str, 
        job_description: str | None = None,
        scan_type: str = "match"
    ) -> dict:
        logger.info("Calling Anthropic (%s) for %s analysis...", self.model, scan_type)
        sys_prompt, user_prompt = self._build_prompts(resume_text, job_description, scan_type)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=sys_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        # Claude returns content blocks — extract the text
        raw = response.content[0].text
        return self._parse_response(raw)


# ──────────────────────────────────────────────
#  Factory
# ──────────────────────────────────────────────

def get_ai_service(settings: Settings) -> AIService:
    """Factory function — returns the correct AI service based on config."""
    if settings.AI_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER is 'openai'")
        return OpenAIService(settings)
    elif settings.AI_PROVIDER == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required when AI_PROVIDER is 'anthropic'")
        return AnthropicService(settings)
    else:
        raise ValueError(f"Unknown AI provider: {settings.AI_PROVIDER}")
