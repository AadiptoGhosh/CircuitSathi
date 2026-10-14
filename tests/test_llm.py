"""
Tests for Ollama LLM wrapper and prompt integration.
"""

from unittest.mock import patch, MagicMock
import pytest
from src.llm import OllamaClient
from src.prompts import CIRCUITSATHI_SYSTEM_PROMPT, CIRCUITSATHI_RAG_PROMPT


def test_ollama_client_check_status_offline():
    """Verify clean status dictionary when Ollama server is unreachable."""
    client = OllamaClient(base_url="http://localhost:99999")
    status = client.check_status()
    assert status["online"] is False
    assert "not running" in status["message"].lower() or "failed" in status["message"].lower()


def test_ollama_client_download_command():
    """Verify download command string."""
    client = OllamaClient()
    cmd = client.get_download_command("gemma3:4b")
    assert cmd == "ollama pull gemma3:4b"


def test_ollama_generate_mock():
    """Verify generate behavior using mocked HTTP response."""
    client = OllamaClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "A MOSFET is a voltage-controlled device."}

    with patch("httpx.Client.post", return_value=mock_resp):
        ans = client.generate(prompt="What is a MOSFET?", system_prompt=CIRCUITSATHI_SYSTEM_PROMPT)
        assert "MOSFET" in ans
        assert "voltage-controlled" in ans


def test_rag_prompt_formatting():
    """Verify RAG prompt formats retrieved context without errors."""
    prompt = CIRCUITSATHI_RAG_PROMPT.format(
        retrieved_context="TB6612FNG VM range is 4.5V to 15V [Doc: TB.pdf, Page: 1]",
        query="What is VM?"
    )
    assert "TB6612FNG VM range" in prompt
    assert "What is VM?" in prompt
    assert "INSTRUCTIONS:" in prompt
