# RNA Motif Visualizer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyMOL](https://img.shields.io/badge/PyMOL-Plugin-blue.svg)](https://pymol.org/)
[![Version](https://img.shields.io/badge/Version-2.1.0-green.svg)](#)

A PyMOL plugin for visualizing RNA structural motifs. Automatically detects and highlights RNA motifs like hairpin loops, internal loops, junctions, GNRA tetraloops, kink-turns, and more directly on your RNA structure.

**🚀 Supports 3000+ PDB structures + User Annotations (FR3D, RNAMotifScan)!**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔬 **Multi-Source Data** | Local database + BGSU API + Rfam API + User Annotations |
| 🎨 **Automatic Coloring** | Each motif type gets distinct colors |
| 📊 **Instance Explorer** | View individual motif instances with details |
| 💡 **Smart Suggestions** | Contextual help after each command |
| 💾 **Intelligent Caching** | API responses cached for 30 days |
| 🎯 **Custom Colors** | Change motif colors at runtime |
| 👤 **User Annotations** | Load FR3D or RNAMotifScan analysis results |

---

## 📦 Installation

### Step 1: Download the Plugin

```bash
git clone https://github.com/Rakib-Hasan-Rahad/rna-motif-visualizer.git
```

### Step 2: Install in PyMOL

1. Open **PyMOL**
2. Go to **Plugin** → **Plugin Manager**
3. Click the **Settings** tab
4. Click **Add new directory**
5. Select the `rna_motif_visualizer` folder
6. Click **OK** and **Restart PyMOL**

---

## 🚀 Quick Start

### Quick Example 1: Local Database

```
rmv_source local
rmv_fetch 1S72
rmv_summary
rmv_show HL
```

### Quick Example 2: Use BGSU Online API

```
rmv_source web bgsu
rmv_fetch 1S72
rmv_summary
```

### Quick Example 3: Load User Annotations

```
rmv_source user fr3d
rmv_fetch 1S72
rmv_summary
rmv_show HAIRPIN
```

---

## 📖 Complete Command Reference

### 🔌 Source Selection Commands

The plugin uses a two-level source hierarchy for intuitive source selection.

#### Local Sources (Offline)

| Command | Description |
|---------|-------------|
| `rmv_source local` | Use local bundled databases (Atlas + Rfam) |
| `rmv_source local atlas` | Use only RNA 3D Motif Atlas |
| `rmv_source local rfam` | Use only Rfam database |

#### Online Sources (Requires Internet)

| Command | Description |
|---------|-------------|
| `rmv_source web` | Auto-select best online API (BGSU/Rfam) |
| `rmv_source web bgsu` | Use BGSU RNA 3D Hub API (~3000+ PDBs) |
| `rmv_source web rfam` | Use Rfam API (named motifs) |

#### Combined Sources

| Command | Description |
|---------|-------------|
| `rmv_source auto` | Auto-select (local first, then API) [DEFAULT] |
| `rmv_source all` | Combine all available sources |

#### User Annotations

| Command | Description |
|---------|-------------|
| `rmv_source user fr3d` | Load FR3D analysis output |
| `rmv_source user rnamotifscan` | Load RNAMotifScan analysis output |

#### Status & Info

| Command | Description |
|---------|-------------|
| `rmv_source` | Show current source config & status |
| `rmv_sources` | List all available sources (quick reference) |

---

### 📥 Loading Commands

| Command | Description | Example |
|---------|-------------|---------|
| `rmv_fetch <PDB_ID>` | Load raw PDB structure (fast) | `rmv_fetch 1S72` |
| `rmv_load <PDB_ID>` | Load structure & auto-visualize motifs | `rmv_load 4V9F` |
| `rmv_refresh [PDB_ID]` | Force refresh from API (bypass cache) | `rmv_refresh` |

---

### 🎨 Visualization Commands

| Command | Description | Example |
|---------|-------------|---------|
| `rmv_all` | Show all motifs (reset view) | `rmv_all` |
| `rmv_show <TYPE>` | Highlight specific motif type | `rmv_show HL` |
| `rmv_show <TYPE> <NO>` | Show & zoom to specific instance | `rmv_show HL 1` |
| `rmv_instance <TYPE> <NO>` | View instance details & zoom | `rmv_instance GNRA 5` |
| `rmv_toggle <TYPE> on/off` | Toggle motif visibility | `rmv_toggle IL on` |
| `rmv_bg_color <COLOR>` | Change background (non-motif) color | `rmv_bg_color white` |
| `rmv_color <TYPE> <COLOR>` | Change motif color | `rmv_color HL blue` |
| `rmv_colors` | Show color legend | `rmv_colors` |

---

### 📊 Information Commands

| Command | Description | Example |
|---------|-------------|---------|
| `rmv_summary` | Show all motif types & counts | `rmv_summary` |
| `rmv_summary <TYPE>` | Show instances of specific type | `rmv_summary HL` |
| `rmv_summary <TYPE> <NO>` | Show specific instance details | `rmv_summary HL 1` |
| `rmv_status` | Show plugin status & configuration | `rmv_status` |
| `rmv_help` | Show command reference | `rmv_help` |

---

## 🔄 Data Source Hierarchy

### Source Selection Strategy

The plugin supports three levels of source selection:

#### Level 1: Category (local/web/auto/all/user)
- `rmv_source local` - Use local databases
- `rmv_source web` - Use online APIs
- `rmv_source auto` - Smart auto-select
- `rmv_source all` - Combine all
- `rmv_source user` - User annotations

#### Level 2: Specific Source (optional)
- `rmv_source local atlas` - Specify local source
- `rmv_source local rfam` - Specify local source
- `rmv_source web bgsu` - Specify online source
- `rmv_source web rfam` - Specify online source
- `rmv_source user fr3d` - Specify annotation tool

#### Available Sources

| Source | Type | Coverage | Connection |
|--------|------|----------|-----------|
| Local Atlas | Local | 759 PDB structures, ~37 motif types | Offline |
| Local Rfam | Local | Named motifs (GNRA, UNCG, etc.) | Offline |
| BGSU API | Online | ~3000+ RNA structures | Internet required |
| Rfam API | Online | All Rfam-annotated PDBs | Internet required |
| FR3D Annotations | User | Custom analysis results | Custom file |
| RNAMotifScan | User | Custom analysis results | Custom file |

---

## 📋 Available Motif Types

### Local/BGSU Sources

| Type | Category | Description |
|------|----------|-------------|
| HL | Basic | Hairpin Loops |
| IL | Basic | Internal Loops |
| J3 | Junctions | 3-way Junction |
| J4 | Junctions | 4-way Junction |
| J5 | Junctions | 5-way Junction |
| J6 | Junctions | 6-way Junction |
| J7 | Junctions | 7-way Junction |
| GNRA | Tetraloop | GNRA Tetraloop (Rfam) |
| UNCG | Tetraloop | UNCG Tetraloop (Rfam) |

### User Annotations (FR3D, RNAMotifScan)

Depends on the analysis performed. Common types include:
- HAIRPIN, BULGE, INTERNAL_LOOP, HELIX, STEM, JUNCTION, etc.

---

## 🎨 Color Customization

### Change Motif Colors

```
rmv_color HL blue              # Change hairpin loops to blue
rmv_color GNRA red             # Change GNRA tetraloops to red
rmv_color IL yellow            # Change internal loops to yellow
rmv_colors                      # Show current color scheme
```

### Available Colors

red, green, blue, yellow, cyan, magenta, orange, purple, pink, white, gray, lime, teal, salmon

---

## 💾 Caching & Performance

API responses are cached locally:

| Setting | Value |
|---------|-------|
| **Cache Location** | `~/.rna_motif_visualizer_cache/` |
| **Duration** | 30 days |
| **Refresh** | Use `rmv_refresh` command |

---

## 🎯 Complete Workflow Examples

### Example 1: Explore Ribosome Structure

```
# Set source
rmv_source web bgsu

# Load structure
rmv_fetch 1S72

# See what motifs are available
rmv_summary

# View all hairpin loops
rmv_show HL

# Zoom to first hairpin loop
rmv_instance HL 1

# Change hairpin color
rmv_color HL cyan

# Show all motifs again
rmv_all
```

### Example 2: FR3D User Annotations

```
# Select FR3D annotations
rmv_source user fr3d

# Load structure
rmv_fetch 1S72

# See detected motifs
rmv_summary

# View hairpins from analysis
rmv_show HAIRPIN

# Color the motifs
rmv_color HAIRPIN red
```

### Example 3: Compare Local vs Online

```
# First, try local database
rmv_source local
rmv_fetch 1S72
rmv_summary

# Then switch to online
rmv_source web bgsu
rmv_fetch 1S72
rmv_summary

# Combine all sources
rmv_source all
rmv_fetch 1S72
rmv_summary
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Plugin not appearing | Restart PyMOL, verify path in Plugin Manager |
| "No motifs found" | Try: `rmv_source all` or use different source |
| API errors | Check internet connection; try: `rmv_source local` |
| Slow first load | API calls cached; subsequent loads are fast |
| Structure won't load | Make sure PDB ID is valid (e.g., `1S72`) |

---

## 📂 Project Structure

```
rna-motif-visualizer/
├── rna_motif_visualizer/
│   ├── plugin.py              # Plugin entry point
│   ├── gui.py                 # PyMOL commands (rmv_*)
│   ├── loader.py              # Visualization logic
│   ├── colors.py              # Color definitions
│   ├── database/              # Data providers
│   ├── motif_database/        # Local motif data
│   └── utils/                 # Utilities
├── README.md                  # This file
├── TUTORIAL.md                # Detailed tutorial
├── DEVELOPER.md               # Architecture & contribution
└── LICENSE                    # MIT License
```

---

## 📚 Further Reading

- **[TUTORIAL.md](TUTORIAL.md)** - Detailed step-by-step tutorial with all workflows
- **[DEVELOPER.md](DEVELOPER.md)** - Architecture and contribution guide

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

## 🙏 Credits

- **RNA 3D Motif Atlas** - BGSU RNA Group
- **Rfam Database** - EMBL-EBI
- **PyMOL** - Schrödinger, LLC

---

<p align="center">
  <b>Happy RNA Visualization! 🧬</b>
</p>

