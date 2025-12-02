import argparse
import json
from pathlib import Path
from typing import List

import yaml

from agents.correlation_agent import CorrelationAgent
from agents.intel_agent import IntelAgent
from agents.onchain_agent import OnchainAgent
from agents.report_agent import ReportAgent
from tools.firecrawl_tools import IntelCrawler
from tools.solana_tools import RPCConfig, SolanaRPCClient


def load_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def run_pipeline(config: dict, addresses: List[str]) -> str:
    rpc_config = RPCConfig(endpoint=config["rpc_endpoint"], commitment=config.get("commitment", "confirmed"))
    rpc_client = SolanaRPCClient(rpc_config)
    intel_agent = IntelAgent(IntelCrawler())
    onchain_agent = OnchainAgent(rpc_client)
    correlation_agent = CorrelationAgent(similarity_threshold=config.get("similarity_threshold", 0.55))

    if not addresses:
        findings = intel_agent.run(config.get("intel_sources", []))
        aggregated = intel_agent.consolidate(findings)
        addresses = aggregated["addresses"]

    onchain_findings = onchain_agent.collect_transfers(addresses)
    onchain_summary = onchain_agent.summarize(onchain_findings)

    correlation = correlation_agent.correlate(
        balances=list(onchain_summary["balances"].values()),
        flags=onchain_summary["flags"],
        transfers=onchain_summary["transfers"],
    )

    report = ReportAgent.build(
        balances=onchain_summary["balances"],
        flags=correlation.flags,
        clusters=correlation.clusters,
        transfers=onchain_summary["transfers"],
    )
    return ReportAgent.to_text(report)


def main() -> None:
    parser = argparse.ArgumentParser(description="Solana forensic pipeline")
    parser.add_argument("--config", type=Path, default=Path("crew_config/crew.yaml"))
    parser.add_argument("--addresses", nargs="*", help="Seed addresses for collection")
    parser.add_argument("--output", type=Path, default=None, help="Optional path to write report")
    args = parser.parse_args()

    config = load_config(args.config)
    report_text = run_pipeline(config, addresses=args.addresses or [])

    if args.output:
        args.output.write_text(report_text, encoding="utf-8")
    else:
        print(report_text)


if __name__ == "__main__":
    main()
