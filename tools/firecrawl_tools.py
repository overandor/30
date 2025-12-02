import re
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


class IntelCrawler:
    """Fetches and normalizes open-source intelligence sources."""

    def __init__(self, user_agent: str = "solana-forensic-system/1.0"):
        self.headers = {"User-Agent": user_agent}

    def fetch_page(self, url: str) -> str:
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.text

    def extract_indicators(self, html: str) -> Dict[str, List[str]]:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        addresses = self._extract_solana_addresses(text)
        urls = [a.get("href") for a in soup.find_all("a") if a.get("href")]
        return {"addresses": addresses, "links": urls}

    @staticmethod
    def _extract_solana_addresses(text: str) -> List[str]:
        base58_charset = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        pattern = rf"[{base58_charset}]{{32,44}}"
        return re.findall(pattern, text)
