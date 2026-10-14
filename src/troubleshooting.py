"""
CircuitSathi Circuit Troubleshooting Engine
Orchestrates guided troubleshooting by fusing deterministic electrical safety checks,
retrieved component datasheet constraints, and evidence-grounded AI diagnosis.
"""

from typing import Any
from pydantic import BaseModel, Field
from src.safety import check_circuit_safety
from src.retrieval import vector_store, format_context_for_prompt
from src.prompts import CIRCUITSATHI_TROUBLESHOOTING_PROMPT
from src.llm import llm_client


class TroubleshootingRequest(BaseModel):
    """Input payload for guided circuit troubleshooting."""
    project_description: str
    wiring_topology: str
    power_supply: str
    supply_voltage_v: float = 5.0
    estimated_current_a: float = 0.5
    components: str
    symptoms: str
    expected_behavior: str
    measurements_taken: str = "None yet"
    has_motors_or_relays: bool = False
    is_battery_powered: bool = False
    battery_type: str = ""
    controller_logic_v: float = 3.3
    peripheral_logic_v: float = 3.3


class TroubleshootingResult(BaseModel):
    """Structured troubleshooting output with deterministic safety checks."""
    safety_warnings: list[dict[str, str]]
    retrieved_citations: list[str]
    retrieved_passages: list[dict[str, Any]]
    analysis_text: str
    disclaimer: str = (
        "CircuitSathi provides advisory engineering diagnostic checks and does not certify circuits as safe. "
        "Always de-energize the circuit before modifying wiring or measuring resistance/continuity."
    )


def conduct_troubleshooting(request: TroubleshootingRequest, stream: bool = False) -> TroubleshootingResult:
    """
    Executes guided troubleshooting:
    1. Deterministic safety analysis
    2. Vector retrieval for components in knowledge base
    3. LLM structured analysis
    """
    # 1. Deterministic safety checks
    safety_warnings = check_circuit_safety(
        supply_voltage=request.supply_voltage_v,
        current_draw_a=request.estimated_current_a,
        has_inductive_load=request.has_motors_or_relays,
        is_battery_powered=request.is_battery_powered,
        battery_type=request.battery_type,
        controller_logic_v=request.controller_logic_v,
        peripheral_logic_v=request.peripheral_logic_v
    )

    # 2. Semantic retrieval on components & symptoms
    query = f"{request.components} {request.symptoms} {request.power_supply}"
    retrieved = vector_store.query(query, top_k=3, score_threshold=0.3)
    citations = [r["citation"] for r in retrieved]
    context_str = format_context_for_prompt(retrieved)

    # 3. Prompt assembly
    prompt = CIRCUITSATHI_TROUBLESHOOTING_PROMPT.format(
        project_description=request.project_description,
        wiring_topology=request.wiring_topology,
        power_supply=request.power_supply,
        components=request.components,
        symptoms=request.symptoms,
        expected_behavior=request.expected_behavior,
        measurements_taken=request.measurements_taken,
        datasheet_context=f"RETRIEVED DATASHEET EVIDENCE:\n{context_str}" if retrieved else "No indexed datasheets matched this configuration."
    )

    # 4. Generate diagnosis
    try:
        response_text = llm_client.generate(prompt=prompt, stream=False)
    except Exception as e:
        response_text = (
            f"Diagnostic analysis could not be completed with the local LLM: {str(e)}\n\n"
            "Review the deterministic safety warnings and verify that Ollama is running."
        )

    return TroubleshootingResult(
        safety_warnings=safety_warnings,
        retrieved_citations=citations,
        retrieved_passages=retrieved,
        analysis_text=response_text
    )
