"""End-to-end tests at the MCP protocol level.

Launch the real server over stdio and drive it with the official MCP client SDK against the
examples/demo-project, exercising the full path an editor would use.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

pytestmark = pytest.mark.e2e

DEMO = Path(__file__).parents[4] / "examples" / "demo-project"


@pytest.fixture(autouse=True)
def _require_kapitan() -> None:
    if shutil.which("kapitan") is None:
        pytest.skip("kapitan CLI not installed")


async def _call(tool: str, args: dict) -> dict:
    params = StdioServerParameters(
        command="kapitan-mcp-server",
        args=["--project-root", str(DEMO.resolve())],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
            return {"content": result.content, "is_error": result.isError}


@pytest.mark.anyio
async def test_e2e__inventory_target__returns_resolved_value() -> None:
    out = await _call("kapitan_inventory_target", {"target": "dev", "parameter_path": "namespace"})

    assert out["is_error"] is False
    assert "dev" in out["content"][0].text


@pytest.mark.anyio
async def test_e2e__compile_diff__clean_demo_has_no_changes() -> None:
    out = await _call("kapitan_compile_diff", {"targets": ["dev", "prod"]})

    assert out["is_error"] is False
    assert '"changed_files": []' in out["content"][0].text


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
