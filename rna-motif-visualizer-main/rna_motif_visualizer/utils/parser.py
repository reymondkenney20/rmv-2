"""
RNA Motif Visualizer - Parser Module
Handles parsing of PDB/mmCIF filenames (PDB ID extraction) and selection formatting.
"""

import os


class PDBParser:
    """Simple parser for PDB metadata (minimal - mostly handled by PyMOL)."""
    
    @staticmethod
    def extract_pdb_id(filepath_or_id):
        """
        Extract PDB ID from file path or return if already a PDB ID.
        
        Args:
            filepath_or_id (str): Either a PDB ID or file path
        
        Returns:
            str: PDB ID (4 characters) or None if invalid
        """
        # Check if it's already a PDB ID (4 characters, alphanumeric)
        if len(filepath_or_id) == 4 and filepath_or_id.isalnum():
            return filepath_or_id.upper()
        
        # Try to extract from filename
        filename = os.path.basename(filepath_or_id)
        # PDB files often named like "1s72.pdb" or "1S72.cif"
        if filename:
            name_without_ext = os.path.splitext(filename)[0]
            if len(name_without_ext) >= 4:
                potential_id = name_without_ext[:4]
                if potential_id.isalnum():
                    return potential_id.upper()
        
        return None
    
    @staticmethod
    def is_valid_pdb_id(pdb_id):
        """
        Check if a string is a valid PDB ID.
        
        Args:
            pdb_id (str): Potential PDB ID
        
        Returns:
            bool: True if valid format
        """
        if not isinstance(pdb_id, str):
            return False
        return len(pdb_id) == 4 and pdb_id.isalnum()


class SelectionParser:
    """Parser for creating PyMOL selection strings from residue data."""
    
    @staticmethod
    def create_selection_string(chain, residues):
        """
        Create a PyMOL selection string from chain and residue numbers.
        
        Args:
            chain (str): Chain identifier
            residues (list): List of residue numbers
        
        Returns:
            str: PyMOL selection string (e.g., "chain A and resi 77-82")
        """
        if not residues:
            return None
        
        residues = sorted(residues)
        selection = f"chain {chain} and resi {residues[0]}-{residues[-1]}"
        return selection
    
    @staticmethod
    def create_detailed_selection(chain, residues):
        """
        Create a detailed PyMOL selection string listing all residues.
        
        Args:
            chain (str): Chain identifier
            residues (list): List of residue numbers
        
        Returns:
            str: Detailed PyMOL selection string
        """
        if not residues:
            return None
        
        residue_list = "+".join([f"resi {r}" for r in sorted(residues)])
        selection = f"chain {chain} and ({residue_list})"
        return selection


def validate_motif_data(motif_entry):
    """
    Validate a motif entry has required fields.
    
    Args:
        motif_entry (dict): Motif dictionary to validate
    
    Returns:
        bool: True if valid
    """
    required_fields = ['chain', 'residues', 'motif_id']
    return all(field in motif_entry for field in required_fields) and \
           isinstance(motif_entry.get('residues'), list) and \
           len(motif_entry.get('residues', [])) > 0
