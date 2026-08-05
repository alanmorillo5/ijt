import yaml
from pathlib import Path
from typing import Any

class Config:
    def __init__(self, data: dict[str, Any]):
        self.data = data

    @property
    def search(self) -> dict[str, Any]:
        return self.data.get("search", {})

    @property
    def scraper(self) -> dict[str, Any]:
        return self.data.get("sources", {})
        
    @property
    def llm(self) -> dict[str, Any]:
        return self.data.get("llm", {})

    @property
    def output(self) -> dict[str, Any]:
        return self.data.get("output", {})

def load_config(path: Path) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(data)
