"""rna_motif_visualizer.atlas_loader

Loads RNA 3D Motif Atlas JSON files (and indexes by PDB ID) for scalable lookup.

Atlas JSON structure (simplified):
- List[dict] of motifs
- Each motif has an "alignment" dict
- alignment maps instance_id -> { position_index: "PDB|Model|Chain|Nuc|ResNum", ... }

This module builds an in-memory index:
  PDB_ID -> List[{motif_type, motif_id, instance_id, ...}]
"""

from __future__ import annotations

import os
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ResidueSpec = Tuple[str, int, str]  # (nucleotide, residue_number, chain)


class AtlasMotifLoader:
    """Loader + indexer for RNA 3D Motif Atlas JSON files."""

    def __init__(self, motif_db_path: str):
        self.db_path = Path(motif_db_path)
        self.registry_file = self.db_path / "motif_registry.json"
        self.registry: Dict[str, Any] = self._load_registry()

        self.pdb_index: Dict[str, List[Dict[str, Any]]] = {}

        # Selected motif files per type, resolved at index-build time.
        # This enables drop-in Atlas upgrades: add new *_{version}.json files and the loader picks the newest.
        self._resolved_motif_files: Dict[str, Path] = {}

    def _load_registry(self) -> Dict[str, Any]:
        try:
            with open(self.registry_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def build_pdb_index(self) -> None:
        """Scan all registry files and build PDB->motifs index."""
        self.pdb_index.clear()

        # Resolve motif type -> file path. Supports:
        # - Explicit registry entries (motif_files[TYPE].file)
        # - Auto-discovery of latest versioned files (e.g., hl_4.5.json, hl_4.6.json)
        # Optional override: set env var RNA_MOTIF_ATLAS_VERSION=4.6
        self._resolved_motif_files = self._resolve_motif_files()

        for motif_type, file_path in self._resolved_motif_files.items():
            if not file_path.exists():
                continue

            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
            except Exception:
                continue

            self._index_motif_file_data(data, motif_type)

    def _resolve_motif_files(self) -> Dict[str, Path]:
        """Resolve motif_type -> JSON file path.

        Order of preference per motif type:
        1) If registry explicitly specifies a file and it exists, use it.
        2) Otherwise, auto-discover the latest versioned file matching `<prefix>_<version>.json`.

        Version override:
          Set `RNA_MOTIF_ATLAS_VERSION` (e.g., "4.6") to pick that version when available.
        """
        motif_types = list((self.registry.get("motif_files", {}) or {}).keys())
        if not motif_types:
            motif_types = ["HL", "IL", "J3", "J4", "J5", "J6", "J7"]

        override_version = (os.environ.get("RNA_MOTIF_ATLAS_VERSION") or "").strip() or None

        resolved: Dict[str, Path] = {}
        registry_files = self.registry.get("motif_files", {}) or {}

        for motif_type in motif_types:
            cfg = registry_files.get(motif_type, {}) if isinstance(registry_files, dict) else {}
            explicit_name = cfg.get("file") if isinstance(cfg, dict) else None
            if explicit_name:
                explicit_path = (self.db_path / str(explicit_name)).resolve()
                if explicit_path.exists():
                    resolved[motif_type] = explicit_path
                    continue

            discovered = self._discover_latest_versioned_file(motif_type, override_version)
            if discovered is not None:
                resolved[motif_type] = discovered

        return resolved

    def _discover_latest_versioned_file(self, motif_type: str, override_version: Optional[str]) -> Optional[Path]:
        """Find the best motif JSON file for a motif type by filename.

        Expected pattern: `<prefix>_<version>.json`, where prefix is lowercased motif type.
        Examples: hl_4.5.json, j3_4.6.json
        """
        prefix = motif_type.lower()
        candidates = list(self.db_path.glob(f"{prefix}_*.json"))
        if not candidates:
            return None

        versioned: List[Tuple[Tuple[int, ...], Path]] = []
        override_match: Optional[Path] = None

        for path in candidates:
            stem = path.stem  # e.g. hl_4.5
            m = re.match(rf"^{re.escape(prefix)}_(.+)$", stem)
            if not m:
                continue
            version_str = m.group(1)

            if override_version is not None and version_str == override_version:
                override_match = path

            parsed = self._parse_version_tuple(version_str)
            if parsed is None:
                continue
            versioned.append((parsed, path))

        if override_match is not None:
            return override_match.resolve()

        if not versioned:
            # Fall back to newest by filename (lexicographic) if versions are not parseable.
            return sorted(candidates, key=lambda p: p.name)[-1].resolve()

        versioned.sort(key=lambda vp: vp[0])
        return versioned[-1][1].resolve()

    @staticmethod
    def _parse_version_tuple(version: str) -> Optional[Tuple[int, ...]]:
        """Parse a dotted version string into a tuple of ints.

        Returns None if version contains no digits.
        Examples: "4.5" -> (4, 5); "4.5.1" -> (4, 5, 1)
        """
        parts = [p for p in str(version).split(".") if p != ""]
        if not parts:
            return None
        parsed: List[int] = []
        for part in parts:
            if not part.isdigit():
                return None
            parsed.append(int(part))
        return tuple(parsed)

    def _index_motif_file_data(self, data: Any, motif_type: str) -> None:
        """Index one Atlas motif JSON file."""
        if not isinstance(data, list):
            return

        motifs: Iterable[Any] = data

        for motif_entry in motifs:
            if not isinstance(motif_entry, dict):
                continue

            alignment = motif_entry.get("alignment")
            if not isinstance(alignment, dict):
                # Not an Atlas motif entry; skip.
                continue

            for instance_id in alignment.keys():
                pdb_id = self._extract_pdb_id(str(instance_id))
                if not pdb_id:
                    continue

                self.pdb_index.setdefault(pdb_id, []).append(
                    {
                        "motif_id": motif_entry.get("motif_id", "unknown"),
                        "motif_type": motif_type,
                        "instance_id": instance_id,
                        "num_instances": motif_entry.get("num_instances"),
                        "num_nucleotides": motif_entry.get("num_nucleotides"),
                    }
                )

    @staticmethod
    def _extract_pdb_id(instance_id: str) -> Optional[str]:
        # Case 1: residue spec style in key (rare)
        if "|" in instance_id:
            head = instance_id.split("|", 1)[0]
            return head.upper() if len(head) == 4 else None

        # Case 2: typical Atlas instance_id like HL_6SVS_002 (PDB IDs are 4-char and can start with a digit)
        parts = instance_id.split("_")
        for part in parts:
            if len(part) == 4 and part.isalnum():
                return part.upper()
        return None

    def get_available_pdb_structures(self) -> List[str]:
        return sorted(self.pdb_index.keys())

    def get_motifs_for_pdb(self, pdb_id: str) -> List[Dict[str, Any]]:
        return self.pdb_index.get(pdb_id.upper(), [])

    def load_motif_residues(self, pdb_id: str, motif_type: str, instance_id: str) -> List[ResidueSpec]:
        """Load residue specs for a single motif instance."""
        pdb_id = pdb_id.upper()

        # Ensure we have resolved motif files even if caller didn't explicitly build the index.
        if not self._resolved_motif_files:
            self._resolved_motif_files = self._resolve_motif_files()

        file_path = self._resolved_motif_files.get(motif_type)
        if file_path is None or not file_path.exists():
            return []

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except Exception:
            return []

        if not isinstance(data, list):
            return []

        for motif_entry in data:
            if not isinstance(motif_entry, dict):
                continue

            alignment = motif_entry.get("alignment")
            if not isinstance(alignment, dict):
                continue

            residues = alignment.get(instance_id)
            if isinstance(residues, dict):
                parsed = self._parse_alignment_residues(residues)
                # Note: residue specs in Atlas entries are already for this instance_id.
                return parsed

        return []

    @staticmethod
    def _parse_alignment_residues(residues: Dict[str, str]) -> List[ResidueSpec]:
        result: List[ResidueSpec] = []
        # Sort by numeric position when possible
        for _, spec in sorted(residues.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 10**9):
            parts = str(spec).split("|")
            if len(parts) < 5:
                continue
            chain = parts[2]
            nuc = parts[3]
            try:
                res_num = int(parts[4])
            except ValueError:
                continue
            result.append((nuc, res_num, chain))
        return result


_loader_instance: Optional[AtlasMotifLoader] = None


def get_atlas_loader(motif_db_path: Optional[str] = None) -> AtlasMotifLoader:
    global _loader_instance
    if _loader_instance is None:
        if motif_db_path is None:
            motif_db_path = str(Path(__file__).parent / "motif_database")
        _loader_instance = AtlasMotifLoader(motif_db_path)
        _loader_instance.build_pdb_index()
    return _loader_instance
