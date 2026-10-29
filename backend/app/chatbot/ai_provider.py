"""Optional AI Fallback Provider for CampusIQ (JDCOEM).

Supports Google Gemini and OpenAI REST APIs with grounded institutional system prompting,
strict timeout handling, and graceful offline degradation.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Grounded institutional system prompt for JDCOEM & MCA Department
GROUNDED_SYSTEM_PROMPT = """You are CampusIQ, the official intelligent college inquiry AI assistant for JD College of Engineering and Management (JDCOEM), Nagpur.
You have a special primary focus on the Master of Computer Applications (MCA) department and broader autonomous engineering disciplines.

VERIFIED INSTITUTIONAL FACTS:
- College Name: JD College of Engineering and Management (JDCOEM), Nagpur
- Status: Autonomous Institute, approved by AICTE, recognized by DTE Maharashtra (DTE Code: 04138, MCA Choice Code: 413824110)
- Accreditation: NAAC 'A' Grade Accredited
- Affiliation: Dr. Babasaheb Ambedkar Technological University (DBATU), Lonere
- Motto: "Education to Eternity"
- Principal & Director: Dr. Shrikant V. Sonekar (Ph.D. Electronics, 25+ years experience)
- MCA Department Head (HOD): Prof. Rohan Kokate (M.C.A., Ph.D. Pursuing; Cloud & Web Technologies)
- MCA Project Coordinator & TBI Mentor: Prof. Chetan Padole (M.C.A., M.Tech; Machine Learning & Capstone Projects)
- MCA Program: 2-Year Full-Time PG (Intake 120 seats). Eligibility: BCA / B.Sc.(CS/IT) or Bachelor Degree with Mathematics with 50% marks (45% for Maharashtra reserved) and valid MAH-MCA-CET score.
- MCA Fee Structure (FRA Sanctioned): ₹91,500 per year (Tuition ₹78,000 + Dev ₹10,000 + Other ₹3,500). Total 2-year: ₹1,83,000. State scholarship concessions apply.
- B.Tech CSE Fee: ₹1,00,000 per year; MBA: ₹87,500 per year.
- Innovation & Incubation: Technology Business Incubator (TBI) on campus pre-incubates student software projects into commercial startups.
- Key Infrastructure: Central Digital Library (30,000+ volumes, IEEE Xplore, DELNET), AI & GPU Labs, Fleet Bus Transportation across 20+ Nagpur city routes, On-campus Hostels with mess dining.
- Attendance Regulation: Minimum 75% attendance in theory and practicals is strictly mandatory under DBATU/JDCOEM Autonomous regulations.
- Anti-Ragging: Zero tolerance policy under the Maharashtra Prohibition of Ragging Act.
- Placements: Top recruiters include TCS, Infosys, Wipro, Capgemini, Cognizant, Tech Mahindra, L&T Infotech, and Persistent Systems (Highest package: 12+ LPA, Average: 4.5 LPA).
- Contact: Khandala/Valni, Near Hanuman Temple, Borgaon Fata, Kalmeshwar Road, Nagpur — 441501. Phone: +91-90110 10038 / +91-7774041329, Email: info@jdcoem.ac.in.

RULES FOR YOUR RESPONSES:
1. Provide accurate, polite, and concise answers based on the verified facts above.
2. Emphasize MCA department excellence, industry alignment, and TBI startup mentoring where relevant.
3. Never invent non-existent courses or false fee structures.
4. If an inquiry cannot be verified from the facts above, politely instruct the user to contact the JDCOEM administrative helpline at +91-90110 10038 or visit https://jdcoem.ac.in.
5. Format output using clean GitHub-style Markdown.
"""


_SENTINEL = object()


class AIProvider:
    """Manages grounded AI fallback requests via Google Gemini or OpenAI."""

    def __init__(
        self,
        provider: Any = _SENTINEL,
        api_key: Any = _SENTINEL,
        model_name: Any = _SENTINEL,
        timeout_seconds: Any = _SENTINEL,
    ):
        raw_prov = settings.AI_PROVIDER if provider is _SENTINEL else provider
        self.provider = (raw_prov or "").lower().strip()
        self.api_key = settings.AI_API_KEY if api_key is _SENTINEL else api_key
        self.model_name = (
            settings.AI_MODEL_NAME if model_name is _SENTINEL else (model_name or settings.AI_MODEL_NAME)
        )
        self.timeout = (
            settings.AI_TIMEOUT_SECONDS if timeout_seconds is _SENTINEL else (timeout_seconds or settings.AI_TIMEOUT_SECONDS)
        )

    def is_available(self) -> bool:
        """Check whether a supported AI provider and API key are configured."""
        if not self.api_key or not self.provider:
            return False
        return self.provider in ("gemini", "google", "openai")

    def generate_response(self, user_query: str) -> Optional[Dict[str, str]]:
        """Synchronously query the configured LLM provider with timeout and fallback."""
        if not self.is_available():
            return None

        try:
            if self.provider in ("gemini", "google"):
                return self._call_gemini(user_query)
            elif self.provider == "openai":
                return self._call_openai(user_query)
        except Exception as e:
            logger.warning("AI fallback provider call failed: %s", e)
            return None

        return None

    def _call_gemini(self, user_query: str) -> Optional[Dict[str, str]]:
        """Call Google Gemini generateContent REST endpoint."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"{GROUNDED_SYSTEM_PROMPT}\n\nStudent Inquiry: {user_query}"}
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 600,
            },
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "").strip()
                        if text:
                            return {
                                "text": text,
                                "source": f"Google Gemini ({self.model_name}) Grounded Model",
                            }
            else:
                logger.warning("Gemini API error: %s - %s", response.status_code, response.text)
                return None
        return None

    def _call_openai(self, user_query: str) -> Optional[Dict[str, str]]:
        """Call OpenAI chat/completions REST endpoint."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": GROUNDED_SYSTEM_PROMPT},
                {"role": "user", "content": user_query},
            ],
            "temperature": 0.2,
            "max_tokens": 600,
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "").strip()
                    if text:
                        return {
                            "text": text,
                            "source": f"OpenAI ({self.model_name or 'gpt-4o-mini'}) Grounded Model",
                        }
            else:
                logger.warning("OpenAI API error: %s - %s", response.status_code, response.text)
                return None
        return None
