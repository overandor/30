"""Entry point for offline Solana forensic triage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from agents.correlation_agent import CorrelationAgent
from agents.intel_agent import IntelAgent
from agents.onchain_agent import OnChainAgent
from agents.report_agent import ReportAgent

CONFIG_PATH = Path("crew_config/tasks.yaml")


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def run() -> Dict[str, Any]:
    cfg = load_config()

    intel_agent = IntelAgent()
    for entry in cfg.get("intel_sources", []):
        intel_agent.ingest(source=entry["source"], payload=entry["payload"])
    merged_intel = intel_agent.consolidate()

    onchain_agent = OnChainAgent()
    onchain_agent.ingest(cfg.get("onchain_records", []))
    account_scores = onchain_agent.score_accounts()
    clusters = onchain_agent.clusters

    correlation_agent = CorrelationAgent()
    correlations = correlation_agent.correlate(merged_intel, onchain_agent.transactions)
    threshold = int(cfg.get("report", {}).get("lamport_threshold", 1_000_000_000))
    high_value = correlation_agent.high_value_hits(threshold)

    report_agent = ReportAgent()
    report = report_agent.build(
        intel=merged_intel,
        correlations=correlations,
        account_scores=account_scores,
        clusters=clusters,
    )
    report["high_value_hits"] = high_value
    return report


def main() -> None:
    report = run()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
