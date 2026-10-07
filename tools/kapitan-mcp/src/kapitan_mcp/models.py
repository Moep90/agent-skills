"""Pydantic response models.

Every tool returns one of these, serialized to JSON, never raw CLI text. Every response
carries ``schema_version`` so clients can detect contract changes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

SCHEMA_VERSION = 1


class Response(BaseModel):
    """Base for all tool responses."""

    schema_version: int = SCHEMA_VERSION


class ProjectInfo(Response):
    root: str
    kapitan_version: str | None
    backend: str
    wrapper_detected: bool
    targets_count: int
    warnings: list[str] = []


class Target(BaseModel):
    name: str
    path: str
    labels: dict[str, Any] = {}


class TargetList(Response):
    targets: list[Target]


class ClassEntry(BaseModel):
    dotted_name: str
    path: str


class ClassList(Response):
    classes: list[ClassEntry]


class InventoryTarget(Response):
    target: str
    backend: str
    parameters: dict[str, Any] | None = None
    subtree: Any | None = None
    truncated: bool = False
    hint: str | None = None


class ClassNode(BaseModel):
    dotted_name: str
    path: str
    depth: int


class ClassHierarchy(Response):
    target: str
    includes: list[ClassNode]


class SearchMatch(BaseModel):
    path: str
    line: int
    snippet: str
    dotted_key: str | None = None


class SearchResult(Response):
    matches: list[SearchMatch]


class RefEntry(BaseModel):
    token: str
    backend: str
    path: str
    exists: bool
    # Deliberately no value field. This tool reports metadata only.


class RefsList(Response):
    refs: list[RefEntry]


class CompileTargetResult(BaseModel):
    target: str
    ok: bool
    duration_s: float | None = None
    error: str | None = None


class CompileResult(Response):
    results: list[CompileTargetResult]


class ChangedFile(BaseModel):
    path: str
    diff: str


class CompileDiff(Response):
    changed_files: list[ChangedFile]
    unchanged_count: int
    truncated: bool = False


class LintResult(Response):
    ok: bool
    output: str


class GeneratorBlock(BaseModel):
    path: str  # e.g. "components.web" or "generators.multus"
    kind: str  # "component" | "generator"
    wired: bool
    matched_input_path: str | None = None
    hint: str | None = None


class TargetTrace(BaseModel):
    target: str
    backend: str
    blocks: list[GeneratorBlock]


class GeneratorTrace(Response):
    targets: list[TargetTrace]
    orphans: list[str] = []  # "<target>: <block path>" for every unwired block


class SchemaKey(BaseModel):
    key: str
    count: int  # distinct blocks that use this key
    examples: list[str] = []  # block names using it (capped)


class GeneratorSchema(Response):
    key: str  # inspected top-level block, e.g. "components"
    blocks_examined: int
    keys: list[SchemaKey]
    rare_keys: list[str] = []  # used by exactly one block: likely typo or new
