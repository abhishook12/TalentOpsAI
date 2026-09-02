"""
Knowledge Graph & Semantic Intelligence API Routes — /knowledge/*

Endpoints:
  GET /knowledge/graph          — Full nodes & edges graph for visual rendering
  GET /knowledge/entities       — Query knowledge entities by type and confidence
  GET /knowledge/relationships  — Query relationships by predicate or entity
  GET /knowledge/signals        — Query staffing, hiring, and business signals
  GET /knowledge/observations   — Extensible typed observations feed
  GET /knowledge/stats          — High-level intelligence graph metrics
"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from ..database import get_db
from ..models.knowledge_models import KnowledgeEntity, KnowledgeRelationship, KnowledgeSignal, SemanticObservation
from ..models.auth_models import User
from ..services.auth_service import get_current_user_from_request

router = APIRouter(prefix="/knowledge", tags=["Knowledge Graph"])


@router.get("/stats")
def get_knowledge_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns aggregate knowledge graph metrics for the intelligence center.
    """
    total_entities = db.query(sqlfunc.count(KnowledgeEntity.id)).filter(KnowledgeEntity.owner_user_id == current_user.id).scalar() or 0
    total_relationships = db.query(sqlfunc.count(KnowledgeRelationship.id)).filter(KnowledgeRelationship.owner_user_id == current_user.id).scalar() or 0
    total_signals = db.query(sqlfunc.count(KnowledgeSignal.id)).filter(KnowledgeSignal.owner_user_id == current_user.id).scalar() or 0
    total_observations = db.query(sqlfunc.count(SemanticObservation.id)).filter(SemanticObservation.owner_user_id == current_user.id).scalar() or 0

    # Entity type breakdown
    type_counts = (
        db.query(KnowledgeEntity.entity_type, sqlfunc.count(KnowledgeEntity.id))
        .filter(KnowledgeEntity.owner_user_id == current_user.id)
        .group_by(KnowledgeEntity.entity_type)
        .all()
    )

    # Signal type breakdown
    signal_counts = (
        db.query(KnowledgeSignal.signal_type, sqlfunc.count(KnowledgeSignal.id))
        .filter(KnowledgeSignal.owner_user_id == current_user.id)
        .group_by(KnowledgeSignal.signal_type)
        .all()
    )

    return {
        "total_entities": total_entities,
        "total_relationships": total_relationships,
        "total_signals": total_signals,
        "total_observations": total_observations,
        "entity_types": {t: c for t, c in type_counts},
        "signal_types": {s: c for s, c in signal_counts},
    }


@router.get("/graph")
def get_knowledge_graph(
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns graph nodes and edges suitable for D3 / Vis.js / React Flow visualizers.
    """
    entities = (
        db.query(KnowledgeEntity)
        .filter(KnowledgeEntity.owner_user_id == current_user.id)
        .order_by(KnowledgeEntity.id.desc())
        .limit(limit)
        .all()
    )

    ent_ids = {e.id for e in entities}

    relationships = (
        db.query(KnowledgeRelationship)
        .filter(
            KnowledgeRelationship.owner_user_id == current_user.id,
            KnowledgeRelationship.subject_entity_id.in_(ent_ids),
            KnowledgeRelationship.object_entity_id.in_(ent_ids)
        )
        .limit(limit * 2)
        .all()
    )

    nodes = [
        {
            "id": f"node_{e.id}",
            "entity_id": e.id,
            "label": e.canonical_name,
            "type": e.entity_type,
            "confidence": e.confidence,
            "identifier": e.primary_identifier,
            "attributes": json.loads(e.attributes_json) if e.attributes_json else {},
        }
        for e in entities
    ]

    edges = [
        {
            "id": f"edge_{r.id}",
            "source": f"node_{r.subject_entity_id}",
            "target": f"node_{r.object_entity_id}",
            "label": r.predicate,
            "is_current": r.is_current,
            "attributes": json.loads(r.attributes_json) if r.attributes_json else {},
        }
        for r in relationships
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


@router.get("/entities")
def list_knowledge_entities(
    entity_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns list of knowledge entities.
    """
    q = db.query(KnowledgeEntity).filter(KnowledgeEntity.owner_user_id == current_user.id)
    if entity_type:
        q = q.filter(KnowledgeEntity.entity_type == entity_type)

    total = q.count()
    entities = q.order_by(KnowledgeEntity.id.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "entities": [
            {
                "id": e.id,
                "entity_type": e.entity_type,
                "canonical_name": e.canonical_name,
                "primary_identifier": e.primary_identifier,
                "confidence": e.confidence,
                "attributes": json.loads(e.attributes_json) if e.attributes_json else {},
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entities
        ]
    }


@router.get("/signals")
def list_knowledge_signals(
    signal_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns staffing, hiring, and business intelligence signals.
    """
    q = db.query(KnowledgeSignal).filter(KnowledgeSignal.owner_user_id == current_user.id)
    if signal_type:
        q = q.filter(KnowledgeSignal.signal_type == signal_type)

    signals = q.order_by(KnowledgeSignal.id.desc()).limit(limit).all()

    return {
        "total": len(signals),
        "signals": [
            {
                "id": s.id,
                "signal_type": s.signal_type,
                "title": s.title,
                "description": s.description,
                "payload": json.loads(s.payload_json) if s.payload_json else {},
                "confidence": s.confidence,
                "source_url": s.source_url,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in signals
        ]
    }


@router.get("/observations")
def list_semantic_observations(
    semantic_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns raw extensible observations stream.
    """
    q = db.query(SemanticObservation).filter(SemanticObservation.owner_user_id == current_user.id)
    if semantic_type:
        q = q.filter(SemanticObservation.semantic_type == semantic_type)

    observations = q.order_by(SemanticObservation.id.desc()).limit(limit).all()

    return {
        "total": len(observations),
        "observations": [
            {
                "id": o.id,
                "subject": o.subject,
                "predicate": o.predicate,
                "object_val": o.object_val,
                "semantic_type": o.semantic_type,
                "context": o.context,
                "confidence": o.confidence,
                "attributes": json.loads(o.attributes_json) if o.attributes_json else {},
                "source_url": o.source_url,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in observations
        ]
    }
