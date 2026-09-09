"""
source_connector_base.py — Pluggable Multi-Source Connector Architecture.

Supports:
- Authorized official connectors (LinkedIn, Apollo, ZoomInfo, Hunter, ContactOut)
- Enterprise Chat Integrations (Google Chat, Microsoft Teams)
- Edge Desktop Client (Scout Edge)
Strictly adheres to official API/webhook protocols, scope validation,
and immutable raw observation recording with SHA-256 idempotency.
"""

from __future__ import annotations

import abc
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("talentops.source_connectors")


class BaseSourceConnector(abc.ABC):
    """
    Abstract contract for all data ingestion sources.
    Every connector must implement authorization checks, payload normalization,
    and field-level observation extraction without mutating raw evidence.
    """

    connector_key: str
    source_type: str
    name: str
    auth_type: str
    source_reliability: float
    field_reliability: Dict[str, float]
    cost_per_query_usd: float
    supported_data_categories: List[str]
    rate_limit_rpm: int

    def __init__(
        self,
        connector_key: str,
        source_type: str,
        name: str,
        auth_type: str = "API_KEY",
        source_reliability: float = 0.85,
        field_reliability: Optional[Dict[str, float]] = None,
        cost_per_query_usd: float = 0.0,
        supported_data_categories: Optional[List[str]] = None,
        rate_limit_rpm: int = 60,
    ):
        self.connector_key = connector_key
        self.source_type = source_type
        self.name = name
        self.auth_type = auth_type
        self.source_reliability = max(0.0, min(1.0, source_reliability))
        self.field_reliability = field_reliability or {
            "full_name": self.source_reliability,
            "current_company": self.source_reliability,
            "current_title": self.source_reliability,
            "primary_email": self.source_reliability,
            "primary_phone": self.source_reliability,
            "linkedin_url": self.source_reliability,
        }
        self.cost_per_query_usd = max(0.0, cost_per_query_usd)
        self.supported_data_categories = supported_data_categories or ["identity"]
        self.rate_limit_rpm = rate_limit_rpm

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Validates official API keys, tokens, or pairing secrets.
        Default implementation checks presence of non-empty secret.
        """
        if not credentials:
            return False
        token = credentials.get("api_key") or credentials.get("access_token") or credentials.get("pairing_token")
        return bool(token and len(str(token).strip()) > 6)

    def validate_scope(self, granted_scopes: List[str], required_scope: str) -> bool:
        """
        Enforces that the connection holds the authorized scope before fetching.
        """
        if not required_scope:
            return True
        if "*" in granted_scopes or "admin" in granted_scopes:
            return True
        return required_scope in granted_scopes

    def compute_payload_hash(self, payload: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 hash of the verbatim payload."""
        canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def create_raw_record_dict(
        self,
        source_object_type: str,
        source_object_id: str,
        raw_payload: Dict[str, Any],
        authorization_scope: str = "authorized",
        provenance: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Produces the standardized dictionary for persisting an immutable RawSignal / RawSourceRecord.
        """
        content_hash = self.compute_payload_hash(raw_payload)
        return {
            "source_type": self.source_type,
            "source_object_type": source_object_type,
            "source_object_id": str(source_object_id),
            "content_hash": content_hash,
            "authorization_scope": authorization_scope,
            "raw_payload": json.dumps(raw_payload),
            "provenance_json": json.dumps(provenance or {"connector_key": self.connector_key}),
            "ingested_at": datetime.now(timezone.utc),
        }

    @abc.abstractmethod
    def normalize_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardizes raw source payload into a dictionary of recognized person/company fields.
        """
        pass

    def extract_field_observations(
        self,
        entity_type: str,
        entity_id: int,
        normalized_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Decomposes normalized data into individual field observations with specific confidence scores.
        """
        observations = []
        now = datetime.now(timezone.utc)
        for field, val in normalized_data.items():
            if val is not None and str(val).strip():
                field_conf = self.field_reliability.get(field, self.source_reliability)
                observations.append({
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "field_name": field,
                    "field_value": str(val).strip(),
                    "source": self.source_type,
                    "confidence": field_conf,
                    "observed_at": now,
                })
        return observations


# ── Concrete Connectors ───────────────────────────────────────────────────────

class LinkedInSourceConnector(BaseSourceConnector):
    """Controlled LinkedIn Connector with explicit permission scopes."""

    def __init__(self, connector_key: str = "LINKEDIN-CONTROLLED"):
        super().__init__(
            connector_key=connector_key,
            source_type="LINKEDIN",
            name="LinkedIn Controlled Connector",
            auth_type="OAUTH2",
            source_reliability=0.95,
            field_reliability={
                "full_name": 0.98,
                "current_company": 0.94,
                "current_title": 0.95,
                "primary_email": 0.85,
                "primary_phone": 0.80,
                "linkedin_url": 0.99,
            },
            cost_per_query_usd=0.00,
            supported_data_categories=["identity", "employment", "education", "skills"],
            rate_limit_rpm=100,
        )

    def normalize_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "full_name": raw_payload.get("name") or raw_payload.get("formatted_name") or f"{raw_payload.get('firstName', '')} {raw_payload.get('lastName', '')}".strip(),
            "current_company": raw_payload.get("company") or raw_payload.get("company_name") or raw_payload.get("headline_company"),
            "current_title": raw_payload.get("title") or raw_payload.get("headline"),
            "primary_email": raw_payload.get("email"),
            "primary_phone": raw_payload.get("phone"),
            "linkedin_url": raw_payload.get("linkedin_url") or raw_payload.get("public_identifier"),
            "location": raw_payload.get("location"),
        }


class ApolloSourceConnector(BaseSourceConnector):
    """Official Apollo.io API Connector for contact enrichment."""

    def __init__(self, connector_key: str = "APOLLO-OFFICIAL"):
        super().__init__(
            connector_key=connector_key,
            source_type="APOLLO",
            name="Apollo.io Contact Intelligence",
            auth_type="API_KEY",
            source_reliability=0.88,
            field_reliability={
                "full_name": 0.90,
                "current_company": 0.88,
                "current_title": 0.88,
                "primary_email": 0.92,
                "primary_phone": 0.82,
                "linkedin_url": 0.90,
            },
            cost_per_query_usd=0.03,
            supported_data_categories=["email", "phone", "employment", "company_firmographics"],
            rate_limit_rpm=120,
        )

    def normalize_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        contact = raw_payload.get("person") or raw_payload
        org = contact.get("organization") or {}
        return {
            "full_name": contact.get("name") or f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
            "current_company": org.get("name") or contact.get("organization_name"),
            "current_title": contact.get("title"),
            "primary_email": contact.get("email"),
            "primary_phone": contact.get("sanitized_phone") or contact.get("phone_number"),
            "linkedin_url": contact.get("linkedin_url"),
            "location": f"{contact.get('city', '')}, {contact.get('state', '')}".strip(", "),
        }


class HunterSourceConnector(BaseSourceConnector):
    """Official Hunter.io Email Verification & Pattern Connector."""

    def __init__(self, connector_key: str = "HUNTER-OFFICIAL"):
        super().__init__(
            connector_key=connector_key,
            source_type="HUNTER",
            name="Hunter.io Email Intelligence",
            auth_type="API_KEY",
            source_reliability=0.86,
            field_reliability={
                "primary_email": 0.94,
                "current_company": 0.80,
                "company_domain": 0.95,
            },
            cost_per_query_usd=0.02,
            supported_data_categories=["email", "company_domain", "email_pattern"],
            rate_limit_rpm=60,
        )

    def normalize_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        data = raw_payload.get("data") or raw_payload
        return {
            "full_name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            "current_company": data.get("company"),
            "current_title": data.get("position"),
            "primary_email": data.get("email"),
            "company_domain": data.get("domain"),
        }


class ZoomInfoSourceConnector(BaseSourceConnector):
    """Official ZoomInfo Enterprise Firmographic & Contact Connector."""

    def __init__(self, connector_key: str = "ZOOMINFO-OFFICIAL"):
        super().__init__(
            connector_key=connector_key,
            source_type="ZOOMINFO",
            name="ZoomInfo Enterprise Intelligence",
            auth_type="API_KEY",
            source_reliability=0.91,
            field_reliability={
                "full_name": 0.92,
                "current_company": 0.93,
                "current_title": 0.91,
                "primary_email": 0.89,
                "primary_phone": 0.90,
                "linkedin_url": 0.88,
            },
            cost_per_query_usd=0.10,
            supported_data_categories=["phone", "email", "firmographics", "org_chart"],
            rate_limit_rpm=60,
        )

    def normalize_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "full_name": raw_payload.get("fullName") or f"{raw_payload.get('firstName', '')} {raw_payload.get('lastName', '')}".strip(),
            "current_company": raw_payload.get("companyName"),
            "current_title": raw_payload.get("jobTitle"),
            "primary_email": raw_payload.get("emailAddress"),
            "primary_phone": raw_payload.get("directPhone") or raw_payload.get("phone"),
            "linkedin_url": raw_payload.get("linkedInUrl"),
        }


class ContactOutSourceConnector(BaseSourceConnector):
    """Official ContactOut Direct Phone & Personal Email Connector."""

    def __init__(self, connector_key: str = "CONTACTOUT-OFFICIAL"):
        super().__init__(
            connector_key=connector_key,
            source_type="CONTACTOUT",
            name="ContactOut Direct Contact Engine",
            auth_type="API_KEY",
            source_reliability=0.87,
            field_reliability={
                "full_name": 0.88,
                "primary_email": 0.90,
                "primary_phone": 0.92,
                "linkedin_url": 0.94,
            },
            cost_per_query_usd=0.04,
            supported_data_categories=["phone", "email", "personal_email"],
            rate_limit_rpm=90,
        )

    def normalize_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "full_name": raw_payload.get("name"),
            "current_company": raw_payload.get("company"),
            "current_title": raw_payload.get("title"),
            "primary_email": raw_payload.get("email") or (raw_payload.get("emails") or [None])[0],
            "primary_phone": raw_payload.get("phone") or (raw_payload.get("phones") or [None])[0],
            "linkedin_url": raw_payload.get("linkedin"),
        }


class ScoutEdgeSourceConnector(BaseSourceConnector):
    """Paired Scout Desktop Client Connector with native Windows OCR."""

    def __init__(self, connector_key: str = "SCOUT-EDGE-PROD"):
        super().__init__(
            connector_key=connector_key,
            source_type="SCOUT_EDGE",
            name="TalentOps Scout Desktop Edge",
            auth_type="DESKTOP_PAIRING",
            source_reliability=0.92,
            field_reliability={
                "full_name": 0.95,
                "current_company": 0.92,
                "current_title": 0.93,
                "primary_email": 0.88,
                "primary_phone": 0.85,
                "linkedin_url": 0.98,
            },
            cost_per_query_usd=0.00,
            supported_data_categories=["identity", "contact", "visual_ocr", "recruiter_action"],
            rate_limit_rpm=300,
        )

    def normalize_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "full_name": raw_payload.get("recruiter_name") or raw_payload.get("canonical_name") or raw_payload.get("raw_name"),
            "current_company": raw_payload.get("company_name") or raw_payload.get("raw_company"),
            "current_title": raw_payload.get("title") or raw_payload.get("raw_title"),
            "primary_email": raw_payload.get("email") or raw_payload.get("raw_email"),
            "primary_phone": raw_payload.get("phone") or raw_payload.get("raw_phone"),
            "linkedin_url": raw_payload.get("linkedin_url") or raw_payload.get("raw_linkedin"),
            "location": raw_payload.get("location") or raw_payload.get("raw_location"),
        }


class GoogleChatSourceConnector(BaseSourceConnector):
    """Google Chat Webhook / Workspace App Connector for unstructured recruiter notes."""

    def __init__(self, connector_key: str = "GOOGLE-CHAT-WORKSPACE"):
        super().__init__(
            connector_key=connector_key,
            source_type="GOOGLE_CHAT",
            name="Google Chat Workspace Connector",
            auth_type="WEBHOOK",
            source_reliability=0.76,
            field_reliability={
                "full_name": 0.80,
                "current_company": 0.75,
                "current_title": 0.75,
                "primary_email": 0.85,
                "primary_phone": 0.85,
            },
            cost_per_query_usd=0.00,
            supported_data_categories=["chat_notes", "contact_fragments"],
            rate_limit_rpm=120,
        )

    def normalize_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        text = raw_payload.get("text") or raw_payload.get("message", {}).get("text") or ""
        return {"raw_text": text, "sender": raw_payload.get("sender", {}).get("displayName")}


class MicrosoftTeamsSourceConnector(BaseSourceConnector):
    """Microsoft Teams Graph API Webhook / Bot Connector."""

    def __init__(self, connector_key: str = "MS-TEAMS-GRAPH"):
        super().__init__(
            connector_key=connector_key,
            source_type="MICROSOFT_TEAMS",
            name="Microsoft Teams Connector",
            auth_type="OAUTH2",
            source_reliability=0.76,
            field_reliability={
                "full_name": 0.80,
                "current_company": 0.75,
                "current_title": 0.75,
                "primary_email": 0.85,
                "primary_phone": 0.85,
            },
            cost_per_query_usd=0.00,
            supported_data_categories=["chat_notes", "contact_fragments"],
            rate_limit_rpm=120,
        )

    def normalize_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        text = raw_payload.get("body", {}).get("content") or raw_payload.get("text") or ""
        return {"raw_text": text, "sender": raw_payload.get("from", {}).get("user", {}).get("displayName")}


# ── Registry ──────────────────────────────────────────────────────────────────

class SourceConnectorRegistry:
    """Singleton-style registry for looking up and managing source connectors."""

    _connectors: Dict[str, BaseSourceConnector] = {}

    @classmethod
    def register(cls, connector: BaseSourceConnector) -> None:
        cls._connectors[connector.connector_key] = connector
        cls._connectors[connector.source_type] = connector

    @classmethod
    def get(cls, key_or_type: str) -> Optional[BaseSourceConnector]:
        return cls._connectors.get(key_or_type)

    @classmethod
    def list_all(cls) -> List[BaseSourceConnector]:
        seen = set()
        unique = []
        for c in cls._connectors.values():
            if c.connector_key not in seen:
                seen.add(c.connector_key)
                unique.append(c)
        return unique


# Pre-register built-in connectors
for conn in [
    LinkedInSourceConnector(),
    ApolloSourceConnector(),
    HunterSourceConnector(),
    ZoomInfoSourceConnector(),
    ContactOutSourceConnector(),
    ScoutEdgeSourceConnector(),
    GoogleChatSourceConnector(),
    MicrosoftTeamsSourceConnector(),
]:
    SourceConnectorRegistry.register(conn)
