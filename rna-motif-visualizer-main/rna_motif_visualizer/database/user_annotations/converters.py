"""
User Annotation Converters

Converts external tool formats (FR3D, RNAMotifScan, etc.) to the standard MotifInstance format.

Each converter follows this pattern:
    1. Parse tool-specific format
    2. Extract motif name, residue positions, and metadata
    3. Convert to standard MotifInstance objects
    4. Return dict: {motif_type: [MotifInstance, ...]}
"""

import csv
from typing import Dict, List, Tuple
from pathlib import Path


class MotifInstanceSimple:
    """Lightweight MotifInstance for user annotations (before standardization)."""
    
    def __init__(self, motif_id: str, instance_id: str, residues: List[Tuple], 
                 annotation: str = ""):
        self.motif_id = motif_id
        self.instance_id = instance_id
        self.residues = residues  # List of (nucleotide, residue_number, chain)
        self.annotation = annotation
    
    def to_legacy_format(self) -> List[Dict]:
        """Convert to legacy format for PyMOL selector."""
        result = []
        current_chain = None
        residue_list = []
        
        for nucleotide, res_num, chain in self.residues:
            if chain != current_chain:
                if residue_list:
                    result.append({
                        'nucleotide': None,
                        'residues': residue_list,
                        'chain': current_chain,
                    })
                current_chain = chain
                residue_list = []
            residue_list.append(res_num)
        
        if residue_list:
            result.append({
                'nucleotide': None,
                'residues': residue_list,
                'chain': current_chain,
            })
        
        return result


class FR3DConverter:
    """Convert FR3D output CSV format to standard motif format.
    
    FR3D CSV columns:
    - Motif order: Sequential number
    - Motif type: e.g., 'Hairpin', 'Internal loop', etc.
    - Resolution: Resolution value
    - Positions: Format "PDB_ID|chain|model|start-end"
    - Sequence: RNA sequence
    - cWW: Base pair count
    - Description: Description text
    """
    
    @staticmethod
    def parse_positions(positions_str: str) -> tuple:
        """
        Parse FR3D positions format: can be:
        - Single range: "1S72|1|0|13-530"
        - Multiple ranges: "1S72|1|0|21-26;1S72|1|0|522-517"
        
        Returns: (pdb_id, chain, residue_ranges) 
                 where residue_ranges is list of (start, end) tuples
        """
        # Handle multiple ranges separated by semicolon
        if ';' in positions_str:
            # Multiple ranges - split by semicolon
            parts = positions_str.split(';')
            residue_ranges = []
            pdb_id = None
            chain = None
            
            for part in parts:
                components = part.strip().split('|')
                if len(components) >= 4:
                    if pdb_id is None:
                        pdb_id = components[0]
                        chain = components[1]
                    
                    range_str = components[3]
                    try:
                        start, end = map(int, range_str.split('-'))
                        residue_ranges.append((start, end))
                    except ValueError:
                        continue
            
            if pdb_id and residue_ranges:
                return pdb_id, chain, residue_ranges
            else:
                raise ValueError(f"Could not parse FR3D positions: {positions_str}")
        
        else:
            # Single range
            parts = positions_str.split('|')
            if len(parts) < 4:
                raise ValueError(f"Invalid FR3D positions format: {positions_str}")
            
            pdb_id = parts[0]
            chain = parts[1]
            range_str = parts[3]
            
            try:
                start, end = map(int, range_str.split('-'))
                return pdb_id, chain, [(start, end)]
            except ValueError:
                raise ValueError(f"Could not parse range: {range_str}")
    
    @staticmethod
    def convert_file(csv_path: str) -> Dict[str, List[MotifInstanceSimple]]:
        """
        Convert FR3D CSV file to motif instances.
        
        Args:
            csv_path: Path to FR3D CSV file
            
        Returns:
            Dict mapping motif types to lists of MotifInstanceSimple
        """
        motifs_by_type = {}
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row_idx, row in enumerate(reader, 1):
                    try:
                        motif_type = row.get('Motif type', '').strip().upper()
                        if not motif_type:
                            continue
                        
                        # Normalize motif type name
                        motif_type = motif_type.replace(' ', '_').replace('-', '_')
                        
                        # Parse positions
                        positions_str = row.get('Positions', '')
                        pdb_id, chain, residue_ranges = FR3DConverter.parse_positions(positions_str)
                        
                        # Create residue list from all ranges
                        residues = []
                        for start, end in residue_ranges:
                            # Handle both ascending and descending ranges
                            if start <= end:
                                for res_num in range(start, end + 1):
                                    residues.append(('N', res_num, chain))
                            else:
                                for res_num in range(start, end - 1, -1):
                                    residues.append(('N', res_num, chain))
                        
                        # Create instance
                        instance_id = f"{pdb_id}_{row_idx}"
                        annotation = row.get('Description', '')
                        
                        instance = MotifInstanceSimple(
                            motif_id=motif_type,
                            instance_id=instance_id,
                            residues=residues,
                            annotation=annotation
                        )
                        
                        if motif_type not in motifs_by_type:
                            motifs_by_type[motif_type] = []
                        motifs_by_type[motif_type].append(instance)
                        
                    except Exception as e:
                        # Silently skip malformed rows instead of warning
                        continue
            
            return motifs_by_type
            
        except FileNotFoundError:
            raise FileNotFoundError(f"FR3D CSV file not found: {csv_path}")
        except Exception as e:
            raise Exception(f"Error parsing FR3D CSV file: {e}")


