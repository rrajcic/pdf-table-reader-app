import json
import uuid
from datetime import datetime
from pathlib import Path


class SessionManager:
    def __init__(self):
        self.session_id: str = str(uuid.uuid4())[:8]
        self.created: str = datetime.now().isoformat()
        self.extractions: list[dict] = []
        self._save_path: Path | None = None

    def add_extraction(
        self,
        pdf_path: str,
        page_number: int,
        table_name: str,
        notes: str,
        csv_path: str,
        bbox: tuple[int, int, int, int] | None = None,
    ) -> None:
        self.extractions.append(
            {
                "id": str(uuid.uuid4())[:8],
                "pdf_path": str(pdf_path),
                "page_number": page_number,
                "table_name": table_name,
                "notes": notes,
                "csv_path": str(csv_path),
                "bbox": list(bbox) if bbox else None,
                "saved_at": datetime.now().isoformat(),
            }
        )
        # Auto-save after every addition
        if self._save_path:
            self._write(self._save_path)

    def save(self, sessions_dir: Path) -> Path:
        sessions_dir.mkdir(exist_ok=True)
        if self._save_path is None:
            filename = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self._save_path = sessions_dir / filename
        self._write(self._save_path)
        return self._save_path

    def _write(self, path: Path) -> None:
        data = {
            "session_id": self.session_id,
            "created": self.created,
            "extractions": self.extractions,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "SessionManager":
        with open(path) as f:
            data = json.load(f)
        sm = cls()
        sm.session_id = data.get("session_id", sm.session_id)
        sm.created = data.get("created", sm.created)
        sm.extractions = data.get("extractions", [])
        sm._save_path = path
        return sm
