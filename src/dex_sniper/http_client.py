from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter, Retry


class HttpClient:
    def __init__(self, timeout: float, max_retries: int, user_agent: str) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        retry_policy = Retry(
            total=max_retries,
            backoff_factor=0.2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "POST"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_policy, pool_connections=4, pool_maxsize=16)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({"User-Agent": user_agent})

    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = self.session.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
