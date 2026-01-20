"""
RNA Motif Visualizer - BGSU RNA 3D Hub API Provider
Fetches motif data from the BGSU RNA 3D Hub REST API.

API Endpoint: https://rna.bgsu.edu/rna3dhub/loops/download/{PDB_ID}
Returns CSV data with motif loop IDs and residue specifications.

This provider enables visualization of RNA motifs for ANY PDB structure
in the RNA 3D Hub database (~3000+ RNA structures), not just those
bundled locally.

Author: Structural Biology Lab
Version: 2.0.0
"""

from __future__ import annotations

import re
import ssl
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Set

from .base_provider import (
    BaseProvider,
    DatabaseInfo,
    DatabaseSourceType,
    MotifInstance,
    MotifType,
    ResidueSpec,
)


class BGSUAPIProvider(BaseProvider):
    """
    Provider that fetches RNA motif data from BGSU RNA 3D Hub API.
    
    Supports:
    - Hairpin loops (HL)
    - Internal loops (IL)
    - Junction loops (J3, J4, J5, J6, J7, J8)
    
    API Response Format (CSV):
        "HL_4V9F_001","4V9F|1|0|U|55,4V9F|1|0|G|56,..."
        
    Each entry has:
        - Loop ID: {TYPE}_{PDB}_{NUMBER}
        - Residues: PDB|Model|Chain|Nucleotide|ResNum (comma-separated)
    """
    
    # Base URL for the BGSU RNA 3D Hub API
    API_BASE_URL = "https://rna.bgsu.edu/rna3dhub/loops/download"
    
    # Timeout for API requests (seconds)
    REQUEST_TIMEOUT = 30
    
    # Mapping of loop type prefixes to full names
    MOTIF_TYPES = {
        'HL': 'Hairpin Loop',
        'IL': 'Internal Loop',
        'J3': '3-way Junction',
        'J4': '4-way Junction',
        'J5': '5-way Junction',
        'J6': '6-way Junction',
        'J7': '7-way Junction',
        'J8': '8-way Junction',
    }
    
    def __init__(self, cache_manager=None):
        """
        Initialize the BGSU API provider.
        
        Args:
            cache_manager: Optional cache manager for storing API responses
        """
        # Create a fake path for the base class (API doesn't use local files)
        super().__init__("api://bgsu.rna3dhub")
        
        self._info = DatabaseInfo(
            id="bgsu_api",
            name="BGSU RNA 3D Hub (Online)",
            version="API",
            description="Live data from BGSU RNA 3D Hub - supports ~3000+ RNA structures",
            source_type=DatabaseSourceType.API,
        )
        self.cache_manager = cache_manager
        self._available_motif_types = list(self.MOTIF_TYPES.keys())
        self._fetched_pdbs: Set[str] = set()  # Track which PDBs we've successfully fetched
        self._motif_cache: Dict[str, Dict[str, List[MotifInstance]]] = {}  # pdb_id -> motifs
    
    @property
    def info(self) -> DatabaseInfo:
        """Get database metadata."""
        return self._info
    
    def initialize(self) -> bool:
        """Initialize the provider (always succeeds for API provider)."""
        self._initialized = True
        return True
    
    def get_available_motif_types(self) -> List[str]:
        """Get list of motif types supported by BGSU RNA 3D Hub."""
        return self._available_motif_types
    
    def get_available_pdb_ids(self) -> List[str]:
        """
        Get list of PDB IDs that have been successfully fetched.
        
        Note: This only returns PDBs we've already fetched. The actual
        BGSU database has ~3000+ structures, but we don't enumerate them.
        """
        return list(self._fetched_pdbs)
    
    def get_motif_type(self, motif_type_id: str) -> Optional[MotifType]:
        """
        Get information about a motif type.
        
        Args:
            motif_type_id: Motif type ID (e.g., 'HL', 'IL')
            
        Returns:
            MotifType object or None
        """
        if motif_type_id not in self.MOTIF_TYPES:
            return None
        
        return MotifType(
            type_id=motif_type_id,
            name=self.MOTIF_TYPES[motif_type_id],
            description=f"{self.MOTIF_TYPES[motif_type_id]} from RNA 3D Motif Atlas",
        )
    
    def get_motifs_for_pdb(self, pdb_id: str) -> Dict[str, List[MotifInstance]]:
        """
        Fetch motifs for a PDB structure from BGSU API.
        
        Args:
            pdb_id: PDB structure ID
            
        Returns:
            Dict mapping motif type IDs to lists of MotifInstances
        """
        pdb_id = pdb_id.strip().upper()
        
        # Check internal cache first
        if pdb_id in self._motif_cache:
            return self._motif_cache[pdb_id]
        
        # Check file cache if available
        if self.cache_manager:
            cached = self.cache_manager.get_cached_motifs(pdb_id, "bgsu_api")
            if cached is not None:
                self._fetched_pdbs.add(pdb_id)
                self._motif_cache[pdb_id] = cached
                return cached
        
        # Fetch from API
        try:
            csv_data = self._fetch_from_api(pdb_id)
            if csv_data is None:
                return {}
            
            # Parse CSV data into motif instances
            motifs = self._parse_csv_response(csv_data, pdb_id)
            
            # Cache the results
            if self.cache_manager and motifs:
                self.cache_manager.cache_motifs(pdb_id, "bgsu_api", motifs)
            
            if motifs:
                self._fetched_pdbs.add(pdb_id)
                self._motif_cache[pdb_id] = motifs
            
            return motifs
            
        except Exception as e:
            print(f"Error fetching motifs for {pdb_id} from BGSU API: {e}")
            return {}
    
    def _fetch_from_api(self, pdb_id: str) -> Optional[str]:
        """
        Fetch raw CSV data from BGSU API.
        
        Args:
            pdb_id: PDB ID to fetch
            
        Returns:
            Raw CSV string or None if failed
        """
        url = f"{self.API_BASE_URL}/{pdb_id}"
        
        try:
            # Create request with proper headers
            request = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'RNA-Motif-Visualizer/2.0',
                    'Accept': 'text/csv, text/plain, */*',
                }
            )
            
            # Create SSL context that doesn't verify certificates
            # This handles macOS certificate issues
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(request, timeout=self.REQUEST_TIMEOUT, context=ssl_context) as response:
                if response.status == 200:
                    return response.read().decode('utf-8')
                else:
                    print(f"BGSU API returned status {response.status} for {pdb_id}")
                    return None
                    
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # PDB not found in RNA 3D Hub - this is normal for non-RNA structures
                print(f"PDB {pdb_id} not found in RNA 3D Hub database")
            else:
                print(f"HTTP error fetching {pdb_id}: {e.code} {e.reason}")
            return None
            
        except urllib.error.URLError as e:
            print(f"Network error fetching {pdb_id}: {e.reason}")
            return None
            
        except Exception as e:
            print(f"Error fetching {pdb_id} from BGSU API: {e}")
            return None
    
    def _parse_csv_response(self, csv_data: str, pdb_id: str) -> Dict[str, List[MotifInstance]]:
        """
        Parse BGSU CSV response into MotifInstance objects.
        
        CSV Format:
            "HL_4V9F_001","4V9F|1|0|U|55,4V9F|1|0|G|56,..."
            
        Args:
            csv_data: Raw CSV string from API
            pdb_id: PDB ID for validation
            
        Returns:
            Dict mapping motif type IDs to lists of MotifInstances
        """
        result: Dict[str, List[MotifInstance]] = {}
        
        # Pattern to match CSV entries: "LOOP_ID","RESIDUES"
        # Handle various whitespace and newline formats
        pattern = r'"([^"]+)","([^"]+)"'
        
        for match in re.finditer(pattern, csv_data):
            loop_id = match.group(1).strip()
            residue_specs = match.group(2).strip()
            
            # Parse loop ID to get motif type
            # Format: {TYPE}_{PDB}_{NUMBER} e.g., HL_4V9F_001
            parts = loop_id.split('_')
            if len(parts) < 2:
                continue
            
            motif_type = parts[0]  # HL, IL, J3, etc.
            
            # Skip unknown motif types
            if motif_type not in self.MOTIF_TYPES:
                continue
            
            # Parse residues
            residues = self._parse_residue_specs(residue_specs)
            if not residues:
                continue
            
            # Create MotifInstance
            instance = MotifInstance(
                instance_id=loop_id,
                motif_id=motif_type,
                pdb_id=pdb_id,
                residues=residues,
                annotation=self.MOTIF_TYPES.get(motif_type, ''),
                metadata={'source': 'bgsu_api', 'loop_id': loop_id}
            )
            
            # Add to results
            if motif_type not in result:
                result[motif_type] = []
            result[motif_type].append(instance)
        
        return result
    
    def _parse_residue_specs(self, specs_str: str) -> List[ResidueSpec]:
        """
        Parse comma-separated residue specifications.
        
        Format: PDB|Model|Chain|Nucleotide|ResNum
        Example: 4V9F|1|0|U|55,4V9F|1|0|G|56
        
        Args:
            specs_str: Comma-separated residue specifications
            
        Returns:
            List of ResidueSpec objects
        """
        residues = []
        
        for spec in specs_str.split(','):
            spec = spec.strip()
            if not spec:
                continue
            
            parts = spec.split('|')
            if len(parts) < 5:
                continue
            
            try:
                # PDB|Model|Chain|Nucleotide|ResNum
                model = int(parts[1]) if parts[1].isdigit() else 1
                chain = parts[2]
                nucleotide = parts[3]
                res_num = int(parts[4])
                
                residues.append(ResidueSpec(
                    chain=chain,
                    residue_number=res_num,
                    nucleotide=nucleotide,
                    model=model,
                ))
            except (ValueError, IndexError):
                continue
        
        return residues
    
    def has_pdb(self, pdb_id: str) -> bool:
        """
        Check if a PDB has motif data in BGSU.
        
        This actually fetches data to check, but results are cached.
        
        Args:
            pdb_id: PDB ID to check
            
        Returns:
            True if PDB has motif data
        """
        motifs = self.get_motifs_for_pdb(pdb_id)
        return len(motifs) > 0
    
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
        pdb_id = pdb_id.upper()
        
        # Check cache first
        if pdb_id in self._motif_cache:
            motifs = self._motif_cache[pdb_id]
        else:
            motifs = self.get_motifs_for_pdb(pdb_id)
            self._motif_cache[pdb_id] = motifs
        
        # Find the specific instance
        if motif_type not in motifs:
            return []
        
        for instance in motifs[motif_type]:
            if instance.instance_id == instance_id:
                return instance.residues
        
        return []
    
    def get_motif_instances_for_pdb(self, pdb_id: str, motif_type_id: str) -> List[MotifInstance]:
        """
        Get all instances of a specific motif type in a PDB.
        
        Args:
            pdb_id: PDB ID
            motif_type_id: Motif type (e.g., 'HL', 'IL')
            
        Returns:
            List of MotifInstance objects
        """
        all_motifs = self.get_motifs_for_pdb(pdb_id)
        return all_motifs.get(motif_type_id, [])
