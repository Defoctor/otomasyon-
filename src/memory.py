import json
from copy import deepcopy
from pathlib import Path
from typing import Any


MEMORY_DEFAULTS = {
    "characters": {"characters": []},
    "world": {"rules": [], "facts": []},
    "timeline": {"events": []},
    "locations": {"locations": []},
    "inventory": {"items": []},
    "relationships": {"relationships": []},
}


class MemoryStore:
    def __init__(self, directory: Path):
        self.directory = directory

    def ensure_exists(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        for name, default in MEMORY_DEFAULTS.items():
            path = self.directory / f"{name}.json"
            if not path.exists():
                self._write(path, default)

    def load_all(self) -> dict[str, Any]:
        self.ensure_exists()
        memory = {}
        for name, default in MEMORY_DEFAULTS.items():
            path = self.directory / f"{name}.json"
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Geçersiz hafıza dosyası: {path}") from exc
            if not isinstance(value, dict):
                raise RuntimeError(f"Hafıza dosyası JSON nesnesi olmalıdır: {path}")
            memory[name] = self._merge(default, value)
        return memory

    def update(self, changes: dict[str, Any]) -> dict[str, Any]:
        current = self.load_all()
        for name in MEMORY_DEFAULTS:
            change = changes.get(name)
            if change is not None:
                if not isinstance(change, dict):
                    raise RuntimeError(f"{name} hafıza güncellemesi nesne olmalıdır.")
                current[name] = self._merge(current[name], change)
        for name, value in current.items():
            self._write(self.directory / f"{name}.json", value)
        return current

    def record_story(self, title: str, topic: str) -> None:
        self.update(
            {
                "timeline": {
                    "events": [
                        {"type": "story_completed", "title": title, "topic": topic}
                    ]
                }
            }
        )

    def _write(self, path: Path, value: dict[str, Any]) -> None:
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    @classmethod
    def _merge(cls, old: Any, new: Any) -> Any:
        if isinstance(old, dict) and isinstance(new, dict):
            merged = deepcopy(old)
            for key, value in new.items():
                merged[key] = (
                    cls._merge(merged[key], value)
                    if key in merged
                    else deepcopy(value)
                )
            return merged
        if isinstance(old, list) and isinstance(new, list):
            merged = deepcopy(old)
            for item in new:
                identity = cls._identity(item)
                match = next(
                    (
                        index
                        for index, existing in enumerate(merged)
                        if identity is not None and cls._identity(existing) == identity
                    ),
                    None,
                )
                if match is not None:
                    merged[match] = cls._merge(merged[match], item)
                elif item not in merged:
                    merged.append(deepcopy(item))
            return merged
        return deepcopy(new)

    @staticmethod
    def _identity(value: Any) -> tuple[str, str] | None:
        if not isinstance(value, dict):
            return None
        for key in ("id", "name", "title"):
            if value.get(key):
                return key, str(value[key]).casefold()
        return None
