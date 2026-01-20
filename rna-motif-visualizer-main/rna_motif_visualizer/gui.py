"""
RNA Motif Visualizer - GUI Module
Provides PyMOL GUI interface for the plugin with multi-database support.

This module provides:
- MotifVisualizerGUI: Main GUI class for the plugin
- PyMOL command registration
- Database selection and switching functionality

Author: CBB Lab
Version: 2.0.0
"""

from pymol import cmd
from .loader import VisualizationManager
from .utils import get_logger
from . import colors
from .database import get_registry
from pathlib import Path


class MotifVisualizerGUI:
    """PyMOL GUI for RNA motif visualization with multi-database support."""
    
    def __init__(self):
        """Initialize GUI components."""
        self.logger = get_logger()
        
        # Get path to motif database
        plugin_dir = Path(__file__).parent
        self.database_dir = plugin_dir / 'motif_database'
        
        # Initialize visualization manager
        self.viz_manager = VisualizationManager(cmd, str(self.database_dir))
        
        # Track UI state
        self.motif_visibility = {}
        
        # Track currently loaded PDB
        self.loaded_pdb = None
        self.loaded_pdb_id = None
        
        # Track current source mode
        self.current_source_mode = None
        self.current_user_tool = None
        self.current_local_source = None      # 'atlas', 'rfam', or None (for both)
        self.current_web_source = None         # 'bgsu', 'rfam', or None (for auto)
    
    def load_structure_action(self, pdb_id_or_path, background_color=None,
                              database=None):
        """
        Load structure and automatically visualize all motifs.
        
        Args:
            pdb_id_or_path (str): PDB ID or file path
            background_color (str): Color for RNA backbone (default: 'gray80')
            database (str): Database to use ('atlas', 'rfam', or None for active)
        """
        try:
            self.logger.info(f"Loading structure: {pdb_id_or_path}")
            
            # Load and visualize with specified database
            motifs = self.viz_manager.load_and_visualize(
                pdb_id_or_path, 
                background_color,
                provider_id=database
            )
            
            if not motifs:
                self.logger.warning("No motifs found or error loading structure")
                return
            
            # Update UI state
            self.motif_visibility = {}
            for motif_type, info in motifs.items():
                self.motif_visibility[motif_type] = True
            
            self.logger.success(f"Loaded {len(motifs)} motif types")
            
        except Exception as e:
            self.logger.error(f"Failed to load structure: {e}")
    
    def fetch_motif_data_action(self, pdb_id, background_color=None):
        """
        Load motif data for a structure WITHOUT creating PyMOL objects (for rmv_fetch).
        
        Args:
            pdb_id (str): PDB ID already loaded in PyMOL
            background_color (str): Optional background color
        """
        try:
            # Set background color if specified
            if background_color:
                cmd.bg_color(background_color)
            
            # Store structure info
            structure_name = pdb_id.lower()
            self.loaded_pdb = structure_name
            self.loaded_pdb_id = pdb_id.upper()
            
            # Load motif data directly from provider WITHOUT creating PyMOL objects
            pdb_id_upper = pdb_id.upper()
            
            # Get active provider and fetch motifs (data only, no visualization)
            from .database import get_source_selector
            source_selector = get_source_selector()
            
            if source_selector:
                # Get motif data from source selector
                available_motifs, source_used = source_selector.get_motifs_for_pdb(pdb_id_upper)
                source_name = source_used or "unknown"
            else:
                # Fall back to active provider
                registry = self.viz_manager.motif_loader._registry
                provider = registry.get_active_provider()
                if not provider:
                    self.logger.error("No database provider available")
                    return
                
                available_motifs = provider.get_motifs_for_pdb(pdb_id_upper)
                source_name = provider.info.name if hasattr(provider, 'info') else 'unknown'
            
            if not available_motifs:
                self.logger.warning(f"No motifs found for {pdb_id}")
                return
            
            # Count total motifs
            total_count = sum(len(instances) for instances in available_motifs.values())
            self.logger.success(f"Found {total_count} motifs in {pdb_id} (source: {source_name})")
            
            # Process motifs for data access (WITHOUT creating PyMOL objects)
            motif_summary = {}
            from .utils.parser import SelectionParser
            
            for motif_type, instances in available_motifs.items():
                display_type = motif_type.split(':')[-1] if ':' in motif_type else motif_type
                display_type_upper = display_type.upper()
                
                # Convert to motif details format (same as _load_motif_type does)
                motif_details = []
                motif_list = []
                
                for instance in instances:
                    if hasattr(instance, 'residues') and instance.residues:
                        motif_details.append({
                            'motif_id': instance.motif_id,
                            'instance_id': instance.instance_id,
                            'residues': [r.to_tuple() for r in instance.residues],
                            'annotation': instance.annotation,
                        })
                        
                        # Also build motif_list for selection string creation
                        legacy_entries = instance.to_legacy_format()
                        motif_list.extend(legacy_entries)
                
                # Build main_selection string (needed for show_motif_type to work)
                main_motif_sel = None
                if motif_list:
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
                
                if motif_details:
                    motif_summary[display_type_upper] = {
                        'object_name': None,  # Will be created when rmv_show is called
                        'structure_name': structure_name,
                        'count': len(motif_details),
                        'visible': False,
                        'motif_details': motif_details,
                        'motifs': motif_list,  # Needed to create PyMOL objects later
                        'main_selection': main_motif_sel,
                    }
                    self.logger.success(f"Loaded {len(motif_details)} {display_type_upper} motifs")
            
            # Store in viz_manager's motif_loader for rmv_summary/rmv_show to access
            self.viz_manager.motif_loader.loaded_motifs = motif_summary
            
            if motif_summary:
                self.logger.success(f"Loaded {len(motif_summary)} motif types from {pdb_id}")
                self.logger.info("")
                self.logger.info("Motif data ready (not rendered, no objects created)")
                self.logger.info("Next steps:")
                self.logger.info(f"  rmv_summary              Show all motifs")
                self.logger.info(f"  rmv_summary HL           Show HL instances")
                self.logger.info(f"  rmv_show HL              Render hairpin loops")
                self.logger.info("")
            else:
                self.logger.warning(f"No valid motifs found for {pdb_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to load motif data: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def load_user_annotations_action(self, tool_name, pdb_id):
        """
        Load user annotations for a PDB structure.
        
        Args:
            tool_name (str): Name of the tool (fr3d, rnamotifscan)
            pdb_id (str): PDB ID
        """
        try:
            # Store structure info
            structure_name = pdb_id.lower()
            self.loaded_pdb = structure_name
            self.loaded_pdb_id = pdb_id.upper()
            
            # Load motif data from user annotations
            from .database.source_selector import SourceSelector
            from .database.registry import MotifRegistry
            
            # Get registry and switch to user annotations
            registry = self.viz_manager.motif_loader._registry
            
            # Create temporary source selector for user annotations
            source_selector = SourceSelector(registry)
            source_selector.select_source_by_name('user')
            
            # Get motifs for this tool and PDB
            available_motifs = source_selector.get_motifs_for_pdb_and_tool(pdb_id.upper(), tool_name)
            
            if not available_motifs:
                self.logger.warning(f"No motifs found for {pdb_id} using {tool_name}")
                return
            
            # Process motifs
            motif_summary = {}
            from .utils.parser import SelectionParser
            
            for motif_type, instances in available_motifs.items():
                display_type = motif_type.split(':')[-1] if ':' in motif_type else motif_type
                display_type_upper = display_type.upper()
                
                motif_details = []
                motif_list = []
                
                for instance in instances:
                    if hasattr(instance, 'residues') and instance.residues:
                        motif_details.append({
                            'motif_id': instance.motif_id,
                            'instance_id': instance.instance_id,
                            'residues': [r.to_tuple() for r in instance.residues],
                            'annotation': instance.annotation,
                        })
                        
                        legacy_entries = instance.to_legacy_format()
                        motif_list.extend(legacy_entries)
                
                # Build main_selection string
                main_motif_sel = None
                if motif_list:
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
                
                if motif_details:
                    motif_summary[display_type_upper] = {
                        'object_name': None,
                        'structure_name': structure_name,
                        'count': len(motif_details),
                        'visible': False,
                        'motif_details': motif_details,
                        'motifs': motif_list,
                        'main_selection': main_motif_sel,
                    }
            
            # Store in viz_manager's motif_loader
            self.viz_manager.motif_loader.loaded_motifs = motif_summary
            
            total_count = sum(len(instances) for instances in available_motifs.values())
            self.logger.success(f"Found {total_count} motifs in {pdb_id} from {tool_name}")
            
            if motif_summary:
                self.logger.success(f"Loaded {len(motif_summary)} motif types from {pdb_id}")
                self.logger.info("")
                self.logger.info("Motif data ready (not rendered, no objects created)")
                self.logger.info("Next steps:")
                self.logger.info(f"  rmv_summary              Show all motifs")
                self.logger.info(f"  rmv_show HL              Render hairpin loops")
                self.logger.info("")
            else:
                self.logger.warning(f"No valid motifs found for {pdb_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to load user annotations: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def load_user_annotations_action(self, tool, pdb_id):
        """
        Load motifs from user-uploaded annotation files.
        
        Args:
            tool (str): Tool name ('fr3d', 'rnamotifscan')
            pdb_id (str): PDB ID to load annotations for
        """
        try:
            from .database.user_annotations import UserAnnotationProvider
            
            # Initialize user annotation provider
            plugin_dir = Path(__file__).parent
            user_annotations_dir = plugin_dir / 'database' / 'user_annotations'
            provider = UserAnnotationProvider(str(user_annotations_dir))
            
            # Get motifs
            pdb_id_upper = pdb_id.upper()
            available_motifs = provider.get_motifs_for_pdb(pdb_id_upper)
            
            if not available_motifs:
                self.logger.warning(f"No {tool.upper()} annotation files found for {pdb_id}")
                self.logger.info(f"Please place files in: database/user_annotations/{tool}/")
                return
            
            # Store structure info
            structure_name = pdb_id_upper.lower()
            self.loaded_pdb = structure_name
            self.loaded_pdb_id = pdb_id_upper
            
            # For FR3D: Map numeric chain IDs to actual PyMOL chain IDs
            # FR3D uses numeric chains like "1", but PyMOL uses letters like "A"
            chain_mapping = {}
            if tool.lower() == 'fr3d':
                # Query the actual chains in the loaded structure
                try:
                    from pymol import cmd
                    actual_chains = cmd.get_chains(structure_name)
                    if actual_chains:
                        # Map numeric FR3D chains to actual chains
                        # Typically: "1" -> "A", "2" -> "B", etc.
                        for idx, actual_chain in enumerate(sorted(actual_chains), 1):
                            chain_mapping[str(idx)] = actual_chain
                except Exception as e:
                    self.logger.debug(f"Could not get chains from structure: {e}")
            
            # Process motifs (same as fetch_motif_data_action)
            motif_summary = {}
            from .utils.parser import SelectionParser
            
            total_count = sum(len(instances) for instances in available_motifs.values())
            self.logger.success(f"Found {total_count} motifs in {pdb_id} (source: {tool.upper()})")
            
            for motif_type, instances in available_motifs.items():
                display_type_upper = motif_type.upper()
                
                # Convert to motif details format
                motif_details = []
                motif_list = []
                
                for instance in instances:
                    if hasattr(instance, 'residues') and instance.residues:
                        # Remap chains if FR3D chain mapping exists
                        residues_to_use = instance.residues
                        if chain_mapping:
                            # Handle both ResidueSpec objects and tuples
                            remapped = []
                            for res in instance.residues:
                                if hasattr(res, 'to_tuple'):
                                    # ResidueSpec object
                                    nuc, resi, chain = res.to_tuple()
                                else:
                                    # Already a tuple
                                    nuc, resi, chain = res
                                remapped.append((nuc, resi, chain_mapping.get(chain, chain)))
                            residues_to_use = remapped
                        
                        motif_details.append({
                            'motif_id': instance.motif_id,
                            'instance_id': instance.instance_id,
                            'residues': residues_to_use,
                            'annotation': instance.annotation,
                        })
                        
                        # Build motif_list for selection string with remapped chains
                        if chain_mapping:
                            # Convert residues to tuples and remap
                            residue_tuples = []
                            for res in instance.residues:
                                if hasattr(res, 'to_tuple'):
                                    nuc, resi, chain = res.to_tuple()
                                else:
                                    nuc, resi, chain = res
                                residue_tuples.append((nuc, resi, chain_mapping.get(chain, chain)))
                            
                            # Create temporary instance with remapped residues for legacy format
                            from .database.user_annotations.converters import MotifInstanceSimple
                            temp_instance = MotifInstanceSimple(
                                instance.motif_id,
                                instance.instance_id,
                                residue_tuples,
                                instance.annotation
                            )
                            legacy_entries = temp_instance.to_legacy_format()
                        else:
                            # Use original logic but handle ResidueSpec objects
                            residue_tuples = []
                            for res in instance.residues:
                                if hasattr(res, 'to_tuple'):
                                    residue_tuples.append(res.to_tuple())
                                else:
                                    residue_tuples.append(res)
                            
                            from .database.user_annotations.converters import MotifInstanceSimple
                            temp_instance = MotifInstanceSimple(
                                instance.motif_id,
                                instance.instance_id,
                                residue_tuples,
                                instance.annotation
                            )
                            legacy_entries = temp_instance.to_legacy_format()
                        motif_list.extend(legacy_entries)
                
                # Build main_selection string
                main_motif_sel = None
                if motif_list:
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
                
                if motif_details:
                    motif_summary[display_type_upper] = {
                        'object_name': None,
                        'structure_name': structure_name,
                        'count': len(motif_details),
                        'visible': False,
                        'motif_details': motif_details,
                        'motifs': motif_list,
                        'main_selection': main_motif_sel,
                    }
                    self.logger.success(f"Loaded {len(motif_details)} {display_type_upper} motifs")
            
            # Store in viz_manager
            self.viz_manager.motif_loader.loaded_motifs = motif_summary
            
            if motif_summary:
                self.logger.success(f"Loaded {len(motif_summary)} motif types from {tool.upper()}")
                self.logger.info("")
                self.logger.info("Motif data ready (not rendered)")
                self.logger.info("Next steps:")
                self.logger.info(f"  rmv_summary              Show all motifs")
                self.logger.info(f"  rmv_summary <TYPE>       Show specific motif type")
                self.logger.info(f"  rmv_show <TYPE>          Render motif on structure")
                self.logger.info("")
            
        except Exception as e:
            self.logger.error(f"Failed to load user annotations: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _list_user_annotations(self):
        """List all available user annotation files."""
        try:
            from pathlib import Path
            plugin_dir = Path(__file__).parent
            user_annotations_dir = plugin_dir / 'database' / 'user_annotations'
            
            print("\n" + "="*60)
            print("Available User Annotation Files")
            print("="*60)
            
            found_any = False
            
            # Check each tool directory
            for tool_dir in user_annotations_dir.iterdir():
                if not tool_dir.is_dir():
                    continue
                
                tool_name = tool_dir.name
                files = list(tool_dir.glob('*.csv')) + list(tool_dir.glob('*.tsv'))
                
                if files:
                    found_any = True
                    print(f"\n{tool_name.upper()}:")
                    for f in files:
                        print(f"  - {f.name}")
            
            if not found_any:
                print("\nNo annotation files found.")
                print("Place files in:")
                print("  - database/user_annotations/fr3d/")
                print("  - database/user_annotations/rnamotifscan/")
            
            print("\n" + "="*60 + "\n")
            
        except Exception as e:
            print(f"Error listing user annotations: {e}")
    
    def switch_database_action(self, database_id):
        """
        Switch to a different database and reload motifs.
        
        Args:
            database_id (str): Database ID to switch to
        """
        try:
            # Check if structure is loaded
            info = self.viz_manager.get_structure_info()
            if not info.get('pdb_id'):
                # Just switch without reloading
                registry = get_registry()
                if registry.set_active_provider(database_id):
                    self.logger.success(f"Switched to database: {database_id}")
                else:
                    self.logger.error(f"Database not found: {database_id}")
                return
            
            # Reload with new database
            motifs = self.viz_manager.reload_with_database(database_id)
            
            if not motifs:
                self.logger.warning(f"No motifs found in {database_id}")
                return
            
            # Update UI state
            self.motif_visibility = {}
            for motif_type, info in motifs.items():
                self.motif_visibility[motif_type] = True
            
            self.logger.success(f"Reloaded with {len(motifs)} motif types from {database_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to switch database: {e}")
    
    def toggle_motif_action(self, motif_type, visible):
        """
        Toggle visibility of a motif type.
        
        Args:
            motif_type (str): Motif type
            visible (bool): Visibility state
        """
        try:
            success = self.viz_manager.motif_loader.toggle_motif_type(motif_type, visible)
            if success:
                self.motif_visibility[motif_type] = visible
                status = "shown" if visible else "hidden"
                self.logger.info(f"Motif {motif_type} {status}")
            else:
                self.logger.warning(f"Could not toggle motif {motif_type}")
        except Exception as e:
            self.logger.error(f"Failed to toggle motif visibility: {e}")
    
    def get_available_motifs(self):
        """
        Get list of available motif types for current PDB.
        
        Returns:
            list: Motif type names
        """
        try:
            pdb_id = self.viz_manager.structure_loader.get_current_pdb_id()
            if not pdb_id:
                return []
            
            motif_types = self.viz_manager.motif_loader.get_available_motif_types(pdb_id)
            return motif_types
        except Exception as e:
            self.logger.error(f"Failed to get motif types: {e}")
            return []
    
    def get_motif_summary(self, pdb_id):
        """
        Get human-readable summary of available motifs for a PDB.
        
        Args:
            pdb_id (str): PDB ID
            
        Returns:
            str: Summary text
        """
        try:
            return self.viz_manager.get_available_motif_summary(pdb_id)
        except Exception as e:
            self.logger.error(f"Failed to get motif summary: {e}")
            return "Error retrieving motif information"
    
    def set_background_color(self, color_name):
        """
        Change the background color of non-motif residues.
        
        Args:
            color_name (str): PyMOL color name (e.g., 'gray80', 'white', 'lightgray')
        """
        try:
            colors.set_background_color(color_name)
            # Recolor the current structure if one is loaded
            current_structure = self.viz_manager.structure_loader.get_current_structure()
            if current_structure:
                cmd.color(color_name, current_structure)
                self.logger.success(f"Background color changed to {color_name}")
            else:
                self.logger.info(f"Background color preference set to {color_name}")
        except Exception as e:
            self.logger.error(f"Failed to change background color: {e}")
    
    def get_motif_info(self, motif_type):
        """
        Get information about a motif type.
        
        Args:
            motif_type (str): Motif type
        
        Returns:
            dict: Motif information
        """
        motif_type_upper = motif_type.upper()
        
        loaded_motifs = self.viz_manager.motif_loader.get_loaded_motifs()
        
        if motif_type_upper not in loaded_motifs:
            return {
                'type': motif_type_upper,
                'loaded': False,
                'count': 0,
                'visible': False,
            }
        
        info = loaded_motifs[motif_type_upper]
        
        return {
            'type': motif_type_upper,
            'loaded': True,
            'count': info.get('count', 0),
            'visible': info.get('visible', False),
            'color': colors.get_color_name(motif_type_upper),
            'description': colors.MOTIF_LEGEND.get(motif_type_upper, {}).get('description', ''),
        }
    
    def list_databases(self):
        """
        List all available databases.
        
        Returns:
            list: Database information dictionaries
        """
        return self.viz_manager.get_available_databases()
    
    def print_status(self):
        """Print current status to PyMOL console."""
        info = self.viz_manager.get_structure_info()
        
        print("\n" + "="*60)
        print("RNA MOTIF VISUALIZER - STATUS")
        print("="*60)
        
        # Database info
        databases = self.list_databases()
        print("\nAvailable Databases:")
        for db in databases:
            active_marker = " [ACTIVE]" if db.get('active') else ""
            print(f"  {db['id']:10s} - {db['name']}{active_marker}")
            print(f"              {db['motif_types']} motif types, {db['pdb_count']} PDB structures")
        
        if info['structure']:
            print(f"\nLoaded Structure: {info['structure']}")
            print(f"PDB ID: {info['pdb_id']}")
            print(f"Using database: {info.get('database', 'N/A')}")
        else:
            print("\nNo structure loaded")
            print("\nTo get started:")
            print("  rmv_load <PDB_ID>")
            print("  rmv_load <PDB_ID>, database=rfam")
            return
        
        if info['motifs']:
            print(f"\nLoaded Motifs ({len(info['motifs'])}):")
            for motif_type, data in info['motifs'].items():
                visible_str = "✓ visible" if data['visible'] else "✗ hidden"
                print(f"  {motif_type:20s} ({data['count']:2d} instances) {visible_str}")
        else:
            print("\nNo motifs loaded for this structure")
        
        print("="*60 + "\n")
    
    def print_sources(self):
        """Print available data sources - clean and simple format."""
        print("\n" + "="*70)
        print("  🗄️  AVAILABLE DATA SOURCES")
        print("="*70)
        
        try:
            from .database import get_config
            config = get_config()
            
            print(f"\n  Currently Active: {config.source_mode.value.upper()}\n")
            
            # Quick reference table
            print("  LOCAL SOURCES (Offline):")
            print("  " + "-"*66)
            print("    rmv_source local              Use local Atlas + Rfam databases")
            print("    rmv_source local atlas        Use local RNA 3D Motif Atlas only")
            print("    rmv_source local rfam         Use local Rfam database only")
            
            print("\n  ONLINE SOURCES (Requires Internet):")
            print("  " + "-"*66)
            print("    rmv_source web                Auto-select online APIs")
            print("    rmv_source web bgsu           Use BGSU RNA 3D Hub API (~3000+ PDBs)")
            print("    rmv_source web rfam           Use Rfam API (named motifs)")
            
            print("\n  COMBINED SOURCES:")
            print("  " + "-"*66)
            print("    rmv_source auto               Auto-select (local first → API) [DEFAULT]")
            print("    rmv_source all                Combine all available sources")
            
            print("\n  USER ANNOTATIONS:")
            print("  " + "-"*66)
            print("    rmv_source user fr3d          Use FR3D analysis output")
            print("    rmv_source user rnamotifscan  Use RNAMotifScan output")
            
            print("\n" + "="*70)
            print("  💡 QUICK START")
            print("="*70)
            print("""
    1. Set source:  rmv_source web bgsu
    2. Load PDB:    rmv_fetch 1S72
    3. Show motifs: rmv_summary
    4. View motif:  rmv_show HL
    5. Get help:    rmv_help
""")
        except Exception as e:
            print(f"  Error loading sources: {e}")
        
        print("="*70 + "\n")
    
    def print_help(self):
        """Print all available commands categorically."""
        print("\n" + "="*75)
        print("  RNA MOTIF VISUALIZER - COMPLETE COMMAND REFERENCE (v2.1.0)")
        print("="*75)
        
        print("""
┌─────────────────────────────────────────────────────────────────────────┐
│  🔌 SOURCE SELECTION COMMANDS                                           │
├─────────────────────────────────────────────────────────────────────────┤
│  rmv_source              Show current source & settings                 │
│  rmv_sources             List all available data sources                │
│                                                                         │
│  LOCAL (Offline):                                                       │
│    rmv_source local          Use bundled databases (Atlas + Rfam)      │
│    rmv_source local atlas    Use RNA 3D Motif Atlas only               │
│    rmv_source local rfam     Use Rfam database only                    │
│                                                                         │
│  ONLINE (Requires Internet):                                            │
│    rmv_source web            Auto-select online APIs (BGSU/Rfam)       │
│    rmv_source web bgsu       Use BGSU RNA 3D Hub (~3000+ PDBs)        │
│    rmv_source web rfam       Use Rfam API (named motifs)               │
│                                                                         │
│  COMBINED:                                                              │
│    rmv_source auto           Auto-select (local first, then API)       │
│    rmv_source all            Combine all sources                       │
│                                                                         │
│  USER ANNOTATIONS:                                                      │
│    rmv_source user fr3d      Load FR3D analysis results                │
│    rmv_source user rnamotifscan  Load RNAMotifScan results             │
├─────────────────────────────────────────────────────────────────────────┤
│  📥 LOADING COMMANDS                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  rmv_fetch <PDB_ID>      Load raw PDB (fast, data only)                │
│  rmv_load <PDB_ID>       Load structure & auto-visualize motifs        │
│  rmv_refresh [PDB_ID]    Force refresh from API (bypass cache)         │
├─────────────────────────────────────────────────────────────────────────┤
│  🎨 VISUALIZATION COMMANDS                                              │
├─────────────────────────────────────────────────────────────────────────┤
│  rmv_all                 Show all motifs (reset view)                   │
│  rmv_show <TYPE>         Highlight specific motif type                 │
│  rmv_show <TYPE> <NO>    Show & zoom to specific instance              │
│  rmv_instance <TYPE> <NO> View instance details & zoom                 │
│  rmv_toggle <TYPE> on/off Toggle motif visibility                      │
│  rmv_bg_color <COLOR>    Change background (non-motif) color           │
│  rmv_color <TYPE> <COLOR> Change motif color                           │
│  rmv_colors              Show color legend for motif types             │
├─────────────────────────────────────────────────────────────────────────┤
│  📊 INFORMATION COMMANDS                                                │
├─────────────────────────────────────────────────────────────────────────┤
│  rmv_summary             Show all motif types & counts                 │
│  rmv_summary <TYPE>      Show instances of specific type               │
│  rmv_summary <TYPE> <NO> Show specific instance details                │
│  rmv_status              Show plugin status & configuration             │
│  rmv_help                Show this command reference                   │
└─────────────────────────────────────────────────────────────────────────┘

  QUICK EXAMPLES:
  ───────────────
  1. Load with local database:
     rmv_source local
     rmv_fetch 1S72
     rmv_summary
     rmv_show HL

  2. Use BGSU online API:
     rmv_source web bgsu
     rmv_fetch 1S72
     rmv_summary

  3. Load user annotations:
     rmv_source user fr3d
     rmv_fetch 1S72
     rmv_summary
     rmv_show HAIRPIN

  4. Explore motifs:
     rmv_show GNRA              # All GNRA instances
     rmv_instance GNRA 1        # Zoom to instance #1
     rmv_color GNRA red         # Change color
     rmv_toggle GNRA off        # Hide GNRA
     rmv_all                    # Show everything

  AVAILABLE COLORS:
  ────────────────
  red, green, blue, yellow, cyan, magenta, orange, purple, pink, white,
  gray, lime, teal, salmon

  MOTIF TYPES:
  ────────────
  Local/BGSU:  HL, IL, J3, J4, J5, J6, J7
  Rfam:        GNRA, UNCG, K-turn, T-loop, C-loop, U-turn
  User Annot:  Depends on analysis (e.g., HAIRPIN, BULGE, HELIX, etc.)

  For detailed documentation, see:
  • README.md    - Complete command reference & examples
  • TUTORIAL.md  - Step-by-step tutorial
  • DEVELOPER.md - Architecture & contribution guide
""")
        print("="*75 + "\n")
    
    def print_motif_summary(self):
        """Print detailed motif summary table to console."""
        info = self.viz_manager.get_structure_info()
        
        # If no info from viz_manager, check if we loaded via rmv_fetch
        if not info.get('pdb_id') and not self.loaded_pdb_id:
            print("\nNo structure loaded. Use 'rmv_fetch <PDB_ID>' or 'rmv_load <PDB_ID>' first.\n")
            return
        
        # Use viz_manager info if available, otherwise use our stored data
        pdb_id = info.get('pdb_id') or self.loaded_pdb_id
        motifs = info.get('motifs', {})
        
        if not motifs:
            print(f"\nNo motifs loaded for {pdb_id}.\n")
            return
        
        # Determine the database name to display
        database_id = info.get('database_id', 'Unknown')
        
        # If user annotations are loaded, show that
        if self.current_user_tool:
            database_id = f"FR3D ({self.current_user_tool.upper()})" if self.current_user_tool == 'fr3d' else f"{self.current_user_tool.upper()}"
        # Map provider IDs to user-friendly names
        elif database_id == 'bgsu_api':
            database_id = "BGSU RNA 3D Hub (Online)"
        elif database_id == 'rfam_api':
            database_id = "Rfam API (Online)"
        elif database_id == 'atlas':
            if self.current_local_source:
                database_id = f"RNA 3D Motif Atlas (Local)"
            else:
                database_id = "Local (Atlas)"
        elif database_id == 'rfam':
            if self.current_local_source:
                database_id = f"Rfam Database (Local)"
            else:
                database_id = "Local (Rfam)"
        
        # Use the visualization manager's summary printer
        self.viz_manager._print_motif_summary_table(pdb_id, motifs, database_id)
    
    def show_motif_summary_for_type(self, motif_type: str):
        """Print summary of a specific motif type without rendering.
        
        Args:
            motif_type (str): Motif type to show (e.g., 'HL', 'IL', 'GNRA')
        """
        motif_arg = motif_type.upper().strip()
        
        # Use the same data source as rmv_show uses
        loaded_motifs = self.viz_manager.motif_loader.get_loaded_motifs()
        
        if not loaded_motifs:
            print("\nNo motifs loaded. Use 'rmv_fetch <PDB_ID>' first.\n")
            return
        
        if motif_arg not in loaded_motifs:
            available = ', '.join(loaded_motifs.keys())
            print(f"\nMotif type '{motif_arg}' not loaded.")
            print(f"Available motifs: {available}\n")
            return
        
        # Get motif details from loaded_motifs (same structure as rmv_show uses)
        motif_info = loaded_motifs[motif_arg]
        motif_details = motif_info.get('motif_details', [])
        
        # Use the visualization manager's table printer (same as rmv_show)
        self.viz_manager._print_motif_instance_table(motif_arg, motif_details)
        
        print("\n  Next steps:")
        print(f"    rmv_show {motif_arg}              Highlight & render {motif_arg}")
        print(f"    rmv_summary {motif_arg} <NO>      Show details of specific instance")
        print("="*70)
        print()
    
    def show_motif_instance_summary(self, motif_type: str, instance_no: int):
        """Print details of a specific motif instance (for rmv_summary MOTIF NO).
        
        Args:
            motif_type (str): Motif type (e.g., 'HL')
            instance_no (int): Instance number (1-indexed)
        """
        motif_arg = motif_type.upper().strip()
        
        # Use the same data source as rmv_show uses
        loaded_motifs = self.viz_manager.motif_loader.get_loaded_motifs()
        
        if not loaded_motifs:
            print("\nNo motifs loaded. Use 'rmv_fetch <PDB_ID>' first.\n")
            return
        
        if motif_arg not in loaded_motifs:
            available = ', '.join(loaded_motifs.keys())
            print(f"\nMotif type '{motif_arg}' not loaded.")
            print(f"Available motifs: {available}\n")
            return
        
        # Get motif details
        motif_info = loaded_motifs[motif_arg]
        motif_details = motif_info.get('motif_details', [])
        
        # Check instance number is valid
        if instance_no < 1 or instance_no > len(motif_details):
            print(f"\nInstance {instance_no} not found. Valid range: 1-{len(motif_details)}\n")
            return
        
        # Get the specific instance (1-indexed)
        detail = motif_details[instance_no - 1]
        
        # Use the visualization manager's instance detail printer (same as rmv_instance uses)
        self.viz_manager._print_single_instance_info(motif_arg, instance_no, detail)
        print()
    
    def set_source_mode(self, mode: str):
        """
        Set the motif data source mode.
        
        Args:
            mode (str): Source mode: auto, local, web, bgsu, rfam, all, user
        """
        try:
            mode_lower = mode.lower()
            
            # Handle user annotations specially
            if mode_lower == 'user':
                self._set_user_annotations_source()
                return
            
            from .database import get_config, SourceMode
            
            mode_map = {
                'auto': SourceMode.AUTO,
                'local': SourceMode.LOCAL,
                'web': SourceMode.AUTO,        # web mode uses AUTO (smart selection)
                'bgsu': SourceMode.BGSU,
                'rfam': SourceMode.RFAM,
                'all': SourceMode.ALL
            }
            
            if mode_lower not in mode_map:
                valid_modes = ['auto', 'local', 'web', 'web bgsu', 'web rfam', 'local atlas', 'local rfam', 'all', 'user fr3d', 'user rnamotifscan']
                self.logger.error(f"Invalid source mode '{mode}'.")
                self.logger.info("Valid source modes:")
                for m in valid_modes:
                    self.logger.info(f"  rmv_source {m}")
                return
            
            config = get_config()
            config.source_mode = mode_map[mode_lower]
            
            mode_display = mode_lower if mode_lower != 'web' else 'web (auto-select online APIs)'
            self.logger.success(f"Motif source mode set to: {mode_display}")
            self._print_source_mode_info()
            
            # Print follow-up suggestions
            print("\n  Next steps:")
            print(f"    rmv_fetch <PDB_ID>         Fetch and load structure + motif data")
            print(f"    Example: rmv_fetch 1S72")
            print()
            
        except Exception as e:
            self.logger.error(f"Failed to set source mode: {e}")
    
    def _set_user_annotations_source(self):
        """Set source to user annotations with tool selection."""
        print("\n" + "="*60)
        print("USER ANNOTATIONS")
        print("="*60)
        print("\nAvailable tools:")
        print("  1. fr3d           - FR3D output format")
        print("  2. rnamotifscan   - RNAMotifScan output format")
        print("\nAfter selecting a tool with rmv_source user <TOOL>,")
        print("use rmv_fetch to load structures:")
        print("\nUsage:")
        print("  rmv_fetch <PDB_ID>")
        print("\nExample:")
        print("  rmv_fetch 1S72")
        print("="*60 + "\n")
        
        # Store that user annotations are selected
        self.current_source_mode = 'user'
        self.logger.success("User Annotations mode selected")
        self.logger.info("Use: rmv_fetch <PDB_ID>")
        self.logger.info("Tools: fr3d, rnamotifscan")
    
    def _print_source_mode_info(self):
        """Print information about current source mode."""
        try:
            from .database import get_config, SourceMode
            
            config = get_config()
            mode = config.source_mode
            
            mode_descriptions = {
                SourceMode.AUTO: "Automatically select best available source (local first, then API)",
                SourceMode.LOCAL: "Use only local bundled databases (offline mode)",
                SourceMode.BGSU: "Use only BGSU RNA 3D Hub API (online, ~3000+ PDBs)",
                SourceMode.RFAM: "Use only Rfam API (online, named motifs)",
                SourceMode.ALL: "Combine all sources (comprehensive, may have duplicates)"
            }
            
            print(f"\nCurrent mode: {mode.value}")
            print(f"Description: {mode_descriptions.get(mode, 'Unknown')}")
            
        except ImportError:
            print("Source selector not available")
    
    def _handle_user_source(self, tool_name):
        """Handle user annotations source selection."""
        if not tool_name:
            self.logger.error("Usage: rmv_source user <tool_name>")
            self.logger.error("Available tools:")
            self.logger.error("  rmv_source user fr3d")
            self.logger.error("  rmv_source user rnamotifscan")
            return
        
        valid_tools = ['fr3d', 'rnamotifscan']
        if tool_name not in valid_tools:
            self.logger.error(f"Invalid tool '{tool_name}'. Valid options: {', '.join(valid_tools)}")
            return
        
        self.current_user_tool = tool_name
        self.current_local_source = None
        self.current_web_source = None
        self.set_source_mode('user')
        self.logger.success(f"Source set to user annotations (tool: {tool_name})")
    
    def _handle_local_source(self, source_name):
        """Handle local source selection."""
        if not source_name:
            # Just 'rmv_source local' - use local (both atlas and rfam)
            self.current_local_source = None
            self.current_web_source = None
            self.current_user_tool = None
            self.set_source_mode('local')
            self.logger.info("Using local sources (RNA 3D Atlas + Rfam database)")
            return
        
        # For specific local sources
        if source_name == 'atlas':
            self.current_local_source = 'atlas'
            self.current_web_source = None
            self.current_user_tool = None
            self.set_source_mode('local')
            self.logger.success("Source set to local RNA 3D Atlas")
        elif source_name == 'rfam':
            self.current_local_source = 'rfam'
            self.current_web_source = None
            self.current_user_tool = None
            self.set_source_mode('local')
            self.logger.success("Source set to local Rfam database")
        else:
            self.logger.error(f"Invalid local source '{source_name}'")
            self.logger.error("Valid local sources: atlas, rfam")
    
    def _handle_web_source(self, source_name):
        """Handle web/online source selection."""
        if not source_name:
            # Just 'rmv_source web' - use smart web source selection
            self.current_web_source = None
            self.current_local_source = None
            self.current_user_tool = None
            self.set_source_mode('web')
            self.logger.info("Using online sources (auto-select between BGSU and Rfam APIs)")
            return
        
        # For specific online sources
        if source_name == 'bgsu':
            self.current_web_source = 'bgsu'
            self.current_local_source = None
            self.current_user_tool = None
            self.set_source_mode('bgsu')
            self.logger.success("Source set to BGSU RNA 3D Hub API (~3000+ PDBs)")
        elif source_name == 'rfam':
            self.current_web_source = 'rfam'
            self.current_local_source = None
            self.current_user_tool = None
            self.set_source_mode('rfam')
            self.logger.success("Source set to Rfam API (named motifs)")
        else:
            self.logger.error(f"Invalid online source '{source_name}'")
            self.logger.error("Valid online sources: bgsu, rfam")
    
    def refresh_motifs_action(self, pdb_id: str = None):
        """
        Force refresh motifs from API (bypass cache).
        
        Args:
            pdb_id (str): PDB ID to refresh (uses current if not specified)
        """
        try:
            info = self.viz_manager.get_structure_info()
            
            if not pdb_id:
                pdb_id = info.get('pdb_id')
            
            if not pdb_id:
                self.logger.error("No PDB ID specified and no structure loaded")
                return
            
            pdb_id = pdb_id.upper()
            self.logger.info(f"Force refreshing motifs for {pdb_id} from API...")
            
            # Clear cache for this PDB
            from .database import get_source_selector
            source_selector = get_source_selector()
            
            if source_selector:
                motifs, source = source_selector.get_motifs_for_pdb(pdb_id, force_refresh=True)
                
                if motifs:
                    total = sum(len(v) for v in motifs.values())
                    self.logger.success(f"Refreshed {total} motifs from {source}")
                    
                    # If this is the currently loaded structure, reload visualization
                    if info.get('pdb_id') == pdb_id and info.get('structure'):
                        self.logger.info("Reloading visualization...")
                        self.viz_manager.reload_with_database(None)
                else:
                    self.logger.warning(f"No motifs found for {pdb_id} in any source")
            else:
                self.logger.error("Source selector not available - API sources may not be initialized")
                
        except Exception as e:
            self.logger.error(f"Failed to refresh motifs: {e}")
    
    def print_source_info(self):
        """Print detailed source configuration and cache status."""
        print("\n" + "="*60)
        print("MOTIF DATA SOURCE CONFIGURATION")
        print("="*60)
        
        try:
            from .database import get_config, get_source_selector, SourceMode
            from .database.cache_manager import get_cache_manager
            
            config = get_config()
            
            # Source mode - with user annotations info
            print(f"\nSource Mode: {config.source_mode.value.upper()}")
            
            # Show specific source selection if applicable
            if self.current_local_source:
                print(f"  └─ Specific Source: {self.current_local_source.upper()}")
            elif self.current_web_source:
                print(f"  └─ Specific Source: {self.current_web_source.upper()}")
            
            # Show active user tool if selected
            if self.current_user_tool:
                print(f"User Annotations Tool: {self.current_user_tool.upper()}")
            
            mode_help = {
                SourceMode.AUTO: "  → Tries local databases first, then APIs if not found",
                SourceMode.LOCAL: "  → Uses only bundled databases (works offline)",
                SourceMode.BGSU: "  → Uses BGSU RNA 3D Hub API (requires internet)",
                SourceMode.RFAM: "  → Uses Rfam API (requires internet)",
                SourceMode.ALL: "  → Combines all sources (most comprehensive)"
            }
            print(mode_help.get(config.source_mode, ""))
            
            # Cache info
            cache_manager = get_cache_manager()
            if cache_manager:
                print(f"\nCache Directory: {cache_manager.cache_dir}")
                print(f"Cache Expiry: {config.freshness_policy.cache_days} days")
                
                # Count cached files
                if cache_manager.cache_dir.exists():
                    cached_files = list(cache_manager.cache_dir.glob("*.json"))
                    meta_files = list(cache_manager.cache_dir.glob("*.meta.json"))
                    data_files = [f for f in cached_files if not f.name.endswith('.meta.json')]
                    print(f"Cached Entries: {len(data_files)}")
            else:
                print("\nCache: Not initialized")
            
            # Source selector status
            source_selector = get_source_selector()
            if source_selector:
                print(f"\nRegistered Sources ({len(source_selector.providers)}):")
                for source_id, provider in source_selector.providers.items():
                    is_api = 'api' in source_id.lower()
                    source_type = "API" if is_api else "Local"
                    print(f"  {source_id:15s} [{source_type}] - {provider.info.name}")
            else:
                print("\nSource Selector: Not initialized")
            
            # Last source used
            loader = self.viz_manager.motif_loader
            if hasattr(loader, 'get_last_source_used'):
                last_source = loader.get_last_source_used()
                if last_source:
                    print(f"\nLast Source Used: {last_source}")
            
        except ImportError as e:
            print(f"\nNote: Advanced source features not available ({e})")
            print("Using standard database registry only.")
        
        print("\n" + "="*60)
        print("Commands:")
        print("  rmv_source auto              - Auto-select best source")
        print("  rmv_source local             - Use only local databases")
        print("  rmv_source bgsu              - Use BGSU API (3000+ PDBs)")
        print("  rmv_source rfam              - Use Rfam API")
        print("  rmv_source all               - Combine all sources")
        print("  rmv_source user <tool>       - Use user annotations (fr3d, rnamotifscan)")
        print("  rmv_switch <DB>              - Switch database (atlas/rfam)")
        print("  rmv_refresh                  - Force refresh from API")
        print("  rmv_source        - Show this information again")
        print("="*60 + "\n")


# Global GUI instance
_gui_instance = None


def get_gui():
    """Get or create global GUI instance."""
    global _gui_instance
    if _gui_instance is None:
        _gui_instance = MotifVisualizerGUI()
    return _gui_instance


def initialize_gui():
    """Initialize GUI and register commands."""
    gui = get_gui()
    
    # Register PyMOL commands
    def fetch_raw_pdb(pdb_id='', background_color='', tool=''):
        """PyMOL command: Load raw PDB and fetch motif data (no rendering).
        
        Fast loading - fetches both structure and motif data without rendering.
        Use rmv_summary after to see available motifs in console.
        
        Usage:
            rmv_fetch 1S72                           # Use current source mode
            rmv_fetch 1S72, bg_color=lightgray       # With background color
            
        If using user annotations, first set source:
            rmv_source user fr3d
            rmv_fetch 1S72
        """
        if not pdb_id:
            gui.logger.error("Usage: rmv_fetch <PDB_ID> [, bg_color=gray80]")
            gui.logger.error("Examples:")
            gui.logger.error("  rmv_fetch 1S72")
            gui.logger.error("  rmv_fetch 1S72, bg_color=lightgray")
            gui.logger.error("")
            gui.logger.error("For user annotations:")
            gui.logger.error("  rmv_source user fr3d")
            gui.logger.error("  rmv_fetch 1S72")
            return
        
        pdb_arg = str(pdb_id).strip()
        bg_arg = str(background_color).strip() if background_color else None
        tool_arg = str(tool).strip().lower() if tool else None
        
        # Load the structure using PyMOL's fetch command
        try:
            structure_name = pdb_arg.lower()
            # Delete any existing object with the same name to avoid "loading mmCIF into existing object" error
            try:
                cmd.delete(structure_name)
            except:
                pass  # Object doesn't exist, that's fine
            cmd.fetch(pdb_arg, structure_name)
            gui.logger.success(f"Loaded structure {pdb_arg}")
            
            # Check if user annotations source is selected
            tool_to_use = tool_arg or gui.current_user_tool
            
            # Load motif data in background (without rendering)
            if tool_to_use:
                gui.load_user_annotations_action(tool_to_use, pdb_arg)
                gui.logger.info(f"Loaded motifs from {tool_to_use} annotations")
            else:
                # Use default source
                gui.fetch_motif_data_action(pdb_arg, bg_arg)
            
        except Exception as e:
            gui.logger.error(f"Failed to load {pdb_arg}: {str(e)}")
    
    def load_structure(pdb_id_or_path='', background_color='', database=''):
        """PyMOL command: Load structure and automatically show all motifs.
        
        Usage:
            rmv_load <pdb_id_or_path>
            rmv_load <pdb_id_or_path>, bg_color=lightgray
            rmv_load <pdb_id_or_path>, database=atlas
            rmv_load <pdb_id_or_path>, database=rfam, bg_color=white
        """
        if not pdb_id_or_path:
            gui.logger.error("Usage: rmv_load <PDB_ID_or_PATH> [, bg_color=gray80] [, database=atlas]")
            return
        
        pdb_arg = str(pdb_id_or_path).strip()
        bg_arg = str(background_color).strip() if background_color else None
        db_arg = str(database).strip() if database else None
        
        gui.load_structure_action(pdb_arg, bg_arg, db_arg)
    
    def switch_database(database_id=''):
        """PyMOL command: Switch to a different database.
        
        Usage:
            rmv_switch atlas
            rmv_switch rfam
        """
        if not database_id:
            gui.print_sources()
            return
        
        gui.switch_database_action(str(database_id).strip())
    
    def toggle_motif(motif_type='', visible=''):
        """PyMOL command: Toggle motif visibility."""
        # PyMOL can pass arguments different ways, so handle both
        
        # Case 1: Both arguments passed separately
        if motif_type and visible:
            motif_arg = motif_type
            visible_arg = visible
        else:
            # Case 2: Everything in motif_type as a single string
            full_arg = str(motif_type).strip()
            parts = full_arg.split()
            
            if len(parts) < 2:
                gui.logger.error(f"Usage: rmv_toggle MOTIF_TYPE on/off")
                gui.logger.error(f"Example: rmv_toggle HL on")
                return
            
            motif_arg = parts[0]
            visible_arg = parts[1]
        
        # Parse visibility
        visible_bool = str(visible_arg).lower() in ['on', 'true', '1', 'yes', 'show']
        motif_arg = str(motif_arg).upper().strip()
        
        gui.toggle_motif_action(motif_arg, visible_bool)
    
    def motif_status():
        """PyMOL command: Show plugin status."""
        gui.print_status()
    
    def list_sources():
        """PyMOL command: Show available data sources."""
        gui.print_sources()
    
    def show_help():
        """PyMOL command: Show all available commands."""
        gui.print_help()
    
    def set_bg_color(color_name='gray80'):
        """PyMOL command: Change background color of non-motif residues."""
        color_arg = str(color_name).strip()
        if not color_arg:
            color_arg = 'gray80'
        gui.set_background_color(color_arg)
    
    def motif_summary(motif_type='', instance_no=''):
        """PyMOL command: Show motif summary table (console only, no rendering).
        
        Usage:
            rmv_summary              Show all motifs summary for loaded PDB
            rmv_summary HL           Show detailed instances of HL motif
            rmv_summary HL 1         Show specific HL instance #1
        """
        if not motif_type:
            # Show general motif summary
            gui.print_motif_summary()
        else:
            # Check if instance number is provided
            motif_arg = str(motif_type).strip().upper()
            
            # Handle both formats: "HL 1" and separate args
            if instance_no:
                try:
                    inst_no = int(instance_no)
                    gui.show_motif_instance_summary(motif_arg, inst_no)
                except ValueError:
                    gui.logger.error("Instance number must be an integer")
            else:
                # Check if the motif_type contains instance number
                parts = motif_arg.split()
                if len(parts) == 2 and parts[1].isdigit():
                    gui.show_motif_instance_summary(parts[0], int(parts[1]))
                else:
                    # Show all instances of the motif type
                    gui.show_motif_summary_for_type(motif_arg)
    
    def set_source(mode='', tool=''):
        """PyMOL command: Set motif data source mode.
        
        Usage:
            rmv_source auto                  - Auto-select best available source
            rmv_source local                 - Use local bundled databases (Atlas + Rfam)
            rmv_source web                   - Use online APIs (smart selection)
            rmv_source local atlas           - Use only local RNA 3D Atlas
            rmv_source local rfam            - Use only local Rfam database
            rmv_source web bgsu              - Use BGSU RNA 3D Hub API
            rmv_source web rfam              - Use Rfam API
            rmv_source all                   - Combine all sources
            rmv_source user fr3d             - Use FR3D user annotations
            rmv_source user rnamotifscan     - Use RNAMotifScan annotations
        """
        if not mode:
            gui.print_source_info()
            return
        
        mode_arg = str(mode).strip().lower()
        tool_arg = str(tool).strip().lower() if tool else None
        
        # Handle PyMOL passing arguments as combined string: "local atlas" or "web bgsu"
        parts = mode_arg.split()
        if len(parts) > 1:
            mode_arg = parts[0]
            if not tool_arg:
                tool_arg = parts[1].lower()
        
        # Route to appropriate handler
        if mode_arg == 'user':
            gui._handle_user_source(tool_arg)
        elif mode_arg == 'local':
            gui._handle_local_source(tool_arg)
        elif mode_arg == 'web':
            gui._handle_web_source(tool_arg)
        else:
            # Old-style: auto, all, etc.
            gui.set_source_mode(mode_arg)
    
    def refresh_motifs(pdb_id=''):
        """PyMOL command: Force refresh motifs from API (bypass cache).
        
        Usage:
            rmv_refresh        - Refresh current structure
            rmv_refresh 4V9F   - Refresh specific PDB
        """
        pdb_arg = str(pdb_id).strip() if pdb_id else None
        gui.refresh_motifs_action(pdb_arg)
    
    def show_motif(motif_type='', instance_no=''):
        """PyMOL command: Show specific motif type, or show specific instance.
        
        Usage:
            rmv_show GNRA          - Show only GNRA motifs (all instances)
            rmv_show HL            - Show only hairpin loops (all instances)
            rmv_show HL 1          - Show specific HL instance #1 (zoom + details)
            rmv_show GNRA 2        - Show specific GNRA instance #2
        """
        if not motif_type:
            gui.logger.error("Usage: rmv_show <MOTIF_TYPE> [<INSTANCE_NO>]")
            gui.logger.error("Example: rmv_show GNRA")
            gui.logger.error("Example: rmv_show HL 1")
            return
        
        motif_arg = str(motif_type).strip().upper()
        
        # Handle both formats: "HL 1" and separate args
        if instance_no:
            try:
                inst_no = int(instance_no)
                gui.viz_manager.show_motif_instance(motif_arg, inst_no)
            except ValueError:
                gui.logger.error("Instance number must be an integer")
        else:
            # Check if the motif_type contains instance number
            parts = motif_arg.split()
            if len(parts) == 2 and parts[1].isdigit():
                gui.viz_manager.show_motif_instance(parts[0], int(parts[1]))
            else:
                # Show all instances of the motif type
                gui.viz_manager.show_motif_type(motif_arg)
    
    def show_instance(motif_type='', instance_no=''):
        """PyMOL command: Show specific instance of a motif type.
        
        Usage:
            rmv_instance GNRA 1   - Show GNRA instance #1
            rmv_instance HL 3     - Show hairpin loop instance #3
        """
        # Handle both separate args and combined string
        if motif_type and instance_no:
            motif_arg = str(motif_type).strip().upper()
            try:
                no_arg = int(instance_no)
            except ValueError:
                gui.logger.error("Instance number must be an integer")
                return
        else:
            # Parse combined string
            full_arg = str(motif_type).strip()
            parts = full_arg.split()
            
            if len(parts) < 2:
                gui.logger.error("Usage: rmv_instance <MOTIF_TYPE> <NO>")
                gui.logger.error("Example: rmv_instance GNRA 1")
                return
            
            motif_arg = parts[0].upper()
            try:
                no_arg = int(parts[1])
            except ValueError:
                gui.logger.error("Instance number must be an integer")
                return
        
        gui.viz_manager.show_motif_instance(motif_arg, no_arg)
    
    def show_all():
        """PyMOL command: Show all motifs (reset to default view)."""
        gui.viz_manager.show_all_motifs()
    
    def load_user_annotations(tool='', pdb_id=''):
        """
        PyMOL command: Load motifs from user-uploaded annotation files.
        
        Supports: FR3D, RNAMotifScan
        
        Usage:
            rmv_user fr3d 1S72          Load FR3D annotations for 1S72
            rmv_user rnamotifscan 1A00  Load RNAMotifScan annotations
            rmv_user list               Show available user annotation files
        """
        # Handle PyMOL argument parsing - may get as single string or separate args
        tool_arg = str(tool).strip() if tool else ''
        pdb_arg = str(pdb_id).strip() if pdb_id else ''
        
        # If tool contains both tool name and pdb_id (space-separated)
        if tool_arg and not pdb_arg:
            parts = tool_arg.split()
            if len(parts) >= 2:
                tool_arg = parts[0]
                pdb_arg = parts[1]
        
        if not tool_arg:
            print("\n" + "="*60)
            print("User Annotation Loader")
            print("="*60)
            print("\nUsage: rmv_user <TOOL> <PDB_ID>")
            print("\nSupported tools:")
            print("  fr3d            FR3D output format")
            print("  rnamotifscan    RNAMotifScan output format")
            print("\nExamples:")
            print("  rmv_user fr3d 1S72")
            print("  rmv_user rnamotifscan 1A00")
            print("  rmv_user list               Show available files")
            print("\nFile locations:")
            print("  FR3D files:        database/user_annotations/fr3d/")
            print("  RNAMotifScan:      database/user_annotations/rnamotifscan/")
            print("="*60 + "\n")
            return
        
        tool_arg = tool_arg.lower().strip()
        
        if tool_arg == 'list':
            gui._list_user_annotations()
            return
        
        if not pdb_arg:
            gui.logger.error("Please specify PDB ID")
            print(f"  Usage: rmv_user {tool_arg} <PDB_ID>")
            return
        
        gui.load_user_annotations_action(tool_arg, pdb_arg)
    
    # Add commands to PyMOL
    cmd.extend('rmv_fetch', fetch_raw_pdb)
    cmd.extend('rmv_load', load_structure)
    cmd.extend('rmv_switch', switch_database)
    cmd.extend('rmv_toggle', toggle_motif)
    cmd.extend('rmv_status', motif_status)
    cmd.extend('rmv_sources', list_sources)
    cmd.extend('rmv_help', show_help)
    cmd.extend('rmv_bg_color', set_bg_color)
    cmd.extend('rmv_summary', motif_summary)
    cmd.extend('rmv_source', set_source)
    cmd.extend('rmv_refresh', refresh_motifs)
    cmd.extend('rmv_show', show_motif)
    cmd.extend('rmv_instance', show_instance)
    cmd.extend('rmv_all', show_all)
    cmd.extend('rmv_user', load_user_annotations)
    
    def show_colors():
        """PyMOL command: Show color legend for all motif types."""
        from . import colors as color_module
        loaded = gui.viz_manager.motif_loader.get_loaded_motifs()
        if loaded:
            color_module.print_color_legend(loaded)
        else:
            color_module.print_color_legend()
    
    cmd.extend('rmv_colors', show_colors)
    
    def set_motif_color(motif_type='', color=''):
        """PyMOL command: Change color of a specific motif type.
        
        Usage:
            rmv_color HL red         Change HL to red
            rmv_color GNRA blue      Change GNRA to blue
            rmv_color IL 0.5 1.0 0.5 Change IL to RGB values
        
        Available colors: red, green, blue, yellow, cyan, magenta, orange,
                         pink, purple, teal, gold, coral, turquoise, etc.
        """
        if not motif_type:
            print("\nUsage: rmv_color <MOTIF_TYPE> <COLOR>")
            print("Examples:")
            print("  rmv_color HL red")
            print("  rmv_color GNRA blue")
            print("  rmv_color IL green")
            print("\nAvailable colors: red, green, blue, yellow, cyan, magenta,")
            print("                  orange, pink, purple, teal, gold, coral, etc.")
            return
        
        if not color:
            gui.logger.error("Please specify a color")
            gui.logger.error("Example: rmv_color HL red")
            return
        
        from . import colors as color_module
        
        motif_arg = str(motif_type).strip().upper()
        color_arg = str(color).strip().lower()
        
        # Set the custom color
        result = color_module.set_custom_motif_color(motif_arg, color_arg)
        
        gui.logger.success(f"Changed {motif_arg} color to {color_arg}")
        
        # Re-apply color to currently loaded motifs if any
        loaded_motifs = gui.viz_manager.motif_loader.get_loaded_motifs()
        if motif_arg in loaded_motifs:
            info = loaded_motifs[motif_arg]
            structure_name = info.get('structure_name')
            main_selection = info.get('main_selection')
            
            # Re-color the motif residues in the structure
            if main_selection:
                try:
                    color_module.set_motif_color_in_pymol(cmd, main_selection, motif_arg)
                    gui.logger.info(f"Applied new color to {motif_arg} residues")
                except Exception as e:
                    gui.logger.debug(f"Could not apply color: {e}")
        
        print(f"\n  {motif_arg} is now colored {color_arg}")
        print(f"  Use 'rmv_show {motif_arg}' or 'rmv_all' to see the change\n")
    
    cmd.extend('rmv_color', set_motif_color)
    
    gui.logger.success("RNA Motif Visualizer GUI initialized")
    gui.logger.info("")
    gui.logger.info("Quick Start:")
    gui.logger.info("  rmv_source bgsu         Set source to BGSU API (3000+ structures)")
    gui.logger.info("  rmv_fetch 1S72          Load raw PDB structure (no rendering)")
    gui.logger.info("  rmv_summary             Show motif summary for loaded PDB")
    gui.logger.info("  rmv_show HL             Highlight and render hairpin loops")
    gui.logger.info("  rmv_instance HL 1       View specific instance")
    gui.logger.info("")
    gui.logger.info("  rmv_help                Show all commands")
    gui.logger.info("  rmv_sources             Show available data sources")
    gui.logger.info("")
