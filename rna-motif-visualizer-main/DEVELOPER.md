# Developer Documentation

Technical guide for developers who want to understand, extend, or contribute to the RNA Motif Visualizer plugin.

---

## 📚 Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Project Structure](#2-project-structure)
3. [Core Components](#3-core-components)
4. [Multi-Source Provider System](#4-multi-source-provider-system)
5. [Data Flow](#5-data-flow)
6. [API Providers](#6-api-providers)
7. [Caching System](#7-caching-system)
8. [Adding New Features](#8-adding-new-features)
9. [Testing](#9-testing)
10. [Contributing](#10-contributing)

---

## 1. Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PyMOL Application                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐ │
│  │  plugin.py  │───►│   gui.py    │───►│      loader.py          │ │
│  │  (entry)    │    │ (commands)  │    │  (VisualizationManager) │ │
│  └─────────────┘    └─────────────┘    └───────────┬─────────────┘ │
│                                                     │               │
│                                    ┌────────────────┴────────────┐  │
│                                    │     UnifiedMotifLoader      │  │
│                                    └────────────┬────────────────┘  │
│                                                 │                   │
│  ┌──────────────────────────────────────────────┴───────────────┐  │
│  │                     Source Selector                           │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐  │  │
│  │  │  LOCAL  │  │  BGSU   │  │  RFAM   │  │  CACHE MANAGER  │  │  │
│  │  │Provider │  │  API    │  │  API    │  │                 │  │  │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────────┬────────┘  │  │
│  └───────┼────────────┼───────────┼─────────────────┼───────────┘  │
│          │            │           │                 │               │
└──────────┼────────────┼───────────┼─────────────────┼───────────────┘
           │            │           │                 │
           ▼            ▼           ▼                 ▼
    ┌──────────┐  ┌───────────┐ ┌───────────┐  ┌──────────────┐
    │  Local   │  │   BGSU    │ │   Rfam    │  │    Cache     │
    │ Database │  │    API    │ │    API    │  │   Storage    │
    └──────────┘  └───────────┘ └───────────┘  └──────────────┘
```

### Design Philosophy

1. **Provider Pattern** - All data sources implement a common interface
2. **Smart Fallback** - Automatically tries multiple sources when one fails
3. **Aggressive Caching** - API responses cached for 30 days
4. **Contextual Help** - Guide users with suggestions after each command
5. **Clean Separation** - PyMOL interactions isolated from data logic

---

## 2. Project Structure

```
rna-motif-visualizer/
├── README.md                    # User documentation
├── TUTORIAL.md                  # Step-by-step tutorial
├── DEVELOPER.md                 # This file
├── LICENSE                      # MIT License
├── test_atlas_validation.py     # Testing script
├── images/                      # Documentation images
│
└── rna_motif_visualizer/        # Main plugin package
    │
    ├── __init__.py              # Package marker
    ├── plugin.py                # PyMOL entry point
    ├── gui.py                   # Command registration
    ├── loader.py                # Core visualization logic
    ├── colors.py                # Color definitions
    │
    ├── atlas_loader.py          # Legacy (compatibility)
    ├── pdb_motif_mapper.py      # Legacy (compatibility)
    │
    ├── database/                # Data provider layer
    │   ├── __init__.py          # Package exports
    │   ├── base_provider.py     # Abstract base classes
    │   ├── registry.py          # Provider registry
    │   ├── atlas_provider.py    # Local Atlas provider
    │   ├── rfam_provider.py     # Local Rfam provider
    │   ├── bgsu_api_provider.py # BGSU API provider
    │   ├── rfam_api_provider.py # Rfam API provider
    │   ├── cache_manager.py     # Response caching
    │   ├── config.py            # Configuration
    │   ├── source_selector.py   # Source orchestration
    │   └── converters.py        # Format converters
    │
    ├── motif_database/          # Bundled data files
    │   ├── hl_4.5.json          # Hairpin loops
    │   ├── il_4.5.json          # Internal loops
    │   ├── j3_4.5.json - j7_4.5.json
    │   └── motif_registry.json
    │
    └── utils/                   # Utility modules
        ├── __init__.py
        ├── logger.py            # PyMOL console logging
        ├── parser.py            # PDB ID parsing
        └── selectors.py         # PyMOL selections
```

---

## 3. Core Components

### 3.1 plugin.py - Entry Point

```python
def __init_plugin__(app=None):
    """PyMOL calls this when loading the plugin."""
    # 1. Initialize logger
    # 2. Initialize database registry
    # 3. Register PyMOL commands
    # 4. Print welcome message
```

### 3.2 gui.py - Command Layer

Registers all PyMOL commands:

```python
# Loading & Sources
cmd.extend('rna_load', load_structure_action)
cmd.extend('rna_source', set_source_action)
cmd.extend('rna_sources', print_sources_action)
cmd.extend('rna_switch', switch_db_action)
cmd.extend('rna_refresh', refresh_action)

# Visualization
cmd.extend('rna_all', show_all_action)
cmd.extend('rna_show', show_motif_action)
cmd.extend('rna_instance', show_instance_action)
cmd.extend('rna_toggle', toggle_action)
cmd.extend('rna_bg_color', bg_color_action)
cmd.extend('rna_color', set_motif_color)
cmd.extend('rna_colors', colors_action)

# Information
cmd.extend('rna_summary', summary_action)
cmd.extend('rna_status', status_action)
cmd.extend('rna_help', help_action)
```

### 3.3 loader.py - Visualization Engine

Contains three main classes:

#### VisualizationManager
```python
class VisualizationManager:
    """Orchestrates the entire visualization workflow."""
    
    def load_and_visualize(self, pdb_id: str):
        # 1. Load PDB structure
        # 2. Setup gray RNA cartoon
        # 3. Load motifs from sources
        # 4. Color residues within structure
        # 5. Print summary with suggestions
```

#### UnifiedMotifLoader
```python
class UnifiedMotifLoader:
    """Loads motifs from multiple sources."""
    
    def load_motifs(self, pdb_id: str) -> Dict[str, List]:
        # Uses source_selector to get motifs
        # Merges results from multiple providers
```

#### StructureLoader
```python
class StructureLoader:
    """Handles PDB structure fetching."""
    
    def load_structure(self, pdb_id: str) -> bool:
        # Download and load PDB from RCSB
```

### 3.4 colors.py - Color System

```python
# Default colors
MOTIF_COLORS = {
    'HL': (1.0, 0.4, 0.4),      # Red - Hairpin Loops
    'IL': (1.0, 0.6, 0.2),      # Orange - Internal Loops
    'J3': (1.0, 0.8, 0.2),      # Yellow - 3-way Junctions
    'J4': (0.2, 0.8, 0.2),      # Green - 4-way Junctions
    'GNRA': (0.2, 0.6, 0.2),    # Forest Green - GNRA Tetraloops
    'K-turn': (0.1, 0.4, 0.6),  # Marine Blue - Kink-turns
}

# Custom colors (user overrides)
CUSTOM_COLORS = {}

# Color name to RGB mapping
COLOR_NAMES = {
    'red': (1.0, 0.0, 0.0),
    'green': (0.0, 1.0, 0.0),
    'blue': (0.0, 0.0, 1.0),
    # ... more colors
}

def set_custom_motif_color(motif_type: str, color: str) -> bool:
    """Set a custom color for a motif type."""
    
def get_color(motif_type: str) -> tuple:
    """Get color for motif type (custom first, then default)."""
```

---

## 4. Multi-Source Provider System

### 4.1 Source Modes

```python
class SourceMode(Enum):
    AUTO = "auto"       # Smart selection with fallback
    LOCAL = "local"     # Bundled database only
    BGSU = "bgsu"       # BGSU API only
    RFAM = "rfam"       # Rfam API only
    ALL = "all"         # Combine all sources
```

### 4.2 Source Selector

```python
class SourceSelector:
    """Orchestrates queries across multiple data sources."""
    
    def get_motifs(self, pdb_id: str) -> Dict[str, List]:
        mode = self.config.get_source_mode()
        
        if mode == SourceMode.AUTO:
            return self._auto_fetch(pdb_id)
        elif mode == SourceMode.BGSU:
            return self.bgsu_provider.get_motifs(pdb_id)
        # ... etc
    
    def _auto_fetch(self, pdb_id: str) -> Dict:
        """Try local first, then BGSU, then Rfam."""
        result = self.local_provider.get_motifs(pdb_id)
        if not result:
            result = self.bgsu_provider.get_motifs(pdb_id)
        if not result:
            result = self.rfam_provider.get_motifs(pdb_id)
        return result
```

### 4.3 Base Provider Interface

```python
class BaseProvider(ABC):
    """Abstract base class for all data providers."""
    
    @abstractmethod
    def get_motifs_for_pdb(self, pdb_id: str) -> Dict[str, List]:
        pass
    
    @property
    @abstractmethod
    def info(self) -> DatabaseInfo:
        pass
```

---

## 5. Data Flow

```
1. User: rna_load 1S72
         │
         ▼
2. gui.py: load_structure_action("1S72")
         │
         ▼
3. loader.py: VisualizationManager.load_and_visualize("1S72")
         │
         ├─► Download PDB from RCSB
         ├─► Setup gray cartoon
         └─► UnifiedMotifLoader.load_motifs("1S72")
                   │
                   ▼
4. source_selector.py: get_motifs("1S72")
         │
         ├─► Check cache_manager
         ├─► Query BGSU API / Rfam API
         └─► Store in cache
                   │
                   ▼
5. Color residues within structure
         │
         ▼
6. Print summary + suggestions
```

---

## 6. API Providers

### 6.1 BGSU API Provider

```python
class BGSUAPIProvider:
    BASE_URL = "https://rna.bgsu.edu/rna3dhub/motifs"
    
    def get_motifs_for_pdb(self, pdb_id: str) -> Dict[str, List]:
        # Endpoint: /motifs/release/{version}/nrlist/{pdb_id}
        # Returns: HL, IL, J3-J7 instances
```

**Motif Types**: HL, IL, J3, J4, J5, J6, J7

### 6.2 Rfam API Provider

```python
class RfamAPIProvider:
    BASE_URL = "https://rfam.org"
    
    MOTIF_FAMILIES = {
        'GNRA': 'RF00028',
        'UNCG': 'RF00029',
        'K-turn': 'RF00167',
        'T-loop': 'RF00370',
    }
```

**Motif Types**: GNRA, UNCG, K-turn, T-loop, C-loop, U-turn

---

## 7. Caching System

### Cache Manager

```python
class CacheManager:
    CACHE_DIR = "~/.rna_motif_visualizer_cache"
    EXPIRY_DAYS = 30
    
    def get(self, key: str) -> Optional[dict]:
        """Retrieve if not expired."""
    
    def set(self, key: str, data: dict):
        """Store with timestamp."""
    
    def clear(self):
        """Clear all cached data."""
```

### Cache Structure

```
~/.rna_motif_visualizer_cache/
├── a1b2c3d4e5f6...json    # BGSU response for 1S72
├── f6e5d4c3b2a1...json    # Rfam for 1S72
└── ...
```

---

## 8. Adding New Features

### 8.1 Adding a New Command

1. **Add handler** in `loader.py`:
```python
def my_new_feature(self, arg1):
    # Implementation
    print("\n  Next steps:")
    print("    rna_summary")
```

2. **Register** in `gui.py`:
```python
def my_feature_action(arg1=""):
    manager = get_visualization_manager()
    manager.my_new_feature(arg1)

cmd.extend('rna_myfeature', my_feature_action)
```

### 8.2 Adding a New Motif Type

1. **Add color** in `colors.py`:
```python
MOTIF_COLORS = {
    'NEW_MOTIF': (0.5, 0.5, 0.8),
}
```

2. **Update API provider** to recognize the new type

### 8.3 Adding a New API Provider

1. Create `database/my_api_provider.py`
2. Implement `BaseProvider` interface
3. Register in `source_selector.py`
4. Add source mode if needed

---

## 9. Testing

### Unit Tests

```bash
python3 test_atlas_validation.py
```

### Integration Tests in PyMOL

```python
rna_source local
rna_load 1S72
rna_summary

rna_source bgsu
rna_load 1S72
rna_summary

rna_source all
rna_load 1S72
rna_summary
```

---

## 10. Contributing

### Development Setup

```bash
git clone https://github.com/Rakib-Hasan-Rahad/rna-motif-visualizer.git
cd rna-motif-visualizer

# Link to PyMOL plugins folder (macOS)
ln -s $(pwd)/rna_motif_visualizer ~/Library/Application\ Support/PyMOL/plugins/
```

### Code Style

- Python 3.6+ compatible
- Type hints encouraged
- Docstrings for public methods
- Contextual help for user-facing functions

### Pull Request Checklist

- [ ] Tests pass
- [ ] New features have contextual help
- [ ] Colors added for new motif types
- [ ] Documentation updated

---

## 📖 Quick Reference

### Key Files

| File | Purpose |
|------|---------|
| `loader.py` | Core visualization logic |
| `source_selector.py` | Multi-source orchestration |
| `bgsu_api_provider.py` | BGSU API integration |
| `rfam_api_provider.py` | Rfam API integration |
| `cache_manager.py` | Caching layer |
| `colors.py` | Color definitions |

### Key Classes

| Class | Location | Purpose |
|-------|----------|---------|
| `VisualizationManager` | loader.py | Main orchestrator |
| `SourceSelector` | source_selector.py | Source routing |
| `CacheManager` | cache_manager.py | Caching |
| `BGSUAPIProvider` | bgsu_api_provider.py | BGSU API |
| `RfamAPIProvider` | rfam_api_provider.py | Rfam API |

---

<p align="center">
  <b>Happy Developing! 🛠️</b>
</p>