class RNAMotifScanConverter:
    """Convert RNAMotifScan output format to standard motif format.
    
    RNAMotifScan typically produces CSV/TSV with columns like:
    - Motif_Name: e.g., 'HL' (hairpin loop), 'IL' (internal loop)
    - Start: Starting residue position
    - End: Ending residue position
    - Sequence: RNA sequence
    - Chain: Chain ID
    - Score: Match score
    """
    
    @staticmethod
    def convert_file(csv_path: str, pdb_id: str, delimiter: str = ',') -> Dict[str, List[MotifInstanceSimple]]:
        """
        Convert RNAMotifScan output file to motif instances.
        
        Args:
            csv_path: Path to RNAMotifScan output file
            pdb_id: PDB ID (for creating instance IDs)
            delimiter: Field delimiter (',' for CSV, '\t' for TSV)
            
        Returns:
            Dict mapping motif types to lists of MotifInstanceSimple
        """
        motifs_by_type = {}
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                
                for row_idx, row in enumerate(reader, 1):
                    try:
                        # Extract fields (may vary by RNAMotifScan version)
                        motif_type = row.get('Motif_Name') or row.get('Motif') or row.get('Type')
                        if not motif_type:
                            continue
                        
                        motif_type = motif_type.strip().upper()
                        motif_type = motif_type.replace(' ', '_').replace('-', '_')
                        
                        # Get positions
                        start = int(row.get('Start') or row.get('Start_Position') or 0)
                        end = int(row.get('End') or row.get('End_Position') or 0)
                        chain = row.get('Chain', 'A').strip()
                        
                        if start <= 0 or end <= 0 or start > end:
                            print(f"Warning: Invalid range in RNAMotifScan row {row_idx}")
                            continue
                        
                        # Create residue list
                        residues = []
                        for res_num in range(start, end + 1):
                            residues.append(('N', res_num, chain))
                        
                        # Create instance
                        instance_id = f"{pdb_id}_{row_idx}"
                        annotation = row.get('Score', '')
                        
                        instance = MotifInstanceSimple(
                            motif_id=motif_type,
                            instance_id=instance_id,
                            residues=residues,
                            annotation=annotation
                        )
                        
                        if motif_type not in motifs_by_type:
                            motifs_by_type[motif_type] = []
                        motifs_by_type[motif_type].append(instance)
                        
                    except Exception as e:
                        print(f"Warning: Could not parse RNAMotifScan row {row_idx}: {e}")
                        continue
            
            return motifs_by_type
            
        except FileNotFoundError:
            raise FileNotFoundError(f"RNAMotifScan output file not found: {csv_path}")
        except Exception as e:
            raise Exception(f"Error parsing RNAMotifScan output file: {e}")
