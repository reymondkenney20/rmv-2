#!/usr/bin/env python3
"""
Test script for RNA Motif Visualizer API providers.
Tests the new multi-source provider system.
"""

import sys
import tempfile
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test 1: Verify all modules can be imported."""
    print("=" * 60)
    print("TEST 1: Import all modules")
    print("=" * 60)
    
    errors = []
    
    try:
        from rna_motif_visualizer.database.config import PluginConfig, SourceMode, CachePolicy, get_config
        print("✓ config.py imported")
    except Exception as e:
        errors.append(f"config.py: {e}")
        print(f"✗ config.py failed: {e}")

    try:
        from rna_motif_visualizer.database.cache_manager import CacheManager, get_cache_manager
        print("✓ cache_manager.py imported")
    except Exception as e:
        errors.append(f"cache_manager.py: {e}")
        print(f"✗ cache_manager.py failed: {e}")

    try:
        from rna_motif_visualizer.database.source_selector import SourceSelector, get_source_selector
        print("✓ source_selector.py imported")
    except Exception as e:
        errors.append(f"source_selector.py: {e}")
        print(f"✗ source_selector.py failed: {e}")

    try:
        from rna_motif_visualizer.database.bgsu_api_provider import BGSUAPIProvider
        print("✓ bgsu_api_provider.py imported")
    except Exception as e:
        errors.append(f"bgsu_api_provider.py: {e}")
        print(f"✗ bgsu_api_provider.py failed: {e}")

    try:
        from rna_motif_visualizer.database.rfam_api_provider import RfamAPIProvider
        print("✓ rfam_api_provider.py imported")
    except Exception as e:
        errors.append(f"rfam_api_provider.py: {e}")
        print(f"✗ rfam_api_provider.py failed: {e}")

    return len(errors) == 0


def test_config():
    """Test 2: Test configuration module."""
    print("\n" + "=" * 60)
    print("TEST 2: Configuration module")
    print("=" * 60)
    
    from rna_motif_visualizer.database.config import (
        PluginConfig, SourceMode, CachePolicy, get_config
    )
    
    config = get_config()
    print(f"✓ Default source mode: {config.source_mode.value}")
    print(f"✓ Source priority: {config.source_priority}")
    print(f"✓ Cache days: {config.freshness_policy.cache_days}")
    
    # Test source list generation
    config.source_mode = SourceMode.LOCAL
    assert config.get_source_list() == ["atlas", "rfam"], "LOCAL mode should return local sources"
    print(f"✓ LOCAL mode source list: {config.get_source_list()}")
    
    config.source_mode = SourceMode.BGSU
    assert "bgsu_api" in config.get_source_list(), "BGSU mode should include bgsu_api"
    print(f"✓ BGSU mode source list: {config.get_source_list()}")
    
    config.source_mode = SourceMode.AUTO
    print(f"✓ AUTO mode source list: {config.get_source_list()}")
    
    return True


def test_cache_manager():
    """Test 3: Test cache manager."""
    print("\n" + "=" * 60)
    print("TEST 3: Cache manager")
    print("=" * 60)
    
    from rna_motif_visualizer.database.cache_manager import CacheManager
    from rna_motif_visualizer.database.base_provider import MotifInstance, ResidueSpec
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CacheManager(tmpdir, expiry_days=30)
        print(f"✓ Cache manager created: {cm.cache_dir}")
        
        # Create test motif data
        test_residues = [
            ResidueSpec(chain="A", residue_number=100, nucleotide="G"),
            ResidueSpec(chain="A", residue_number=101, nucleotide="A"),
        ]
        test_instance = MotifInstance(
            instance_id="HL_TEST_001",
            motif_id="HL",
            pdb_id="TEST",
            residues=test_residues,
            annotation="Test hairpin loop"
        )
        test_motifs = {"HL": [test_instance]}
        
        # Test caching
        cm.cache_motifs("TEST", "bgsu_api", test_motifs)
        print("✓ Motifs cached successfully")
        
        # Test retrieval
        cached = cm.get_cached_motifs("TEST", "bgsu_api")
        assert cached is not None, "Should retrieve cached motifs"
        assert "HL" in cached, "Should have HL motif type"
        assert len(cached["HL"]) == 1, "Should have 1 instance"
        print(f"✓ Retrieved cached motifs: {len(cached)} type(s)")
        
        # Test non-existent
        missing = cm.get_cached_motifs("NONEXISTENT", "bgsu_api")
        assert missing is None, "Should return None for missing cache"
        print("✓ Returns None for missing cache entries")
        
    return True


def test_providers():
    """Test 4: Test API provider instantiation."""
    print("\n" + "=" * 60)
    print("TEST 4: API providers")
    print("=" * 60)
    
    from rna_motif_visualizer.database.bgsu_api_provider import BGSUAPIProvider
    from rna_motif_visualizer.database.rfam_api_provider import RfamAPIProvider
    
    # Test BGSU provider
    bgsu = BGSUAPIProvider()
    assert bgsu.info.id == "bgsu_api", "BGSU provider ID should be bgsu_api"
    assert bgsu.initialize() == True, "BGSU should initialize successfully"
    print(f"✓ BGSU Provider: {bgsu.info.name}")
    print(f"  Motif types: {bgsu.get_available_motif_types()}")
    
    # Test Rfam provider
    rfam = RfamAPIProvider()
    assert rfam.info.id == "rfam_api", "Rfam provider ID should be rfam_api"
    assert rfam.initialize() == True, "Rfam should initialize successfully"
    print(f"✓ Rfam Provider: {rfam.info.name}")
    print(f"  Motif types: {rfam.get_available_motif_types()}")
    
    return True


def test_bgsu_api():
    """Test 5: Test BGSU API with real request."""
    print("\n" + "=" * 60)
    print("TEST 5: BGSU API live request")
    print("=" * 60)
    
    from rna_motif_visualizer.database.bgsu_api_provider import BGSUAPIProvider
    
    bgsu = BGSUAPIProvider()
    
    # Test with a small RNA structure
    pdb_id = "1C0A"
    print(f"Fetching motifs for {pdb_id}...")
    
    try:
        motifs = bgsu.get_motifs_for_pdb(pdb_id)
        
        if motifs:
            print(f"✓ Found {len(motifs)} motif type(s):")
            for motif_type, instances in motifs.items():
                print(f"  {motif_type}: {len(instances)} instance(s)")
                if instances:
                    first = instances[0]
                    print(f"    First: {first.instance_id} ({len(first.residues)} residues)")
        else:
            print(f"ℹ No motifs found for {pdb_id} (may not be in RNA 3D Hub)")
        
        return True
        
    except Exception as e:
        print(f"✗ API request failed: {e}")
        print("  (This may be due to network issues)")
        return False


def test_source_selector():
    """Test 6: Test source selector."""
    print("\n" + "=" * 60)
    print("TEST 6: Source selector")
    print("=" * 60)
    
    from rna_motif_visualizer.database.source_selector import SourceSelector
    from rna_motif_visualizer.database.bgsu_api_provider import BGSUAPIProvider
    from rna_motif_visualizer.database.cache_manager import CacheManager
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CacheManager(tmpdir)
        bgsu = BGSUAPIProvider(cache_manager=cm)
        
        providers = {"bgsu_api": bgsu}
        selector = SourceSelector(providers, cm)
        
        print(f"✓ Source selector created with {len(providers)} provider(s)")
        print(f"  Available sources: {selector.get_available_sources()}")
        
        # Test source info
        info = selector.get_source_info()
        print(f"  Source info: {info}")
        
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("RNA MOTIF VISUALIZER - API PROVIDER TESTS")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Config", test_config()))
    results.append(("Cache Manager", test_cache_manager()))
    results.append(("Providers", test_providers()))
    results.append(("Source Selector", test_source_selector()))
    
    # API test is optional (requires network)
    try:
        results.append(("BGSU API Live", test_bgsu_api()))
    except Exception as e:
        print(f"\n⚠ BGSU API test skipped: {e}")
        results.append(("BGSU API Live", None))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for name, result in results:
        if result is True:
            print(f"  ✓ {name}: PASSED")
            passed += 1
        elif result is False:
            print(f"  ✗ {name}: FAILED")
            failed += 1
        else:
            print(f"  ⚠ {name}: SKIPPED")
            skipped += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
