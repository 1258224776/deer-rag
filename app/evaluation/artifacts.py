from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class ExperimentArtifactStore:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, payload: dict, name: str | None = None) -> dict[str, str]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        slug = name or "experiment"
        artifact_id = f"{slug}-{timestamp}-{uuid4().hex[:8]}"
        path = self.base_dir / f"{artifact_id}.json"
        artifact_meta = {
            "artifact_id": artifact_id,
            "artifact_path": str(path),
        }
        payload_to_write = dict(payload)
        payload_to_write.update(artifact_meta)
        path.write_text(json.dumps(payload_to_write, ensure_ascii=False, indent=2), encoding="utf-8")
        return artifact_meta

    def list(self) -> list[dict[str, str | int]]:
        items: list[dict[str, str | int]] = []
        for path in sorted(self.base_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            items.append(
                {
                    "artifact_id": path.stem,
                    "artifact_path": str(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        return items

    def get(self, artifact_id: str) -> dict:
        path = self.base_dir / f"{artifact_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Experiment artifact not found: {artifact_id}")
        return json.loads(path.read_text(encoding="utf-8"))
