"""rna_motif_visualizer.pdb_motif_mapper

Convenience wrapper around AtlasMotifLoader for fast, grouped lookups.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .atlas_loader import get_atlas_loader


class PDBMotifMapper:
    def __init__(self, motif_db_path: Optional[str] = None):
        self.loader = get_atlas_loader(motif_db_path)
        self._cache: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    def get_available_motifs(self, pdb_id: str) -> Dict[str, List[Dict[str, Any]]]:
        pdb_id = pdb_id.upper()
        if pdb_id in self._cache:
            return self._cache[pdb_id]

        motifs = self.loader.get_motifs_for_pdb(pdb_id)
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for motif in motifs:
            motif_type = str(motif.get("motif_type", "")).upper()
            grouped.setdefault(motif_type, []).append(motif)

        self._cache[pdb_id] = grouped
        return grouped

    def get_motifs_by_type(self, pdb_id: str, motif_type: str) -> List[Dict[str, Any]]:
        return self.get_available_motifs(pdb_id).get(motif_type.upper(), [])

    def count_motifs(self, pdb_id: str) -> int:
        return sum(len(v) for v in self.get_available_motifs(pdb_id).values())

    def pdb_has_motifs(self, pdb_id: str) -> bool:
        return self.count_motifs(pdb_id) > 0

    def get_summary(self, pdb_id: str) -> str:
        grouped = self.get_available_motifs(pdb_id)
        if not grouped:
            return f"No motifs found in {pdb_id.upper()}"

        lines = [f"Motifs in {pdb_id.upper()}:" ]
        for motif_type in sorted(grouped.keys()):
            lines.append(f"  {motif_type}: {len(grouped[motif_type])} instances")
        return "\n".join(lines)


_mapper_instance: Optional[PDBMotifMapper] = None


def get_pdb_mapper(motif_db_path: Optional[str] = None) -> PDBMotifMapper:
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = PDBMotifMapper(motif_db_path)
    return _mapper_instance
