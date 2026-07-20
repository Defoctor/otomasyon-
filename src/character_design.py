import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "name",
    "age",
    "gender",
    "species",
    "height",
    "hair",
    "eyes",
    "clothes",
    "colors",
    "accessories",
    "personality",
    "speaking_style",
    "prompt",
    "negative_prompt",
}


class CharacterDesignStore:
    def __init__(self, directory: Path):
        self.directory = directory

    def load_all(self) -> dict[str, dict[str, Any]]:
        designs = {}
        for path in sorted(self.directory.glob("*.json")):
            try:
                design = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Geçersiz karakter tasarım dosyası: {path}") from exc
            missing = REQUIRED_FIELDS.difference(design)
            if missing:
                raise RuntimeError(
                    f"{path} dosyasında eksik alanlar: {', '.join(sorted(missing))}"
                )
            designs[path.stem] = design
        return designs

    def build_scene_prompt(self, scene_prompt: str, narration: str) -> str:
        text = f"{scene_prompt}\n{narration}".casefold()
        matched = [
            design
            for design in self.load_all().values()
            if any(
                name.casefold() in text
                for name in [str(design["name"])]
                + [str(alias) for alias in design.get("aliases", [])]
            )
        ]
        if not matched:
            return scene_prompt

        positive = " ".join(str(design["prompt"]) for design in matched)
        negatives = list(
            dict.fromkeys(str(design["negative_prompt"]) for design in matched)
        )
        return (
            f"{scene_prompt}\n\nCharacter design references: {positive}\n"
            f"Negative prompt: {', '.join(negatives)}"
        )

    def sync_from_memory(self, memory: dict[str, Any]) -> None:
        characters = memory.get("characters", {}).get("characters", [])
        by_id = {
            str(character.get("id")): character
            for character in characters
            if character.get("id")
        }
        for path in sorted(self.directory.glob("*.json")):
            design = json.loads(path.read_text(encoding="utf-8"))
            character = by_id.get(str(design.get("memory_character_id")))
            if character is None:
                continue

            appearance = character.get("appearance", {})
            updates = {
                "name": character.get("name"),
                "age": character.get("age"),
                "species": character.get("species"),
                "hair": appearance.get("hair"),
                "eyes": appearance.get("eyes"),
                "clothes": appearance.get("signature_clothing"),
                "personality": character.get("personality"),
            }
            snapshot = design.setdefault("memory_snapshot", {})
            changed = False
            for key, value in updates.items():
                if (
                    value is not None
                    and key in snapshot
                    and snapshot[key] != value
                ):
                    design[key] = value
                    snapshot[key] = value
                    changed = True
            if changed:
                design["prompt"] = self._build_prompt(design)
                self._write(path, design)

    @staticmethod
    def _write(path: Path, design: dict[str, Any]) -> None:
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(design, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _build_prompt(design: dict[str, Any]) -> str:
        colors = ", ".join(str(value) for value in design["colors"])
        accessories = ", ".join(str(value) for value in design["accessories"])
        personality = ", ".join(str(value) for value in design["personality"])
        return (
            f"{design['name']}, consistent character design: age {design['age']}, "
            f"{design['gender']} {design['species']}, {design['height']}, "
            f"{design['hair']}, {design['eyes']}, wearing {design['clothes']}; "
            f"color palette: {colors}; accessories: {accessories or 'none'}; "
            f"personality: {personality}; polished 3D animated family-film style, "
            "expressive, child-friendly proportions, cinematic lighting"
        )
