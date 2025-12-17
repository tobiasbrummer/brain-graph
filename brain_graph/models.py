#!/usr/bin/env python3
"""
Pydantic models generated from JSON schemas.
Single source of truth for data validation across the pipeline.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ============================================================================
# Node Types
# ============================================================================


class Section(BaseModel):
    """Document structure section (heading hierarchy)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^(sec_[a-f0-9]{8,12}|[0-9A-HJKMNP-TV-Z]{26})$")
    ulid: str = Field(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")
    title: str = Field(min_length=1)
    level: int = Field(ge=1, le=6, description="Heading level 1-6")


class Chunk(BaseModel):
    """Text chunk with content-addressable ID."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^(chunk_[a-f0-9]{8,12}|[0-9A-HJKMNP-TV-Z]{26})$")
    ulid: str = Field(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")
    doc_id: str = Field(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")
    chunk_id: str = Field(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}:[a-f0-9]{12}$")
    chunk_hash: str = Field(pattern=r"^[a-f0-9]{12}$")
    chunk_index: int = Field(ge=0)
    text: str = Field(min_length=1)
    tokens: int = Field(ge=0)
    language: str = Field(pattern=r"^[a-z]{2}$")
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    summary: Optional[str] = None
    categories: list[str] = Field(default_factory=list)


class EntityType(str, Enum):
    """Named entity types from spaCy NER."""

    PER = "PER"  # Person
    LOC = "LOC"  # Location
    ORG = "ORG"  # Organization
    MISC = "MISC"  # Miscellaneous
    AGENT = "AGENT"  # AI Agent or User


class AgentProfile(BaseModel):
    """Configuration for AGENT entities."""

    model_config = ConfigDict(extra="allow")

    model_name: Optional[str] = Field(None, alias="model")
    status: Optional[Literal["active", "inactive"]] = None
    capabilities: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class Entity(BaseModel):
    """Named entity extracted from text (NER)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^(ent_[a-z0-9_-]+|[0-9A-HJKMNP-TV-Z]{26})$")
    ulid: str = Field(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")
    entity_type: EntityType
    agent_profile: Optional[AgentProfile] = None
    title: str = Field(min_length=1)
    occurrences: int = Field(ge=1)
    mentioned_in: list[str] = Field(default_factory=list)


class Nodes(BaseModel):
    """Graph nodes grouped by type."""

    model_config = ConfigDict(extra="forbid")

    sections: list[Section] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)


# ============================================================================
# Edge
# ============================================================================


class EdgeType(str, Enum):
    """Edge types in the graph."""

    IN_SECTION = "in_section"
    PARENT = "parent"
    NEXT = "next"
    PREV = "prev"
    SIMILAR = "similar"
    MENTIONS = "mentions"
    RELATED = "related"
    AUTHORED_BY = "authored_by"
    DERIVED_FROM = "derived_from"
    INVESTIGATES = "investigates"
    PREDICTED_CONNECTION = "predicted_connection"
    VALIDATED_CONNECTION = "validated_connection"


class Edge(BaseModel):
    """Graph edge connecting two nodes."""

    model_config = ConfigDict(extra="forbid")

    from_id: str
    to_id: str
    type: EdgeType
    weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    overlap_chars: Optional[int] = Field(None, ge=0)


# ============================================================================
# Links
# ============================================================================


class LinkType(str, Enum):
    """Link types from SYNTAX.md."""

    LINK = "link"  # +link:
    IMAGE = "image"  # +image:
    PROJEKT = "projekt"  # +projekt:
    QUELLE = "quelle"  # +quelle:


class Link(BaseModel):
    """Document link (+link:, +image:, +projekt: from SYNTAX.md)."""

    model_config = ConfigDict(extra="forbid")

    type: LinkType
    target_id: str
    source_node: Optional[str] = None
    context: Optional[str] = None
    char_offset: Optional[int] = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_target_id(self) -> "Link":
        """
        Validate target_id based on link type.

        - Internal links (`link`, `image`, `projekt`) must point to a full ULID.
        - External references (`quelle`) accept any non-empty string (URL, DOI, etc.).
        """
        if self.type == LinkType.QUELLE:
            if not self.target_id.strip():
                raise ValueError("target_id must be non-empty for type=quelle")
            return self

        if not re.fullmatch(r"^[0-9A-HJKMNP-TV-Z]{26}$", self.target_id):
            raise ValueError("target_id must be a 26-char ULID for internal link types")
        return self


# ============================================================================
# Processing
# ============================================================================


class ProcessingStep(str, Enum):
    """Pipeline processing steps."""

    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    SUMMARIZATION = "summarization"
    TAXONOMY_MATCHING = "taxonomy_matching"
    LLM_VERIFICATION = "llm_verification"
    NER_EXTRACTION = "ner_extraction"


class ProcessingStepInfo(BaseModel):
    """Information about a processing step."""

    model_config = ConfigDict(extra="allow")

    step: ProcessingStep
    completed: bool
    timestamp: datetime


class Processing(BaseModel):
    """Pipeline processing metadata."""

    steps: list[ProcessingStepInfo] = Field(default_factory=list)


# ============================================================================
# Document
# ============================================================================


class DocType(str, Enum):
    """Document types."""

    NOTE = "note"
    PDF = "pdf"
    INVOICE = "invoice"
    EMAIL = "email"
    IMAGE = "image"
    WEBPAGE = "webpage"
    HYPOTHESIS = "hypothesis"
    INSIGHT = "insight"
    CONVERSATION = "conversation"


class LifecycleStage(str, Enum):
    """Memory stage."""

    VOLATILE = "volatile"
    CRYSTALLIZED = "crystallized"


class ResearchStatus(str, Enum):
    """Status for hypotheses."""

    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class Document(BaseModel):
    """Complete document with metadata, graph structure, links, and processing info."""

    model_config = ConfigDict(extra="forbid")

    # Metadata
    id: str = Field(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")
    slug: str = Field(pattern=r"^[a-z0-9-]{1,60}$")
    path: str
    original_source: Optional[str] = None
    title: str = Field(min_length=1)
    language: str = Field(pattern=r"^[a-z]{2}$")
    doc_type: DocType
    lifecycle_stage: Optional[LifecycleStage] = None
    research_status: Optional[ResearchStatus] = None
    decay_factor: Optional[float] = None
    valid_until: Optional[datetime] = None

    # Hashing & Versioning
    content_hash: str = Field(pattern=r"^sha256:[a-f0-9]{8,64}$")
    file_hash: Optional[str] = Field(None, pattern=r"^sha256:[a-f0-9]{8,64}$")
    source_commit: Optional[str] = Field(None, pattern=r"^[a-f0-9]{7,40}$")
    source_commit_date: Optional[datetime] = None
    source_dirty: bool

    # Timestamps
    created: datetime
    updated: datetime

    # Information Decay
    uses: int = Field(ge=0)
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    decay: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Content
    full_text: str

    # Type-specific metadata (flexible JSON)
    facets: dict[str, Any] = Field(default_factory=dict)

    # Graph Structure
    nodes: Nodes
    edges: list[Edge] = Field(default_factory=list)

    # Links (from SYNTAX.md)
    links: list[Link] = Field(default_factory=list)
    backlinks: list[Link] = Field(default_factory=list)

    # Processing
    processing: Processing

    @field_validator("content_hash", "file_hash")
    @classmethod
    def validate_hash(cls, v: Optional[str]) -> Optional[str]:
        """Validate SHA256 hash format."""
        if v and not v.startswith("sha256:"):
            raise ValueError("Hash must start with 'sha256:'")
        return v

    def get_all_nodes(self) -> list[Section | Chunk | Entity]:
        """Get all nodes as a flat list."""
        return [
            *self.nodes.sections,
            *self.nodes.chunks,
            *self.nodes.entities,
        ]

    def get_node_by_id(self, node_id: str) -> Optional[Section | Chunk | Entity]:
        """Get a node by its ID."""
        for node in self.get_all_nodes():
            if node.id == node_id:
                return node
        return None

    def add_processing_step(
        self, step: ProcessingStep, completed: bool = True, **kwargs: Any
    ) -> None:
        """Add a processing step with metadata."""
        step_info = ProcessingStepInfo(
            step=step,
            completed=completed,
            timestamp=datetime.now(),
            **kwargs,
        )
        self.processing.steps.append(step_info)

    def get_latest_step(self, step: ProcessingStep) -> Optional[ProcessingStepInfo]:
        """Get the most recent info for a processing step."""
        matching = [s for s in self.processing.steps if s.step == step]
        return matching[-1] if matching else None


# ============================================================================
# Taxonomy
# ============================================================================


class TaxonomyCategory(BaseModel):
    """Taxonomy category node for classification."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Category slug (kebab-case)")
    ulid: str = Field(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")
    type: Literal["category"] = "category"
    title: str = Field(min_length=1)
    description: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    importance: Optional[int] = Field(None, ge=1, le=10)
    decay: Optional[int] = Field(None, ge=1, le=10)
    embedding: Optional[list[float]] = None
