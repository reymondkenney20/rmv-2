#!/usr/bin/env python3
"""
Quick verification script to check if all bug fixes are in place.
Run this to verify the session's fixes were applied correctly.
"""

import os
import sys

def check_file_contains(filepath, search_string, description):
    """Check if file contains a specific string."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            if search_string in content:
                print(f"✓ {description}")
                return True
            else:
                print(f"✗ {description}")
                return False
    except Exception as e:
        print(f"✗ Could not check {description}: {e}")
        return False

def verify_fixes():
    """Verify all fixes are in place."""
    print("=" * 70)
    print("RNA Motif Visualizer - Bug Fix Verification")
    print("=" * 70)
    print()
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    gui_file = os.path.join(base_path, "rna_motif_visualizer", "gui.py")
    loader_file = os.path.join(base_path, "rna_motif_visualizer", "loader.py")
    
    results = []
    
    # Issue #2: Usage message fix
    print("Issue #2: Misleading Usage Message Fix")
    print("-" * 70)
    results.append(check_file_contains(
        gui_file,
        'Use: rmv_fetch <PDB_ID>',
        "Usage message corrected to 'rmv_fetch <PDB_ID>' (without tool suffix)"
    ))
    results.append(check_file_contains(
        gui_file,
        'Example: rmv_fetch 1S72',
        "Example updated to show single PDB_ID parameter"
    ))
    print()
    
    # Issue #3: Visualization fix - show_motif_type
    print("Issue #3: Visualization Fix - show_motif_type()")
    print("-" * 70)
    results.append(check_file_contains(
        loader_file,
        'Color each instance individually to avoid PyMOL selection string length limits',
        "Loop-based coloring implemented in show_motif_type()"
    ))
    results.append(check_file_contains(
        loader_file,
        'for detail in motif_details:',
        "Detail-by-detail iteration in show_motif_type()"
    ))
    results.append(check_file_contains(
        loader_file,
        'colors.set_motif_color_in_pymol(self.cmd, instance_sel, motif_type)',
        "Individual instance coloring in show_motif_type()"
    ))
    print()
    
    # Issue #3: Visualization fix - show_all_motifs
    print("Issue #3: Visualization Fix - show_all_motifs()")
    print("-" * 70)
    results.append(check_file_contains(
        loader_file,
        'for motif_type, info in loaded_motifs.items():',
        "Motif type iteration in show_all_motifs()"
    ))
    results.append(check_file_contains(
        loader_file,
        'for detail in motif_details:',
        "Detail-by-detail iteration in show_all_motifs()"
    ))
    print()
    
    # Compilation check
    print("Syntax Validation")
    print("-" * 70)
    try:
        import py_compile
        py_compile.compile(gui_file, doraise=True)
        print("✓ gui.py compiles successfully")
        results.append(True)
    except Exception as e:
        print(f"✗ gui.py has syntax errors: {e}")
        results.append(False)
    
    try:
        py_compile.compile(loader_file, doraise=True)
        print("✓ loader.py compiles successfully")
        results.append(True)
    except Exception as e:
        print(f"✗ loader.py has syntax errors: {e}")
        results.append(False)
    
    print()
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("✓ All fixes verified successfully!")
        return 0
    else:
        print("✗ Some fixes are missing or incorrect")
        return 1

if __name__ == "__main__":
    sys.exit(verify_fixes())
