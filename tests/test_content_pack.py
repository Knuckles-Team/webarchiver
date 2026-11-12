"""The served content pack: ontology roll-up, tool-use and access contracts,
operator and role prompts, and skills (CONN-WEBARCHIVER-WEB-SOURCE-R003)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp import Client
from scion_sdk.turtle_reader import RDF_TYPE, parse_graph
from scion_sdk.access_contract import parse_access_contracts

from webarchiver.mcp_server import get_mcp_instance

ONTOLOGY = Path(__file__).resolve().parents[1] / "webarchiver" / "ontology"
KG = "https://knuckles-team.github.io/ontology/core#"
CONNECTOR_NS = "https://knuckles-team.github.io/ontology/connector/web-archive#"
CP = "https://knuckles-team.github.io/ontology/connector-pack#"
OWL = "http://www.w3.org/2002/07/owl#"
SUBCLASS = "http://www.w3.org/2000/01/rdf-schema#subClassOf"

#: The medulla core classes this pack rolls up to.
CORE = {KG + name for name in ("WebResource", "WebCapture", "Dataset", "Observation")}
TOOLS = {
    "web_fetch",
    "web_extract",
    "web_render",
    "web_screenshot",
    "web_links",
    "web_crawl",
}
SKILLS = {"webarchiver-web-capture", "webarchiver-market-research-capture"}
PROMPTS = {"webarchiver_operator", "webarchiver_market_researcher"}


def _graph(name: str) -> dict:
    return parse_graph((ONTOLOGY / f"{name}.ttl").read_text(encoding="utf-8"))


def _typed(graph: dict, cls: str) -> dict:
    return {s: p for s, p in graph.items() if cls in p.get(RDF_TYPE, [])}


async def _served() -> tuple[set[str], set[str], set[str], dict]:
    server, _args, _mw = get_mcp_instance(command_args=[])
    async with Client(server) as client:
        tools = {t.name for t in await client.list_tools()}
        resources = {str(r.uri) for r in await client.list_resources()}
        prompts = {p.name: p for p in await client.list_prompts()}
        rendered = {
            name: await client.get_prompt(name) for name in prompts if name in PROMPTS
        }
    return tools, resources, set(prompts), rendered


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R003.1")
def test_every_class_rolls_up_to_medulla_core() -> None:
    domain = _graph("webarchiver")
    classes = _typed(domain, OWL + "Class")
    assert classes, "the domain ontology declares no class"
    for subject, props in classes.items():
        parents = set(props.get(SUBCLASS, []))
        assert parents, f"{subject} has no rdfs:subClassOf"
        # Each class reaches a core class directly or through a pack class.
        seen, frontier = set(), parents
        while frontier and not frontier & CORE:
            seen |= frontier
            frontier = {
                p for f in frontier for p in classes.get(f, {}).get(SUBCLASS, [])
            } - seen
        assert frontier & CORE, f"{subject} does not roll up to a core class"
    for name in ("webarchiver", "pack", "access_contracts"):
        text = (ONTOLOGY / f"{name}.ttl").read_text(encoding="utf-8")
        assert "owl:imports" not in text and "_:" not in text and "STUB" not in text


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R003.1")
async def test_tool_use_contracts_cover_the_served_tools() -> None:
    tools, _resources, _prompts, _rendered = await _served()
    pack = _graph("pack")
    declared = {
        props[CP + "componentId"][0]: props
        for props in _typed(pack, CP + "Tool").values()
    }
    assert set(declared) == TOOLS == tools & TOOLS
    domain_classes = set(_typed(_graph("webarchiver"), OWL + "Class")) | CORE
    for name, props in declared.items():
        assert props.get(CP + "operatesOn"), name
        assert set(props.get(CP + "produces", [])) <= domain_classes, name
    skills = {p[CP + "componentId"][0] for p in _typed(pack, CP + "Skill").values()}
    prompts = {p[CP + "componentId"][0] for p in _typed(pack, CP + "Prompt").values()}
    assert (skills, prompts) == (SKILLS, PROMPTS)
    for feature, props in _typed(pack, CP + "Feature").items():
        members = set(props.get(CP + "realizedBy", []))
        assert members and members <= set(pack), feature


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R003.2")
def test_access_contracts_route_every_class_to_a_served_tool() -> None:
    contracts = parse_access_contracts(
        (ONTOLOGY / "access_contracts.ttl").read_text(encoding="utf-8")
    )
    classes = set(_typed(_graph("webarchiver"), OWL + "Class"))
    assert {c.class_iri for c in contracts} == classes - {CONNECTOR_NS + "WebFetchRefusal"}
    assert {c.operation for c in contracts} == TOOLS
    assert {c.source_id for c in contracts} == {"webarchiver-mcp"}
    assert all(c.access_kind == "mcp_tool" and c.auth_ref is None for c in contracts)


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R003.3")
async def test_prompts_and_skills_are_served_as_agent_definitions() -> None:
    _tools, resources, prompts, rendered = await _served()
    assert PROMPTS <= prompts and "webarchiver_specialist" not in prompts
    for name in SKILLS:
        assert f"skill://{name}/SKILL.md" in resources
    assert "skill://webarchiver-starter/SKILL.md" not in resources
    for name in ("webarchiver.ttl", "pack.ttl", "access_contracts.ttl"):
        assert f"ontology://webarchiver-mcp/{name}" in resources
    for name, prompt in rendered.items():
        text = prompt.messages[0].content.text
        # An agent definition names its role, tools, skills, data and guardrails.
        for needle in ("Goal:", "Tools", "Skills:", "Data:", "Guardrails:", "Output:"):
            assert needle in text, (name, needle)
    research = rendered["webarchiver_market_researcher"].messages[0].content.text
    assert "archivebox_cli_add" in research and "web_extract" in research
