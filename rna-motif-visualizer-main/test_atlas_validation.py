#!/usr/bin/env python
"""
Test script to validate the scalable RNA 3D Motif Atlas implementation.
Runs without PyMOL to verify registry loading, indexing, and PDB lookups.
"""

import json
import sys
from pathlib import Path

# Add the repo root to sys.path so we can import the package
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

plugin_path = repo_root / "rna_motif_visualizer"

def test_motif_registry():
    """Test that motif registry loads correctly"""
    print("="*70)
    print("TEST 1: Loading Motif Registry")
    print("="*70)
    
    registry_file = plugin_path / "motif_database" / "motif_registry.json"
    
    if not registry_file.exists():
        print("ERROR: motif_registry.json not found")
        return False
    
    try:
        with open(registry_file, 'r') as f:
            registry = json.load(f)
        
        atlas_count = len(registry.get("motif_files", {}))
        
        print(f"✓ Registry loaded successfully")
        print(f"  - Atlas motif types: {atlas_count}")
        
        # List all motif types
        print("\n  Atlas motifs:")
        for motif_type in registry.get("motif_files", {}):
            print(f"    - {motif_type}")
        
        return True
        
    except Exception as e:
        print(f"ERROR loading registry: {e}")
        return False


def test_atlas_loader():
    """Test that Atlas loader initializes and builds index"""
    print("\n" + "="*70)
    print("TEST 2: Initializing Atlas Loader")
    print("="*70)
    
    try:
        from rna_motif_visualizer.atlas_loader import AtlasMotifLoader
        
        database_dir = plugin_path / "motif_database"
        loader = AtlasMotifLoader(str(database_dir))
        
        print(f"✓ AtlasMotifLoader initialized")
        print(f"  Database directory: {database_dir}")
        
        # Build the PDB index
        print("\n  Building PDB index... (indexing all motif files)")
        loader.build_pdb_index()

        # Show resolved motif files (supports drop-in Atlas upgrades)
        resolved = getattr(loader, "_resolved_motif_files", {}) or {}
        if resolved:
            print("\n  Resolved Atlas motif files:")
            for motif_type in sorted(resolved.keys()):
                print(f"    - {motif_type}: {resolved[motif_type].name}")
        
        pdb_count = len(loader.pdb_index)
        print(f"✓ PDB index built successfully")
        print(f"  - PDB structures indexed: {pdb_count}")
        
        if pdb_count == 0:
            print("  ⚠️  WARNING: No PDB structures found in index")
            return False
        
        # Show some sample PDB IDs
        sample_pdbs = sorted(list(loader.pdb_index.keys()))[:10]
        print(f"\n  Sample PDB IDs (showing first 10):")
        for pdb_id in sample_pdbs:
            motif_count = len(loader.pdb_index[pdb_id])
            print(f"    - {pdb_id}: {motif_count} motifs")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR initializing Atlas loader: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pdb_lookup():
    """Test PDB motif lookup for specific structures"""
    print("\n" + "="*70)
    print("TEST 3: PDB Motif Lookup")
    print("="*70)
    
    try:
        from rna_motif_visualizer.atlas_loader import AtlasMotifLoader
        
        database_dir = plugin_path / "motif_database"
        loader = AtlasMotifLoader(str(database_dir))
        loader.build_pdb_index()
        
        # Get a sample PDB ID from the index
        sample_pdbs = sorted(list(loader.pdb_index.keys()))
        
        if not sample_pdbs:
            print("❌ No PDB structures in index")
            return False
        
        # Test lookup for first few PDB IDs
        test_count = min(3, len(sample_pdbs))
        
        for pdb_id in sample_pdbs[:test_count]:
            motifs = loader.get_motifs_for_pdb(pdb_id)
            
            if not motifs:
                print(f"⚠️  {pdb_id}: No motifs found (may be in index but no data)")
                continue
            
            # Group by type
            by_type = {}
            for m in motifs:
                mtype = m.get('motif_type')
                if mtype not in by_type:
                    by_type[mtype] = 0
                by_type[mtype] += 1
            
            print(f"\n✓ {pdb_id}:")
            print(f"  Total motifs: {len(motifs)}")
            print(f"  Motif types:")
            for mtype, count in sorted(by_type.items()):
                print(f"    - {mtype}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR in PDB lookup test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pdb_mapper():
    """Test the PDB mapper wrapper"""
    print("\n" + "="*70)
    print("TEST 4: PDB Motif Mapper")
    print("="*70)
    
    try:
        from rna_motif_visualizer.pdb_motif_mapper import PDBMotifMapper
        
        mapper = PDBMotifMapper()
        
        print(f"✓ PDBMotifMapper initialized")
        
        # Get all available PDBs
        all_pdbs = mapper.loader.get_available_pdb_structures()
        print(f"✓ Total PDB structures in database: {len(all_pdbs)}")
        
        # Test search by motif type
        if all_pdbs:
            # Find a PDB with lots of motifs
            test_pdb = sorted(all_pdbs, 
                            key=lambda p: len(mapper.loader.pdb_index.get(p, [])),
                            reverse=True)[0]
            
            motif_count = mapper.count_motifs(test_pdb)
            summary = mapper.get_summary(test_pdb)
            
            print(f"\n✓ Testing with {test_pdb}:")
            print(f"  {motif_count} total motifs")
            print(f"\n{summary}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR in PDB mapper test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "RNA MOTIF ATLAS - VALIDATION TEST" + " "*20 + "║")
    print("╚" + "="*68 + "╝")
    
    tests = [
        ("Registry", test_motif_registry),
        ("Atlas Loader", test_atlas_loader),
        ("PDB Lookup", test_pdb_lookup),
        ("PDB Mapper", test_pdb_mapper),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ FATAL ERROR in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status:10s} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Scalable database is ready.")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
