"""
RNA Motif Visualizer - Updated Loader Module
Handles loading structures and motif annotations using scalable database providers.

This module provides:
- StructureLoader: Loads PDB structures into PyMOL
- UnifiedMotifLoader: Loads motifs from any registered database provider
- VisualizationManager: Coordinates the complete visualization workflow

The loader now uses the database registry to support multiple databases
(RNA 3D Atlas, Rfam, etc.) with a unified interface.

Author: CBB Lab by Dr.Zhong
Version: 2.0.0
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from .utils import (
    PDBParser,
    MotifSelector,
    get_logger,
)
from . import colors
from .database import (
    get_registry,
    MotifInstance,
)


class StructureLoader:
    """Handles loading RNA structures into PyMOL."""
    
    def __init__(self, cmd):
        """
        Initialize loader.
        
        Args:
            cmd: PyMOL cmd module
        """
        self.cmd = cmd
        self.logger = get_logger()
        self.current_structure = None
        self.current_pdb_id = None
    
    def load_structure(self, pdb_id_or_path):
        """
        Load an RNA structure into PyMOL.
        
        Args:
            pdb_id_or_path (str): Either a PDB ID or local file path
        
        Returns:
            str: Name of loaded structure in PyMOL, or None if failed
        """
        try:
            # Determine if it's a PDB ID or file path
            if os.path.isfile(pdb_id_or_path):
                # Local file
                self.logger.info(f"Loading structure from file: {pdb_id_or_path}")
                structure_name = Path(pdb_id_or_path).stem
                self.cmd.load(pdb_id_or_path, structure_name)
                pdb_id = PDBParser.extract_pdb_id(pdb_id_or_path)
            else:
                # Assume PDB ID
                pdb_id = pdb_id_or_path.strip().upper()
                if not PDBParser.is_valid_pdb_id(pdb_id):
                    self.logger.error(f"Invalid PDB ID format: {pdb_id}")
                    return None
                
                self.logger.info(f"Downloading structure from RCSB: {pdb_id}")
                structure_name = pdb_id
                # Delete any existing object with the same name to avoid "loading mmCIF into existing object" error
                try:
                    self.cmd.delete(structure_name)
                except:
                    pass  # Object doesn't exist, that's fine
                self.cmd.fetch(pdb_id, structure_name)
            
            self.current_structure = structure_name
            self.current_pdb_id = pdb_id
            
            self.logger.success(f"Loaded structure: {structure_name} (PDB: {pdb_id})")
            return structure_name
            
        except Exception as e:
            self.logger.error(f"Failed to load structure: {e}")
            return None
    
    def get_current_structure(self):
        """Get name of currently loaded structure."""
        return self.current_structure
    
    def get_current_pdb_id(self):
        """Get PDB ID of currently loaded structure."""
        return self.current_pdb_id


class UnifiedMotifLoader:
    """
    Unified motif loader that works with any database provider.
    
    Uses the source selector to automatically find the best data source:
    1. Local bundled databases (fast, offline)
    2. BGSU RNA 3D Hub API (comprehensive, ~3000+ PDBs)
    3. Rfam API (named motifs)
    """
    
    def __init__(self, cmd, database_dir: str):
        """
        Initialize motif loader.
        
        Args:
            cmd: PyMOL cmd module
            database_dir (str): Path to motif database directory
        """
        self.cmd = cmd
        self.database_dir = database_dir
        self.logger = get_logger()
        self.selector = MotifSelector(cmd)
        self.loaded_motifs: Dict[str, Dict] = {}  # Track loaded motif objects
        self._last_source_used: Optional[str] = None
        
        # Get registry
        self._registry = get_registry()
    
    def load_motifs(self, structure_name: str, pdb_id: str,
                   provider_id: Optional[str] = None,
                   force_refresh: bool = False) -> Dict:
        """
        Load all available motifs for a structure.
        
        Uses smart source selection: tries local first, then APIs if needed.
        
        Args:
            structure_name (str): Name of structure in PyMOL
            pdb_id (str): PDB ID to look up motifs for
            provider_id (str): Optional specific provider to use (auto-select if None)
            force_refresh (bool): Force re-fetch from API (ignore cache)
        
        Returns:
            dict: Dictionary of loaded motifs: {motif_type: {details}}
        """
        try:
            self.loaded_motifs = {}
            pdb_id = pdb_id.upper()
            
            # Try to use source selector for smart source selection
            from .database import get_source_selector
            source_selector = get_source_selector()
            
            if source_selector and not provider_id:
                # Use smart source selection
                available_motifs, source_used = source_selector.get_motifs_for_pdb(
                    pdb_id, 
                    source_override=provider_id,
                    force_refresh=force_refresh
                )
                self._last_source_used = source_used
                source_name = source_used or "unknown"
            else:
                # Fall back to registry-based provider selection
                if provider_id:
                    provider = self._registry.get_provider(provider_id)
                else:
                    provider = self._registry.get_active_provider()
                
                if not provider:
                    self.logger.error("No database provider available")
                    return {}
                
                available_motifs = provider.get_motifs_for_pdb(pdb_id)
                source_name = provider.info.name if hasattr(provider, 'info') else provider_id
                self._last_source_used = provider_id
            
            if not available_motifs:
                self.logger.warning(f"No motifs found for PDB {pdb_id}")
                self.logger.info("Tip: This PDB may not have RNA motif annotations in any database")
                return {}
            
            total_count = sum(len(instances) for instances in available_motifs.values())
            self.logger.info(f"Found {total_count} motifs in {pdb_id} (source: {source_name})")
            
            # Process each motif type
            for motif_type, instances in available_motifs.items():
                try:
                    # Handle prefixed motif types from combined sources (e.g., "bgsu_api:HL")
                    display_type = motif_type.split(':')[-1] if ':' in motif_type else motif_type
                    self._load_motif_type(structure_name, pdb_id, display_type, instances)
                except Exception as e:
                    self.logger.error(f"Error loading {motif_type} motifs: {e}")
                    continue
            
            return self.loaded_motifs
            
        except Exception as e:
            self.logger.error(f"Failed to load motifs: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def get_last_source_used(self) -> Optional[str]:
        """Get the data source used for the last load operation."""
        return self._last_source_used
    
    def _load_motif_type(self, structure_name: str, pdb_id: str,
                        motif_type: str, instances: List,
                        use_direct_coloring: bool = True) -> None:
        """
        Load a specific motif type and visualize in PyMOL.
        
        Creates PyMOL objects (visible in right panel) AND colors residues
        directly on the structure (to avoid z-fighting stripes).
        
        Args:
            structure_name: PyMOL structure name
            pdb_id: PDB ID
            motif_type: Type of motif (HL, IL, GNRA, etc.)
            instances: List of MotifInstance objects
            use_direct_coloring: If True, also color residues directly on structure
        """
        if not instances:
            return
        
        # Build motif_list in format MotifSelector expects
        motif_list: List[Dict] = []
        motif_details = []
        
        for instance in instances:
            if not instance.residues:
                continue
            
            # Convert to legacy format for selector
            legacy_entries = instance.to_legacy_format()
            motif_list.extend(legacy_entries)
            
            motif_details.append({
                'motif_id': instance.motif_id,
                'instance_id': instance.instance_id,
                'residues': [r.to_tuple() for r in instance.residues],
                'annotation': instance.annotation,
            })
        
        if not motif_list:
            self.logger.debug(f"No residues found for {motif_type} motifs in {pdb_id}")
            return
        
        motif_type_upper = motif_type.upper()
        color_rgb = colors.get_color(motif_type_upper)
        
        # STEP 1: Hide motif residues on the MAIN structure to prevent z-fighting
        # Build combined selection for all residues of this motif type
        from .utils.parser import SelectionParser
        all_selections = []
        for motif in motif_list:
            chain = motif.get('chain')
            residues = motif.get('residues')
            sel = SelectionParser.create_selection_string(chain, residues)
            if sel:
                all_selections.append(f"({sel})")
        
        if all_selections:
            combined_sel = " or ".join(all_selections)
            main_motif_sel = f"({structure_name}) and ({combined_sel})"
            # Hide the cartoon on main structure for these residues
            self.cmd.hide('cartoon', main_motif_sel)
        
        # STEP 2: Create PyMOL object (visible in right panel)
        obj_name = self.selector.create_motif_class_object(
            structure_name,
            motif_type_upper,
            motif_list,
        )
        
        if obj_name:
            # Show cartoon on the motif object
            self.cmd.show('cartoon', obj_name)
            
            # Apply consistent representation settings for uniform appearance
            self.cmd.set('cartoon_nucleic_acid_mode', 4, obj_name)  # Simple tube mode
            self.cmd.set('cartoon_tube_radius', 0.4, obj_name)
            
            # Color the object with the motif color
            colors.set_motif_color_in_pymol(self.cmd, obj_name, motif_type_upper)
            
            # Object stays ENABLED (visible in panel and on screen)
            # No z-fighting because main structure doesn't render these residues
            
            self.loaded_motifs[motif_type_upper] = {
                'object_name': obj_name,
                'structure_name': structure_name,
                'count': len(instances),
                'visible': True,
                'motifs': motif_list,
                'motif_details': motif_details,
                'color_rgb': color_rgb,
                'main_selection': main_motif_sel if all_selections else None,
            }
            
            self.logger.success(f"Loaded {len(instances)} {motif_type_upper} motifs")
    
    def toggle_motif_type(self, motif_type: str, visible: bool) -> bool:
        """
        Toggle visibility of a motif type.
        
        Shows/hides the motif object.
        
        Args:
            motif_type (str): Motif type (e.g., 'HL', 'IL', 'GNRA')
            visible (bool): True to show, False to hide
        
        Returns:
            bool: True if successful
        """
        motif_type = str(motif_type).upper().strip()
        motif_type = motif_type.replace('-', '_').replace(' ', '_')
        
        if motif_type not in self.loaded_motifs:
            self.logger.warning(f"Motif type {motif_type} not loaded")
            return False
        
        info = self.loaded_motifs[motif_type]
        obj_name = info['object_name']
        
        if visible:
            # Show the motif object
            self.cmd.enable(obj_name)
            self.cmd.show('cartoon', obj_name)
        else:
            # Hide the motif object
            self.cmd.disable(obj_name)
        
        self.loaded_motifs[motif_type]['visible'] = visible
        return True
    
    def get_loaded_motifs(self) -> Dict:
        """Get dictionary of loaded motifs."""
        return self.loaded_motifs
    
    def clear_motifs(self) -> None:
        """Clear all loaded motif objects from PyMOL."""
        try:
            for motif_type, info in self.loaded_motifs.items():
                obj_name = info['object_name']
                
                # Delete the object
                try:
                    self.cmd.delete(obj_name)
                except:
                    pass
            
            self.loaded_motifs = {}
            self.logger.info("Cleared all motif objects")
        except Exception as e:
            self.logger.error(f"Failed to clear motifs: {e}")
    
    def reload_motifs(self, structure_name: str, pdb_id: str,
                     provider_id: Optional[str] = None) -> Dict:
        """
        Reload motifs (clear and reload).
        
        Args:
            structure_name (str): Name of structure in PyMOL
            pdb_id (str): PDB ID
            provider_id (str): Optional provider ID
        
        Returns:
            dict: Loaded motifs
        """
        self.clear_motifs()
        return self.load_motifs(structure_name, pdb_id, provider_id)
    
    def get_available_motif_types(self, pdb_id: str,
                                  provider_id: Optional[str] = None) -> List[str]:
        """Get list of motif types available for a PDB."""
        pdb_id = pdb_id.upper()
        
        if provider_id:
            provider = self._registry.get_provider(provider_id)
        else:
            provider = self._registry.get_active_provider()
        
        if not provider:
            return []
        
        motifs = provider.get_motifs_for_pdb(pdb_id)
        return sorted(list(motifs.keys()))
    
    def get_registry(self):
        """Get the database registry."""
        return self._registry


class VisualizationManager:
    """High-level manager for the entire visualization workflow."""
    
    def __init__(self, cmd, database_dir: str):
        """
        Initialize visualization manager.
        
        Args:
            cmd: PyMOL cmd module
            database_dir (str): Path to motif database directory
        """
        self.cmd = cmd
        self.database_dir = database_dir
        self.structure_loader = StructureLoader(cmd)
        self.motif_loader = UnifiedMotifLoader(cmd, database_dir)
        self.logger = get_logger()
        self._current_provider_id = None
    
    def setup_clean_visualization(self, structure_name: str,
                                 background_color: Optional[str] = None) -> None:
        """
        Set up clean RNA visualization with uniform color.
        
        Workflow:
        1. Hide everything
        2. Select all polymer.nucleic (all RNA chains)
        3. Show cartoon representation
        4. Set cartoon nucleic acid mode
        5. Color uniformly with background_color
        
        Args:
            structure_name (str): Name of structure in PyMOL
            background_color (str): Color for the RNA (default: 'gray80')
        """
        try:
            if background_color is None:
                background_color = colors.NON_MOTIF_COLOR or 'gray80'
            
            # Hide everything first
            self.cmd.hide('everything', 'all')
            self.logger.debug("Hidden all objects")
            
            # Select ALL polymer.nucleic
            rna_selection = f"{structure_name}_rna"
            self.cmd.select(rna_selection, f"{structure_name} and polymer.nucleic")
            
            # Show cartoon representation
            self.cmd.show('cartoon', rna_selection)
            
            # Set consistent cartoon nucleic acid settings for uniform appearance
            self.cmd.set('cartoon_nucleic_acid_mode', 4)  # Simple tube mode
            self.cmd.set('cartoon_tube_radius', 0.4)
            
            # Color uniformly
            self.cmd.color(background_color, rna_selection)
            self.logger.info(f"Visualization: All RNA shown as {background_color} cartoon")
            
            # Clean up temporary selection
            self.cmd.delete(rna_selection)
            
        except Exception as e:
            self.logger.error(f"Failed to set up visualization: {e}")
    
    def load_and_visualize(self, pdb_id_or_path: str,
                          background_color: Optional[str] = None,
                          provider_id: Optional[str] = None) -> Dict:
        """
        Complete workflow: load structure and visualize all motifs.
        
        Args:
            pdb_id_or_path (str): PDB ID or file path
            background_color (str): Color for RNA backbone (default: 'gray80')
            provider_id (str): Optional database provider ID
        
        Returns:
            dict: Loaded motifs, or empty dict if failed
        """
        # Load structure
        structure_name = self.structure_loader.load_structure(pdb_id_or_path)
        if not structure_name:
            return {}
        
        pdb_id = self.structure_loader.get_current_pdb_id()
        
        # Set up clean visualization
        self.setup_clean_visualization(structure_name, background_color)
        
        # Load motifs from specified or active provider
        motifs = self.motif_loader.load_motifs(structure_name, pdb_id, provider_id)
        
        if provider_id:
            self._current_provider_id = provider_id
        
        # Print detailed summary table to PyMOL console
        if motifs:
            self._print_motif_summary_table(pdb_id, motifs, provider_id)
        
        return motifs
    
    def switch_database(self, provider_id: str) -> bool:
        """
        Switch to a different database provider.
        
        Args:
            provider_id: ID of the provider to switch to
            
        Returns:
            True if successful
        """
        registry = self.motif_loader.get_registry()
        if registry.set_active_provider(provider_id):
            self._current_provider_id = provider_id
            self.logger.info(f"Switched to database: {provider_id}")
            return True
        return False
    
    def reload_with_database(self, provider_id: str,
                            background_color: Optional[str] = None) -> Dict:
        """
        Reload current structure with a different database.
        
        Args:
            provider_id: Database provider to use
            background_color: Optional background color
            
        Returns:
            Loaded motifs
        """
        structure_name = self.structure_loader.get_current_structure()
        pdb_id = self.structure_loader.get_current_pdb_id()
        
        if not structure_name or not pdb_id:
            self.logger.error("No structure loaded")
            return {}
        
        # Clear existing motifs
        self.motif_loader.clear_motifs()
        
        # Set up visualization again
        self.setup_clean_visualization(structure_name, background_color)
        
        # Switch database and load
        self.switch_database(provider_id)
        return self.motif_loader.load_motifs(structure_name, pdb_id, provider_id)
    
    def get_structure_info(self) -> Dict:
        """Get current structure and motif info."""
        registry = self.motif_loader.get_registry()
        active_provider = registry.get_active_provider()
        
        return {
            'structure': self.structure_loader.get_current_structure(),
            'pdb_id': self.structure_loader.get_current_pdb_id(),
            'motifs': self.motif_loader.get_loaded_motifs(),
            'database': active_provider.info.name if active_provider else None,
            'database_id': self._current_provider_id,
        }
    
    def get_available_databases(self) -> List[Dict]:
        """Get list of available database providers."""
        registry = self.motif_loader.get_registry()
        return [
            {
                'id': pid,
                'name': provider.info.name,
                'description': provider.info.description,
                'motif_types': len(provider.get_available_motif_types()),
                'pdb_count': len(provider.get_available_pdb_ids()),
                'active': pid == self._current_provider_id,
            }
            for pid, provider in registry.get_all_providers().items()
        ]
    
    def get_available_motif_summary(self, pdb_id: str) -> str:
        """Get summary of available motifs for a PDB."""
        motif_types = self.motif_loader.get_available_motif_types(pdb_id)
        if not motif_types:
            return f"No motifs found for {pdb_id}"
        return f"Available motifs: {', '.join(motif_types)}"
    
    def _print_motif_summary_table(self, pdb_id: str, motifs: Dict,
                                   provider_id: Optional[str] = None) -> None:
        """
        Print a simplified summary table of loaded motifs to PyMOL console.
        Shows only motif types and their frequencies.
        
        Args:
            pdb_id: PDB ID
            motifs: Dictionary of loaded motifs
            provider_id: Database provider used
        """
        # Get database name from the last source used
        last_source = self.motif_loader.get_last_source_used()
        
        # Map source IDs to friendly names
        source_names = {
            'atlas': 'RNA 3D Motif Atlas (Local)',
            'rfam': 'Rfam (Local)',
            'bgsu_api': 'BGSU RNA 3D Hub (API)',
            'rfam_api': 'Rfam (API)',
        }
        
        if last_source:
            # Handle comma-separated sources (from 'all' mode)
            if ',' in last_source:
                sources = [source_names.get(s.strip(), s.strip()) for s in last_source.split(',')]
                db_name = ' + '.join(sources)
            else:
                db_name = source_names.get(last_source, last_source)
        else:
            # Fallback to registry
            registry = self.motif_loader.get_registry()
            if provider_id:
                provider = registry.get_provider(provider_id)
            else:
                provider = registry.get_active_provider()
            db_name = provider.info.name if provider else "Unknown"
        
        # Build the table
        print("\n" + "=" * 50)
        print(f"  MOTIF SUMMARY - {pdb_id}")
        print("=" * 50)
        print(f"  Database: {db_name}")
        print("-" * 50)
        
        # Header
        print(f"  {'MOTIF TYPE':<20} {'INSTANCES':>12}")
        print("-" * 50)
        
        total_motifs = 0
        
        for motif_type, info in sorted(motifs.items()):
            count = info.get('count', 0)
            total_motifs += count
            print(f"  {motif_type:<20} {count:>12}")
        
        print("-" * 50)
        print(f"  {'TOTAL':<20} {total_motifs:>12}")
        print("=" * 50)
        print("\n  Next steps:")
        if total_motifs > 0:
            # Find the first motif type to suggest
            first_motif = None
            for motif_type in sorted(motifs.keys()):
                if motifs[motif_type].get('count', 0) > 0:
                    first_motif = motif_type
                    break
            if first_motif:
                print(f"    rmv_show {first_motif:<20}  Highlight & view {first_motif} instances")
            print(f"    rmv_summary              Display this summary again")
            print(f"    rmv_all                  Show all motifs (default view)")
        print("=" * 50 + "\n")
    
    def show_motif_type(self, motif_type: str) -> bool:
        """
        Show only a specific motif type highlighted, with full structure visible in gray.
        
        Workflow:
        1. Create PyMOL object if needed (for visibility in object panel)
        2. Hide ALL separate motif objects (avoid overlap/stripe artifacts)
        3. Show full PDB structure uniformly
        4. Color the entire structure gray80
        5. Color ONLY the selected motif residues in their color (within the structure)
        
        Args:
            motif_type: Motif type to show (e.g., 'GNRA', 'HL')
            
        Returns:
            True if successful
        """
        motif_type = motif_type.upper().strip()
        loaded_motifs = self.motif_loader.get_loaded_motifs()
        
        if motif_type not in loaded_motifs:
            self.logger.error(f"Motif type '{motif_type}' not loaded")
            self.logger.info(f"Available: {', '.join(loaded_motifs.keys())}")
            return False
        
        # Get structure name and motif details
        info = loaded_motifs[motif_type]
        structure_name = info.get('structure_name')
        motif_details = info.get('motif_details', [])
        main_selection = info.get('main_selection')
        motif_list = info.get('motifs', [])  # For PyMOL object creation
        
        if not structure_name:
            self.logger.error("No structure name found")
            return False
        
        # Step 0: Create PyMOL object if it doesn't exist (needed for object panel visibility)
        obj_name = info.get('object_name')
        if not obj_name and motif_list:
            # Create the PyMOL object (like HL_all)
            obj_name = self.motif_loader.selector.create_motif_class_object(
                structure_name,
                motif_type,
                motif_list,
            )
            if obj_name:
                # Color the object with the motif color
                colors.set_motif_color_in_pymol(self.cmd, obj_name, motif_type)
                # Update the info dict
                info['object_name'] = obj_name
                loaded_motifs[motif_type] = info
                self.logger.debug(f"Created PyMOL object: {obj_name}")
        
        # Step 1: Hide ALL separate motif objects (prevents overlap/stripes)
        for mt, mt_info in loaded_motifs.items():
            obj_name_check = mt_info.get('object_name')
            if obj_name_check:
                self.cmd.disable(obj_name_check)
        
        # Hide any previously created instance objects
        for obj in self.cmd.get_object_list():
            for mt in loaded_motifs.keys():
                if obj.startswith(f"{mt}_") and obj[len(mt)+1:].isdigit():
                    self.cmd.disable(obj)
        
        # Step 2: Show the full structure with uniform representation
        self.cmd.enable(structure_name)
        self.cmd.show('cartoon', f"{structure_name} and polymer.nucleic")
        self.cmd.set('cartoon_nucleic_acid_mode', 4, structure_name)
        self.cmd.set('cartoon_tube_radius', 0.4, structure_name)
        
        # Step 3: Color the ENTIRE structure gray80 first
        self.cmd.color('gray80', f"{structure_name} and polymer.nucleic")
        
        # Step 4: Color ONLY the selected motif residues in their color
        if motif_details:
            # Show the motif residues (in case they were hidden)
            if main_selection:
                self.cmd.show('cartoon', main_selection)
            
            # Color each instance individually to avoid PyMOL selection string length limits
            # (Large "or" selections with 100+ instances can exceed PyMOL's parsing limits)
            from .utils.parser import SelectionParser
            for detail in motif_details:
                residues = detail.get('residues', [])
                if not residues:
                    continue
                
                # Build selection for this individual instance
                chain_residues = {}
                for res in residues:
                    if isinstance(res, tuple) and len(res) >= 3:
                        nucleotide, resi, chain = res[0], res[1], res[2]
                        if chain not in chain_residues:
                            chain_residues[chain] = []
                        chain_residues[chain].append(resi)
                
                # Create selection for this instance and color it
                selections = []
                for chain, resi_list in chain_residues.items():
                    sel = SelectionParser.create_selection_string(chain, sorted(resi_list))
                    if sel:
                        selections.append(f"({sel})")
                
                if selections:
                    combined_sel = " or ".join(selections)
                    instance_sel = f"({structure_name}) and ({combined_sel})"
                    # Color this instance with the motif color
                    colors.set_motif_color_in_pymol(self.cmd, instance_sel, motif_type)
        
        # Print instance table
        self._print_motif_instance_table(motif_type, motif_details)
        
        self.logger.success(f"Showing {len(motif_details)} {motif_type} instances")
        
        # Print follow-up suggestions
        print("  Next steps:")
        print(f"    rmv_instance {motif_type} <NO>     View specific instance (1-{len(motif_details)})")
        print(f"    rmv_show <OTHER_MOTIF>       Show different motif type")
        print(f"    rmv_all                      Show all motifs")
        print()
        return True
    
    def _create_single_instance_object(self, motif_type: str, instance_no: int,
                                         detail: Dict, structure_name: str) -> bool:
        """
        Create a single PyMOL object for one motif instance (on-demand).
        
        Args:
            motif_type: Motif type (e.g., 'HL', 'GNRA')
            instance_no: 1-indexed instance number
            detail: Single motif instance detail dict
            structure_name: Name of the structure in PyMOL
            
        Returns:
            True if successful
        """
        from .utils.parser import SelectionParser
        
        residues = detail.get('residues', [])
        
        if not residues:
            return False
        
        # Build selection for this instance
        chain_residues = {}
        for res in residues:
            if isinstance(res, tuple) and len(res) >= 3:
                nucleotide, resi, chain = res[0], res[1], res[2]
                if chain not in chain_residues:
                    chain_residues[chain] = []
                chain_residues[chain].append(resi)
        
        # Create selection
        selections = []
        for chain, resi_list in chain_residues.items():
            sel = SelectionParser.create_selection_string(chain, sorted(resi_list))
            if sel:
                selections.append(f"({sel})")
        
        if not selections:
            return False
        
        combined_sel = " or ".join(selections)
        instance_sel = f"({structure_name}) and ({combined_sel})"
        
        # Create object name: MOTIF_NO (e.g., GNRA_1, GNRA_2)
        obj_name = f"{motif_type}_{instance_no}"
        
        # Create the object
        try:
            self.cmd.create(obj_name, instance_sel)
            self.cmd.show('cartoon', obj_name)
            self.cmd.set('cartoon_nucleic_acid_mode', 4, obj_name)
            self.cmd.set('cartoon_tube_radius', 0.4, obj_name)
            colors.set_motif_color_in_pymol(self.cmd, obj_name, motif_type)
            return True
        except Exception as e:
            self.logger.debug(f"Could not create object {obj_name}: {e}")
            return False

    def _print_motif_instance_table(self, motif_type: str, motif_details: List[Dict]) -> None:
        """
        Print detailed instance table for a motif type.
        
        Args:
            motif_type: Motif type
            motif_details: List of motif instance details
        """
        print("\n" + "=" * 70)
        print(f"  {motif_type} MOTIF INSTANCES")
        print("=" * 70)
        print(f"  Total Instances: {len(motif_details)}")
        print("-" * 70)
        print(f"  {'NO.':<6} {'CHAIN':<10} {'RESIDUE RANGE':<25} {'NUCLEOTIDES':<25}")
        print("-" * 70)
        
        for idx, detail in enumerate(motif_details, 1):
            residues = detail.get('residues', [])
            
            if not residues:
                print(f"  {idx:<6} {'-':<10} {'-':<25} {'-':<25}")
                continue
            
            # Group by chain
            chain_info = {}
            for res in residues:
                if isinstance(res, tuple) and len(res) >= 3:
                    nucleotide, resi, chain = res[0], res[1], res[2]
                    if chain not in chain_info:
                        chain_info[chain] = {'min': resi, 'max': resi, 'nucs': []}
                    else:
                        chain_info[chain]['min'] = min(chain_info[chain]['min'], resi)
                        chain_info[chain]['max'] = max(chain_info[chain]['max'], resi)
                    if nucleotide:
                        chain_info[chain]['nucs'].append(nucleotide)
            
            # Format output
            chains = ', '.join(sorted(chain_info.keys()))
            
            # Residue ranges
            range_parts = []
            for chain in sorted(chain_info.keys()):
                ci = chain_info[chain]
                range_parts.append(f"{chain}:{ci['min']}-{ci['max']}")
            residue_range = ', '.join(range_parts)
            
            # Nucleotides
            all_nucs = []
            for chain in sorted(chain_info.keys()):
                all_nucs.extend(chain_info[chain]['nucs'])
            nucs_str = ''.join(all_nucs[:20])
            if len(all_nucs) > 20:
                nucs_str += '...'
            
            # Truncate if too long
            if len(residue_range) > 23:
                residue_range = residue_range[:20] + '...'
            
            print(f"  {idx:<6} {chains:<10} {residue_range:<25} {nucs_str:<25}")
        
        print("-" * 70)
        print("\n  To view a specific instance:")
        print(f"    rmv_instance {motif_type} <NO>")
        print(f"    Example: rmv_instance {motif_type} 1")
        print("=" * 70 + "\n")
    
    def show_motif_instance(self, motif_type: str, instance_no: int) -> bool:
        """
        Show only a specific instance of a motif type highlighted, with full structure in gray.
        Creates a separate PyMOL object for the instance.
        
        Workflow:
        1. Hide all separate motif objects
        2. Show full structure in gray80
        3. Create a separate object for the instance and highlight it
        
        Args:
            motif_type: Motif type (e.g., 'GNRA')
            instance_no: Instance number (1-indexed)
            
        Returns:
            True if successful
        """
        motif_type = motif_type.upper().strip()
        loaded_motifs = self.motif_loader.get_loaded_motifs()
        
        if motif_type not in loaded_motifs:
            self.logger.error(f"Motif type '{motif_type}' not loaded")
            return False
        
        info = loaded_motifs[motif_type]
        motif_details = info.get('motif_details', [])
        structure_name = info.get('structure_name')
        
        if instance_no < 1 or instance_no > len(motif_details):
            self.logger.error(f"Instance {instance_no} not found. Valid range: 1-{len(motif_details)}")
            return False
        
        if not structure_name:
            self.logger.error("No structure name found")
            return False
        
        # Step 1: Hide ALL separate motif objects
        for mt, mt_info in loaded_motifs.items():
            obj_name = mt_info.get('object_name')
            if obj_name:
                self.cmd.disable(obj_name)
        
        # Hide any previously created instance objects
        for obj in self.cmd.get_object_list():
            for mt in loaded_motifs.keys():
                if obj.startswith(f"{mt}_") and obj[len(mt)+1:].isdigit():
                    self.cmd.disable(obj)
        
        # Step 2: Show the full structure with uniform representation in gray80
        self.cmd.enable(structure_name)
        self.cmd.show('cartoon', f"{structure_name} and polymer.nucleic")
        self.cmd.set('cartoon_nucleic_acid_mode', 4, structure_name)
        self.cmd.set('cartoon_tube_radius', 0.4, structure_name)
        self.cmd.color('gray80', f"{structure_name} and polymer.nucleic")
        
        # Step 3: Color the instance residues WITHIN the main structure
        detail = motif_details[instance_no - 1]
        residues = detail.get('residues', [])
        instance_obj = f"{motif_type}_{instance_no}"
        
        if residues:
            from .utils.parser import SelectionParser
            
            # Build chain-residue mapping
            chain_residues = {}
            for res in residues:
                if isinstance(res, tuple) and len(res) >= 3:
                    nucleotide, resi, chain = res[0], res[1], res[2]
                    if chain not in chain_residues:
                        chain_residues[chain] = []
                    chain_residues[chain].append(resi)
            
            # Create selection for this instance
            selections = []
            for chain, resi_list in chain_residues.items():
                sel = SelectionParser.create_selection_string(chain, sorted(resi_list))
                if sel:
                    selections.append(f"({sel})")
            
            if selections:
                combined_sel = " or ".join(selections)
                instance_sel = f"({structure_name}) and ({combined_sel})"
                
                # Color the instance residues WITHIN the main structure (no overlap)
                colors.set_motif_color_in_pymol(self.cmd, instance_sel, motif_type)
                
                # Create object for the panel (disabled - just for reference)
                existing_objects = self.cmd.get_object_list()
                if instance_obj not in existing_objects:
                    try:
                        self.cmd.create(instance_obj, instance_sel)
                        self.cmd.set('cartoon_nucleic_acid_mode', 4, instance_obj)
                        self.cmd.set('cartoon_tube_radius', 0.4, instance_obj)
                        colors.set_motif_color_in_pymol(self.cmd, instance_obj, motif_type)
                        # Disable so it doesn't render (avoids overlap)
                        self.cmd.disable(instance_obj)
                    except Exception as e:
                        self.logger.debug(f"Could not create instance object: {e}")
                else:
                    # Object exists, just disable it
                    self.cmd.disable(instance_obj)
                
                # Zoom to the instance (using the selection, not the object)
                self.cmd.zoom(instance_sel, 5)
        
        # Print instance details
        self._print_single_instance_info(motif_type, instance_no, detail)
        
        # Print follow-up suggestions
        print("  Next steps:")
        if instance_no > 1:
            print(f"    rmv_instance {motif_type} {instance_no-1}         View previous instance")
        if instance_no < len(motif_details):
            print(f"    rmv_instance {motif_type} {instance_no+1}         View next instance")
        print(f"    rmv_show {motif_type}               Show all {motif_type} instances")
        print(f"    rmv_all                      Show all motifs")
        print()
        
        return True
    
    def _print_single_instance_info(self, motif_type: str, instance_no: int, 
                                     detail: Dict) -> None:
        """Print information about a single motif instance."""
        residues = detail.get('residues', [])
        instance_id = detail.get('instance_id', f'{motif_type}_{instance_no}')
        annotation = detail.get('annotation', '')
        
        print("\n" + "=" * 50)
        print(f"  {motif_type} INSTANCE #{instance_no}")
        print("=" * 50)
        print(f"  Instance ID: {instance_id}")
        if annotation:
            print(f"  Annotation: {annotation}")
        print(f"  Residues: {len(residues)}")
        print("-" * 50)
        
        # List all residues
        print(f"  {'CHAIN':<8} {'RESI':<8} {'NUCLEOTIDE':<12}")
        print("-" * 50)
        
        for res in residues:
            if isinstance(res, tuple) and len(res) >= 3:
                nucleotide, resi, chain = res[0], res[1], res[2]
                print(f"  {chain:<8} {resi:<8} {nucleotide:<12}")
        
        print("=" * 50)
        print(f"  Object: {motif_type}_{instance_no}")
        print("=" * 50 + "\n")
    
    def show_all_motifs(self) -> None:
        """
        Show all loaded motifs with full structure visible (reset to default view).
        
        Workflow:
        1. Hide ALL separate motif objects (avoid overlap/stripe artifacts)
        2. Show full PDB structure uniformly in gray80
        3. Color each motif type's residues in the structure with their color
        """
        loaded_motifs = self.motif_loader.get_loaded_motifs()
        
        # Get structure name
        structure_name = None
        for info in loaded_motifs.values():
            if info.get('structure_name'):
                structure_name = info.get('structure_name')
                break
        
        if not structure_name:
            self.logger.error("No structure loaded")
            return
        
        # Step 1: Hide ALL separate motif objects (prevents overlap/stripes)
        for motif_type, info in loaded_motifs.items():
            obj_name = info.get('object_name')
            if obj_name:
                self.cmd.disable(obj_name)
            
            # Also disable individual instance objects
            motif_details = info.get('motif_details', [])
            for i in range(1, len(motif_details) + 1):
                try:
                    self.cmd.disable(f"{motif_type}_{i}")
                except:
                    pass
        
        # Step 2: Show the full structure with uniform representation
        self.cmd.enable(structure_name)
        self.cmd.show('cartoon', f"{structure_name} and polymer.nucleic")
        self.cmd.set('cartoon_nucleic_acid_mode', 4, structure_name)
        self.cmd.set('cartoon_tube_radius', 0.4, structure_name)
        
        # Step 3: Color the ENTIRE structure gray80 first
        self.cmd.color('gray80', f"{structure_name} and polymer.nucleic")
        
        # Step 4: Color each motif type's residues in their color
        for motif_type, info in loaded_motifs.items():
            motif_details = info.get('motif_details', [])
            if not motif_details:
                continue
            
            # Color each instance individually to avoid PyMOL selection string length limits
            from .utils.parser import SelectionParser
            for detail in motif_details:
                residues = detail.get('residues', [])
                if not residues:
                    continue
                
                # Build selection for this individual instance
                chain_residues = {}
                for res in residues:
                    if isinstance(res, tuple) and len(res) >= 3:
                        nucleotide, resi, chain = res[0], res[1], res[2]
                        if chain not in chain_residues:
                            chain_residues[chain] = []
                        chain_residues[chain].append(resi)
                
                # Create selection for this instance and color it
                selections = []
                for chain, resi_list in chain_residues.items():
                    sel = SelectionParser.create_selection_string(chain, sorted(resi_list))
                    if sel:
                        selections.append(f"({sel})")
                
                if selections:
                    combined_sel = " or ".join(selections)
                    instance_sel = f"({structure_name}) and ({combined_sel})"
                    # Show and color this instance
                    try:
                        self.cmd.show('cartoon', instance_sel)
                        colors.set_motif_color_in_pymol(self.cmd, instance_sel, motif_type)
                    except Exception as e:
                        self.logger.debug(f"Could not color instance {motif_type}: {e}")
        
        self.logger.info("All motifs shown")
        
        # Print follow-up suggestions
        print("\n  Next steps:")
        if loaded_motifs:
            first_motif = next(iter(sorted(loaded_motifs.keys())), None)
            if first_motif:
                print(f"    rmv_show {first_motif:<20}  Highlight specific motif type")
        print(f"    rmv_summary              View motif summary table")
        print(f"    rna_load <PDB_ID>        Load a different structure")
        print()
