"""
TalentOpsAI - AI Multi-Touch Email Sequence Generator
=====================================================
Generates high-converting 3-touch cold outreach email cadences for recruiting campaigns:
  - Touch 1 (Day 0): Compelling hook, personalized angle, low-friction ask
  - Touch 2 (Day 3): Value-add context, team mission, candidate growth angle
  - Touch 3 (Day 7): Polite breakup email, keeping the door open
"""

import os
import json
import logging
import requests
from typing import List, Dict, Any

logger = logging.getLogger("talentops.sequence")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


class SequenceGenerator:
    def __init__(self):
        self.api_key = GEMINI_API_KEY

    def generate_sequence(
        self,
        target_role: str = "Senior Software Engineer",
        company_name: str = "our company",
        industry: str = "Technology",
        seniority: str = "Senior",
        value_props: str = "competitive equity, flexible remote culture, rapid scale",
        tone: str = "Professional"
    ) -> Dict[str, Any]:
        """
        Synthesizes a 3-touch outreach sequence tailored to target role and candidate level.
        """
        if self.api_key:
            try:
                ai_res = self._generate_with_gemini(
                    target_role, company_name, industry, seniority, value_props, tone
                )
                if ai_res:
                    return ai_res
            except Exception as e:
                logger.warning("Gemini sequence generation error: %s. Falling back to heuristic builder.", e)

        return self._generate_heuristic_sequence(
            target_role, company_name, industry, seniority, value_props, tone
        )

    def _generate_with_gemini(
        self,
        target_role: str,
        company_name: str,
        industry: str,
        seniority: str,
        value_props: str,
        tone: str
    ) -> Dict[str, Any] | None:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        prompt = f"""
You are an elite executive recruiter and email copywriter.
Generate a high-converting 3-touch cold outreach email cadence for recruiting:
- Target Role: {target_role}
- Company: {company_name}
- Industry: {industry}
- Candidate Seniority: {seniority}
- Value Propositions / Highlights: {value_props}
- Desired Tone: {tone}

Output strictly valid JSON with this schema:
{{
  "sequence_name": "string",
  "touches": [
    {{
      "step": 1,
      "day_delay": 0,
      "touch_type": "Initial Hook",
      "subject": "string",
      "body": "string (use variables like {{first_name}}, {{company}})"
    }},
    {{
      "step": 2,
      "day_delay": 3,
      "touch_type": "Value Follow-up",
      "subject": "string (can use Re: {{subject}} or custom)",
      "body": "string"
    }},
    {{
      "step": 3,
      "day_delay": 7,
      "touch_type": "Graceful Breakup",
      "subject": "string",
      "body": "string"
    }}
  ]
}}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.4}
        }
        res = requests.post(url, json=payload, timeout=8)
        if res.status_code == 200:
            data = res.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text)
        return None

    def _generate_heuristic_sequence(
        self,
        target_role: str,
        company_name: str,
        industry: str,
        seniority: str,
        value_props: str,
        tone: str
    ) -> Dict[str, Any]:
        """
        Deterministic, battle-tested heuristic 3-step outreach templates.
        """
        role_label = target_role or "Engineering Leader"
        comp_label = company_name or "our team"
        val_label = value_props or "rapid scale, impactful architecture, top-tier compensation"

        if tone.lower() == "casual":
            # Casual / Direct Style
            touches = [
                {
                    "step": 1,
                    "day_delay": 0,
                    "touch_type": "Initial Hook",
                    "subject": f"Quick note regarding {role_label} @ {comp_label}",
                    "body": (
                        "Hi {{first_name}},\n\n"
                        f"Came across your profile and was impressed by your track record. We are currently building out key {role_label} capabilities at {comp_label}.\n\n"
                        f"A quick highlight of what we're working on: {val_label}.\n\n"
                        "Do you have 10 minutes sometime this week for a brief introductory sync?\n\n"
                        "Best regards,\n{{sender_name}}\n\n"
                        "P.S. If you're completely happy where you are, reply STOP and I won't follow up!"
                    )
                },
                {
                    "step": 2,
                    "day_delay": 3,
                    "touch_type": "Value Follow-up",
                    "subject": f"Thought you'd find this interesting (re: {role_label} at {comp_label})",
                    "body": (
                        "Hi {{first_name}},\n\n"
                        f"Following up briefly on my note from earlier this week. The team at {comp_label} is solving some fascinating problems in {industry}, and we're looking for someone with your specific experience to shape the technical roadmap.\n\n"
                        "Here's a quick link to our engineering philosophy / recent milestones.\n\n"
                        "Let me know if Thursday or Friday afternoon works for a 10-minute chat!\n\n"
                        "Best,\n{{sender_name}}"
                    )
                },
                {
                    "step": 3,
                    "day_delay": 7,
                    "touch_type": "Graceful Breakup",
                    "subject": f"Permission to close the loop? ({comp_label})",
                    "body": (
                        "Hi {{first_name}},\n\n"
                        f"I know you're likely heads down with ongoing priorities at {{{{company}}}}, so I don't want to crowd your inbox.\n\n"
                        "I'll pause following up for now, but if your situation changes in the future or you'd ever like to connect about opportunities, feel free to reach out anytime.\n\n"
                        "Wishing you continued success,\n{{sender_name}}"
                    )
                }
            ]
        else:
            # Professional / Standard Corporate Style
            touches = [
                {
                    "step": 1,
                    "day_delay": 0,
                    "touch_type": "Initial Hook",
                    "subject": f"{role_label} Opportunity at {comp_label} — Introduction",
                    "body": (
                        "Dear {{first_name}},\n\n"
                        f"I have been following your professional journey in {industry} and wanted to reach out regarding a high-priority {role_label} role we are hiring for at {comp_label}.\n\n"
                        f"Our organization is uniquely positioned with {val_label}, and your background aligns remarkably well with our vision.\n\n"
                        "Would you be open to an exploratory 15-minute introductory conversation this week?\n\n"
                        "Sincerely,\n{{sender_name}}\n\n"
                        "If you prefer not to receive recruiting correspondence, please let me know."
                    )
                },
                {
                    "step": 2,
                    "day_delay": 3,
                    "touch_type": "Value Follow-up",
                    "subject": f"Re: {role_label} Opportunity at {comp_label}",
                    "body": (
                        "Dear {{first_name}},\n\n"
                        f"I wanted to gently follow up on my previous message regarding the {role_label} role with {comp_label}.\n\n"
                        f"Given your expertise, we believe you would play a transformative role in driving our team's mission. We offer competitive compensation, comprehensive benefits, and an environment dedicated to technical excellence.\n\n"
                        "Please let me know if you have availability for a brief call in the coming days.\n\n"
                        "Best regards,\n{{sender_name}}"
                    )
                },
                {
                    "step": 3,
                    "day_delay": 7,
                    "touch_type": "Graceful Breakup",
                    "subject": f"Closing the loop: {role_label} at {comp_label}",
                    "body": (
                        "Dear {{first_name}},\n\n"
                        "I understand that timing is everything and you may not be currently exploring new opportunities.\n\n"
                        "I will not reach out again regarding this specific role, but I would welcome staying connected on LinkedIn for future strategic roles that align with your career goals.\n\n"
                        "Thank you for your time, and I wish you all the best in your current endeavors.\n\n"
                        "Warm regards,\n{{sender_name}}"
                    )
                }
            ]

        return {
            "sequence_name": f"{seniority} {role_label} 3-Touch Cadence",
            "target_role": role_label,
            "company_name": comp_label,
            "tone": tone,
            "touches": touches
        }


sequence_generator = SequenceGenerator()
