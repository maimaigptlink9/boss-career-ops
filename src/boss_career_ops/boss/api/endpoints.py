from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from boss_career_ops.config.singleton import SingletonMeta


YAML_PATH = Path(__file__).parent / "boss.yaml"


@dataclass
class Endpoint:
    name: str
    path: str
    method: str
    description: str


class Endpoints(metaclass=SingletonMeta):
    def __init__(self):
        self._endpoints: dict[str, Endpoint] = {}
        self._base_url = ""
        self._api_base = ""
        self._load()

    def _load(self):
        with open(YAML_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self._base_url = data.get("base_url", "")
        self._api_base = data.get("api_base", "")
        for name, ep_data in data.get("endpoints", {}).items():
            self._endpoints[name] = Endpoint(
                name=name,
                path=ep_data["path"],
                method=ep_data.get("method", "GET"),
                description=ep_data.get("description", ""),
            )

    def get(self, name: str) -> Endpoint | None:
        return self._endpoints.get(name)

    def url(self, name: str) -> str:
        ep = self.get(name)
        if ep is None:
            raise ValueError(f"未知端点: {name}")
        return f"{self._base_url}{ep.path}"

