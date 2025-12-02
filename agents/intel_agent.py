from dataclasses import dataclass
from typing import Dict, List

from tools.firecrawl_tools import IntelCrawler


@dataclass
class IntelFinding:
    source_url: str
    addresses: List[str]
    links: List[str]


class IntelAgent:
    def __init__(self, crawler: IntelCrawler):
        self.crawler = crawler

    def run(self, sources: List[str]) -> List[IntelFinding]:
        findings: List[IntelFinding] = []
        for url in sources:
            html = self.crawler.fetch_page(url)
            indicators = self.crawler.extract_indicators(html)
            findings.append(
                IntelFinding(
                    source_url=url,
                    addresses=indicators.get("addresses", []),
                    links=indicators.get("links", []),
                )
            )
        return findings

    @staticmethod
    def consolidate(findings: List[IntelFinding]) -> Dict[str, List[str]]:
        aggregated: Dict[str, List[str]] = {"addresses": [], "links": []}
        for finding in findings:
            aggregated["addresses"].extend(finding.addresses)
            aggregated["links"].extend(finding.links)
        aggregated["addresses"] = sorted(set(aggregated["addresses"]))
        aggregated["links"] = sorted(set(aggregated["links"]))
        return aggregated
