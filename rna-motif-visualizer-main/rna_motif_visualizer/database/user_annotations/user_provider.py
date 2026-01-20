"""
User Annotation Provider

Loads motif data from user-uploaded annotation files (FR3D, RNAMotifScan, etc.).
Uses converters to transform external formats to standard MotifInstance format.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from ..base_provider import BaseProvider, MotifInstance, DatabaseInfo, DatabaseSourceType, ResidueSpec
from .converters import FR3DConverter, RNAMotifScanConverter, MotifInstanceSimple


class UserAnnotationProvider(BaseProvider):
    """
    Provides motifs from user-uploaded annotation files.
    
    Supports:
    - FR3D output CSV files
    - RNAMotifScan output files
    """
    
    def __init__(self, user_annotations_dir: str):
        """
        Initialize user annotation provider.
        
        Args:
            user_annotations_dir: Path to directory containing user annotation subdirectories
                                 (fr3d/, rnamotifscan/, etc.)
        """
        self.user_annotations_dir = Path(user_annotations_dir)
        self.user_annotations_dir.mkdir(parents=True, exist_ok=True)
        
        self._info = DatabaseInfo(
            id='user_annotations',
            name='User Annotations',
            description='User-uploaded motif annotation files from external tools',
            version='1.0.0',
            source_type=DatabaseSourceType.LOCAL_DIRECTORY,
        )
        
        # Supported tool formats
        self.supported_tools = ['fr3d', 'rnamotifscan']
        
        # Track loaded data
        self._loaded_motifs_cache: Dict[str, Dict] = {}
        self._available_pdbs: List[str] = []
        self._motif_types: Dict[str, List[MotifInstance]] = {}
        self._initialized = False
    
    @property
    def info(self) -> DatabaseInfo:
        """Get database metadata."""
        return self._info
    
    def initialize(self) -> bool:
        """
        Initialize the provider by scanning for annotation files.
        
        Returns:
            True if initialization successful
        """
        try:
            # Scan for available PDB files
            pdbs = set()
            for tool_name in self.supported_tools:
                tool_dir = self.user_annotations_dir / tool_name
                if tool_dir.exists():
                    for file_path in tool_dir.glob('*'):
                        if file_path.is_file() and file_path.suffix in ['.csv', '.tsv', '.txt']:
                            # Extract PDB ID from filename
                            filename = file_path.stem.lower()
                            # Try to extract PDB ID (usually first 4 chars)
                            pdb_id = filename.split('_')[0]
                            if len(pdb_id) >= 4:
                                pdbs.add(pdb_id.upper())
            
            self._available_pdbs = sorted(list(pdbs))
            self._initialized = True
            return True
        except Exception as e:
            print(f"Warning: Could not initialize UserAnnotationProvider: {e}")
            return False
    
    def get_available_motif_types(self) -> List[str]:
        """Get all available motif types across all loaded files."""
        all_types = set()
        for motif_list in self._motif_types.values():
            for instance in motif_list:
                all_types.add(instance.motif_id)
        return sorted(list(all_types))
    
    def get_motif_type(self, type_id: str) -> Optional[Dict]:
        """Get all instances of a specific motif type."""
        all_instances = []
        for instances in self._motif_types.values():
            for inst in instances:
                if inst.motif_id == type_id:
                    all_instances.append(inst)
        
        if all_instances:
            return {
                'type_id': type_id,
                'instances': all_instances,
                'count': len(all_instances)
            }
        return None
    
    def get_motifs_for_pdb(self, pdb_id: str) -> Dict[str, List[MotifInstance]]:
        """
        Get motifs for a PDB ID from user annotation files.
        
        Searches for files matching PDB_ID pattern in tool subdirectories.
        
        Args:
            pdb_id: PDB ID to search for
            
        Returns:
            Dict mapping motif types to lists of MotifInstance objects
        """
        pdb_id_lower = pdb_id.lower()
        all_motifs = {}
        
        # Search each tool subdirectory
        for tool_name in self.supported_tools:
            tool_dir = self.user_annotations_dir / tool_name
            if not tool_dir.exists():
                continue
            
            # Look for matching files (e.g., 1s72_motifs.csv, 1s72.csv)
            for file_path in tool_dir.glob(f"{pdb_id_lower}*"):
                if file_path.is_file() and file_path.suffix in ['.csv', '.tsv', '.txt']:
                    try:
                        motifs = self._load_file(file_path, tool_name, pdb_id)
                        all_motifs.update(motifs)
                    except Exception as e:
                        print(f"Warning: Could not load {file_path}: {e}")
                        continue
        
        # Convert MotifInstanceSimple to standard MotifInstance
        result = {}
        for motif_type, instances in all_motifs.items():
            result[motif_type] = [self._convert_instance(inst, pdb_id) for inst in instances]
        
        # Cache for later reference
        self._motif_types[pdb_id] = sum(result.values(), [])
        
        return result
    
    def get_available_pdb_ids(self) -> List[str]:
        """Get list of all PDB IDs with annotation files."""
        if not self._available_pdbs:
            self.initialize()
        return self._available_pdbs
    
    def get_motif_residues(self, pdb_id: str, motif_type: str, 
                          instance_id: str) -> List[ResidueSpec]:
        """
        Get residues for a specific motif instance.
        
        Args:
            pdb_id: PDB structure identifier
            motif_type: Motif type identifier
            instance_id: Instance identifier
            
        Returns:
            List of ResidueSpec objects
        """
        motifs = self.get_motifs_for_pdb(pdb_id)
        
        if motif_type not in motifs:
            return []
        
        for instance in motifs[motif_type]:
            if instance.instance_id == instance_id:
                return instance.residues
        
        return []
    
    def _load_file(self, file_path: Path, tool_name: str, pdb_id: str) -> Dict[str, List[MotifInstanceSimple]]:
        """
        Load motifs from a specific file using appropriate converter.
        
        Args:
            file_path: Path to annotation file
            tool_name: Tool name ('fr3d', 'rnamotifscan')
            pdb_id: PDB ID
            
        Returns:
            Dict of motifs keyed by type
        """
        if tool_name.lower() == 'fr3d':
            return FR3DConverter.convert_file(str(file_path))
        elif tool_name.lower() == 'rnamotifscan':
            delimiter = '\t' if file_path.suffix == '.tsv' else ','
            return RNAMotifScanConverter.convert_file(str(file_path), pdb_id, delimiter=delimiter)
        else:
            raise ValueError(f"Unknown tool format: {tool_name}")
    
    def _convert_instance(self, simple_instance: MotifInstanceSimple, pdb_id: str) -> MotifInstance:
        """
        Convert MotifInstanceSimple to standard MotifInstance format.
        
        Args:
            simple_instance: Simple instance from converter
            pdb_id: PDB ID
            
        Returns:
            Standard MotifInstance object
        """
        # Convert residue tuples to ResidueSpec objects
        residues = []
        for nucleotide, res_num, chain in simple_instance.residues:
            residue = ResidueSpec(
                nucleotide=nucleotide or 'N',
                residue_number=res_num,
                chain=chain
            )
            residues.append(residue)
        
        # Create MotifInstance
        instance = MotifInstance(
            motif_id=simple_instance.motif_id,
            instance_id=simple_instance.instance_id,
            residues=residues,
            pdb_id=pdb_id,
            annotation=simple_instance.annotation
        )
        
        return instance
    
    def is_available(self) -> bool:
        """Check if any user annotation files exist."""
        if not self.user_annotations_dir.exists():
            return False
        
        for tool_name in self.supported_tools:
            tool_dir = self.user_annotations_dir / tool_name
            if tool_dir.exists() and any(tool_dir.glob('*.csv')) or \
               any(tool_dir.glob('*.tsv')) or \
               any(tool_dir.glob('*.txt')):
                return True
        
        return False

