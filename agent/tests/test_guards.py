"""DroneCAD — tests des garde-fous de la boucle agentique (Phase 3).

EN: pure unit tests — no MCP server, no ROS. A FakeClient stands in for real MCP servers.
FR : tests unitaires purs — aucun serveur MCP, aucun ROS. Un FakeClient remplace les serveurs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_loop import (  # noqa: E402
    AgentLoop,
    IterationLimitReached,
    PhaseGuard,
    ToolCall,
    ToolNotAllowed,
    sha256_digest,
)
from mcp_stdio import MCPTimeout  # noqa: E402

ALLOWLIST = {
    "design": {"freecad": ["create_document", "export_step"]},
    "simulate": {"ros2": ["publish_cmd_vel"]},
}


class FakeClient:
    """Client MCP simulé / simulated MCP client."""

    def __init__(self, failing: tuple[str, ...] = (), timing_out: tuple[str, ...] = ()) -> None:
        self.failing = failing
        self.timing_out = timing_out
        self.calls: list[tuple[str, dict]] = []

    def call_tool(self, name: str, arguments: dict, timeout_s: float = 30.0) -> dict:
        self.calls.append((name, arguments))
        if name in self.timing_out:
            raise MCPTimeout(f"faux délai dépassé / simulated timeout for {name}")
        if name in self.failing:
            raise RuntimeError(f"échec simulé / simulated failure for {name}")
        return {"content": [{"type": "text", "text": f"ok:{name}"}]}

    def list_tools(self, timeout_s: float = 20.0) -> list[dict]:
        return [{"name": "fake_tool"}]


@pytest.fixture()
def loop(tmp_path: Path) -> AgentLoop:
    guard = PhaseGuard(ALLOWLIST)
    return AgentLoop(
        clients={"freecad": FakeClient(), "ros2": FakeClient()},
        guard=guard,
        journal_path=tmp_path / "journal.jsonl",
        max_iterations=3,
        call_timeout_s=5.0,
    )


def _journal_entries(loop: AgentLoop) -> list[dict]:
    return [json.loads(line) for line in loop.journal_path.read_text(encoding="utf-8").splitlines()]


def test_allowlist_blocks_and_journals(loop: AgentLoop) -> None:
    with pytest.raises(ToolNotAllowed):
        loop.submit("design", ToolCall("freecad", "rm_minus_rf", {}), "corr-1", 1)
    entries = _journal_entries(loop)
    assert len(entries) == 1
    assert entries[0]["ok"] is False
    assert entries[0]["error"].startswith("allowlist:")
    # EN: the forbidden tool was never sent to the client / FR : jamais envoyé au client
    assert loop.clients["freecad"].calls == []  # type: ignore[attr-defined]


def test_unknown_phase_is_blocked(loop: AgentLoop) -> None:
    with pytest.raises(ToolNotAllowed):
        loop.submit("sabotage", ToolCall("freecad", "create_document", {}), "corr-1", 1)


def test_allowed_call_succeeds_and_journals_digests(loop: AgentLoop) -> None:
    args = {"name": "bracket", "height": 42}
    outcome = loop.submit("design", ToolCall("freecad", "create_document", args), "corr-2", 1)
    assert outcome.ok is True
    assert outcome.result_digest
    entries = _journal_entries(loop)
    entry = entries[-1]
    assert entry["args_digest"] == sha256_digest(args)
    assert len(entry["args_preview"]) <= 200
    assert entry["correlation_id"] == "corr-2"
    assert entry["iteration"] == 1


def test_timeout_is_journaled_not_fatal(tmp_path: Path) -> None:
    guard = PhaseGuard(ALLOWLIST)
    client = FakeClient(timing_out=("create_document",))
    loop = AgentLoop(
        clients={"freecad": client},
        guard=guard,
        journal_path=tmp_path / "journal.jsonl",
    )
    outcome = loop.submit("design", ToolCall("freecad", "create_document", {}), "corr-3", 1)
    assert outcome.ok is False
    assert "MCPTimeout" in (outcome.error or "")
    entries = _journal_entries(loop)
    assert entries[-1]["ok"] is False


def test_failure_is_journaled(tmp_path: Path) -> None:
    guard = PhaseGuard(ALLOWLIST)
    loop = AgentLoop(
        clients={"freecad": FakeClient(failing=("export_step",))},
        guard=guard,
        journal_path=tmp_path / "journal.jsonl",
    )
    outcome = loop.submit("design", ToolCall("freecad", "export_step", {}), "corr-4", 1)
    assert outcome.ok is False
    assert "RuntimeError" in (outcome.error or "")


def test_criterion_stops_early(loop: AgentLoop) -> None:
    steps = [("design", ToolCall("freecad", "create_document", {}))]
    history = loop.run(steps, criterion=lambda outcomes: all(o.ok for o in outcomes))
    assert len(history) == 1


def test_iteration_limit_is_enforced(loop: AgentLoop) -> None:
    steps = [("design", ToolCall("freecad", "create_document", {}))]
    with pytest.raises(IterationLimitReached):
        loop.run(steps, criterion=lambda outcomes: False)
    entries = _journal_entries(loop)
    assert len(entries) == 3  # 3 itérations max, une entrée par appel / one entry per call
    correlation_ids = {e["correlation_id"] for e in entries}
    assert len(correlation_ids) == 3  # corrélation par itération / per-iteration correlation
    assert {e["iteration"] for e in entries} == {1, 2, 3}
