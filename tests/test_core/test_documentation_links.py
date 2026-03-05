"""Verify all documentation files exist and contain expected section headers."""

import os
import pytest

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs")


# (filename, list of required section headings)
REQUIRED_DOCS = [
    ("API_REFERENCE.md", ["Products", "Recommendations", "Reviews", "Price", "Policy", "Chat", "Health"]),
    ("AGENTS.md", ["BaseAgent", "RecommendationAgent", "ReviewSummarizationAgent", "PriceComparisonAgent", "PolicyAgent", "IntentClassifier", "GeneralResponseAgent", "Orchestrator"]),
    ("TESTING.md", ["Running Tests", "Directory Structure", "Key Testing Patterns"]),
    ("EVALS.md", ["Architecture", "Core Classes", "Test File Index", "How to Run"]),
    ("DEPLOYMENT.md", ["Prerequisites", "Environment Variables", "Docker Compose"]),
    ("DEVELOPER_GUIDE.md", ["Adding a New Agent"]),
    ("DATA_PIPELINE.md", ["CSV Schemas", "Ingestion Pipeline", "FAISS Vector Index"]),
    ("MONITORING.md", ["Health Endpoints", "Metrics System", "Alerting System"]),
    ("TROUBLESHOOTING.md", ["Startup Issues", "Database Issues", "OpenAI"]),
]


@pytest.mark.parametrize("filename,required_headings", REQUIRED_DOCS, ids=[r[0] for r in REQUIRED_DOCS])
def test_doc_exists_and_has_sections(filename, required_headings):
    """Each doc file must exist, be non-empty, and contain required section headings."""
    filepath = os.path.join(DOCS_DIR, filename)
    assert os.path.isfile(filepath), f"Missing documentation file: docs/{filename}"

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert len(content) > 100, f"docs/{filename} is too short ({len(content)} chars)"

    for heading in required_headings:
        assert heading in content, (
            f"docs/{filename} missing expected section containing '{heading}'"
        )
