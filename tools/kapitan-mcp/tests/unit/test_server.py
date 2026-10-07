"""Unit tests for the MCP server assembly."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from kapitan_mcp.errors import PathOutsideProjectError
from kapitan_mcp.models import TargetList
from kapitan_mcp.server import _guard, create_server


def test_create_server__registers_all_m1_tools(mini_inventory: Path) -> None:
    server = create_server(mini_inventory)

    names = {t.name for t in asyncio.run(server.list_tools())}
    assert {
        "kapitan_project_info",
        "kapitan_list_targets",
        "kapitan_list_classes",
        "kapitan_inventory_target",
        "kapitan_class_hierarchy",
        "kapitan_search_inventory",
        "kapitan_refs_list",
        "kapitan_compile",
        "kapitan_compile_diff",
        "kapitan_generator_trace",
        "kapitan_generator_schema",
        "kapitan_lint",
    } <= names


def test_create_server__tools_have_descriptions(mini_inventory: Path) -> None:
    server = create_server(mini_inventory)

    for tool in asyncio.run(server.list_tools()):
        assert tool.description, f"{tool.name} has no description for the agent"


def test_create_server__read_only_tools_annotated_read_only(mini_inventory: Path) -> None:
    server = create_server(mini_inventory)
    tools = {t.name: t for t in asyncio.run(server.list_tools())}

    read_only = {
        "kapitan_project_info",
        "kapitan_list_targets",
        "kapitan_list_classes",
        "kapitan_inventory_target",
        "kapitan_class_hierarchy",
        "kapitan_search_inventory",
        "kapitan_refs_list",
        "kapitan_compile_diff",
        "kapitan_generator_trace",
        "kapitan_generator_schema",
        "kapitan_lint",
    }
    for name in read_only:
        ann = tools[name].annotations
        assert ann is not None, f"{name} has no annotations"
        assert ann.readOnlyHint is True, f"{name} not marked read-only"


def test_create_server__compile_annotated_destructive(mini_inventory: Path) -> None:
    server = create_server(mini_inventory)
    tools = {t.name: t for t in asyncio.run(server.list_tools())}

    ann = tools["kapitan_compile"].annotations
    assert ann is not None
    assert ann.readOnlyHint is False
    assert ann.destructiveHint is True


def test_guard__success__returns_model_dump() -> None:
    def ok() -> TargetList:
        return TargetList(targets=[])

    result = _guard(ok)()

    assert result == {"schema_version": 1, "targets": []}


def test_guard__typed_error__returns_structured_error_contract() -> None:
    def boom() -> TargetList:
        raise PathOutsideProjectError("nope")

    result = _guard(boom)()

    assert result["error"]["code"] == "PATH_OUTSIDE_PROJECT"


def test_create_server__no_project__still_registers_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    server = create_server(None)

    names = {t.name for t in asyncio.run(server.list_tools())}
    assert "kapitan_project_info" in names


def test_create_server__no_project__tool_returns_project_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    server = create_server(None)

    result = asyncio.run(server.call_tool("kapitan_list_targets", {}))

    structured = result[1] if isinstance(result, tuple) else result
    assert "PROJECT_NOT_FOUND" in str(structured)


def test_create_server__no_project__discovers_root_lazily_per_call(
    mini_inventory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(mini_inventory)
    server = create_server(None)

    result = asyncio.run(server.call_tool("kapitan_list_targets", {}))

    structured = result[1] if isinstance(result, tuple) else result
    assert "PROJECT_NOT_FOUND" not in str(structured)
    assert "targets" in str(structured)


def test_main__no_project__serves_instead_of_crashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys as _sys

    from kapitan_mcp import server as server_module

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(_sys, "argv", ["kapitan-mcp-server"])
    captured: dict[str, object] = {}

    class FakeServer:
        def run(self, transport: str) -> None:
            captured["transport"] = transport

    def fake_create_server(root: Path | None) -> FakeServer:
        captured["root"] = root
        return FakeServer()

    monkeypatch.setattr(server_module, "create_server", fake_create_server)

    server_module.main()

    assert captured["root"] is None
    assert captured["transport"] == "stdio"


def test_search_tool_end_to_end__returns_matches_dict(mini_inventory: Path) -> None:
    server = create_server(mini_inventory)

    result = asyncio.run(
        server.call_tool(
            "kapitan_search_inventory", {"query": "image", "kind": "key", "scope": "classes"}
        )
    )
    # FastMCP returns (content, structured); the structured payload is our dict.
    structured = result[1] if isinstance(result, tuple) else result
    assert "matches" in str(structured)
