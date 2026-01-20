"""
RNA Motif Visualizer - Main Plugin Module
PyMOL plugin for visualizing RNA structural motifs with multi-database support.

Version: 2.0.0 
Author: CBB Lab by Dr.Zhong
License: MIT

This module is the entry point when the plugin is loaded into PyMOL.
Supports multiple motif databases:
- RNA 3D Motif Atlas (JSON format)
- Rfam Motif Database (Stockholm format)
- Extensible to future databases and API sources

Usage in PyMOL:
    rmv_load <PDB_ID>                    # Load with default database
    rmv_load <PDB_ID>, database=atlas    # Load with RNA 3D Atlas
    rmv_load <PDB_ID>, database=rfam     # Load with Rfam database
    rmv_switch <database_id>             # Switch active database
    rmv_databases                        # List available databases
    rmv_status                           # Show current status
"""

from pymol import cmd
from pathlib import Path
from .gui import initialize_gui
from .utils import initialize_logger
from .database import initialize_registry, get_registry
from datetime import datetime


def __init_plugin__(app):
    """
    Initialize plugin in PyMOL with multi-database support.
    
    This function is called by PyMOL when the plugin is first loaded.
    
    Initialization steps:
    1. Setup logging
    2. Initialize database registry with all available providers
    3. Register GUI commands
    4. Print welcome message with usage instructions
    
    Args:
        app: PyMOL application instance
    """
    # Initialize logger
    plugin_dir = Path(__file__).parent
    logger = initialize_logger(use_pymol_console=True)
    
    # Initialize database registry with all available providers
    try:
        database_dir = plugin_dir / 'motif_database'
        logger.debug(f"Initializing database registry from {database_dir}")
        
        # Initialize registry - this registers all available providers
        registry = initialize_registry(str(database_dir))
        
        # Get summary of registered databases
        providers = registry.get_all_providers()
        total_pdbs = sum(len(p.get_available_pdb_ids()) for p in providers.values())
        total_motif_types = sum(len(p.get_available_motif_types()) for p in providers.values())
        
        logger.success(f"Loaded {len(providers)} database(s)")
        for pid, provider in providers.items():
            logger.debug(f"  {pid}: {provider.info.name} - "
                        f"{len(provider.get_available_motif_types())} motif types, "
                        f"{len(provider.get_available_pdb_ids())} PDB structures")
        
    except Exception as e:
        logger.error(f"Error initializing database registry: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize GUI and register commands
    initialize_gui()
    
    # Print professional welcome message
    last_updated = "January 19, 2025"
    print("\n" + "="*80)
    print("┌" + " "*78 + "┐")
    print("│" + " "*20 + "🧬 RNA MOTIF VISUALIZER 🧬" + " "*32 + "│")
    print("│" + " "*78 + "│")
    print("│" + " Version 2.1.0" + " "*63 + "│")
    print("│" + " Last Updated: " + last_updated + " "*44 + "│")
    print("│" + " "*78 + "│")
    print("│" + " Multi-source RNA structural motif visualization for PyMOL" + " "*18 + "│")
    print("│" + " Fast loading: Load PDB first, render motifs on demand" + " "*23 + "│")
    print("│" + " "*78 + "│")
    print("└" + " "*78 + "┘")
    print("="*80)
    print("\n📊 AVAILABLE DATA SOURCES:")
    print("   • Local:       RNA 3D Atlas, Rfam (offline)")
    print("   • Online:      BGSU RNA 3D Hub, Rfam API")
    print("   • Annotations: User annotations (FR3D, RNAMotifScan)")
    print("\n⚡ QUICK START:")
    print("   rmv_source web bgsu      # Select online BGSU source")
    print("   rmv_fetch 1S72           # Load PDB structure")
    print("   rmv_summary              # Show available motifs")
    print("   rmv_show HL              # Render hairpin loops")
    print("\n📚 COMMANDS & HELP:")
    print("   rmv_help                 # All available commands")
    print("   rmv_sources              # List all data sources")
    print("   rmv_status               # Current plugin status")
    print("\n" + "="*80 + "\n")


# Module metadata
__all__ = ['__init_plugin__']
