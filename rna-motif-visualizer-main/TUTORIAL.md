# RNA Motif Visualizer - Tutorial

Complete step-by-step guide to using the RNA Motif Visualizer plugin in PyMOL.

---

## 📚 Table of Contents

1. [Getting Started](#1-getting-started)
2. [Data Sources](#2-data-sources)
3. [Loading Structures](#3-loading-structures)
4. [Viewing Motif Summary](#4-viewing-motif-summary)
5. [Exploring Motifs](#5-exploring-motifs)
6. [Instance Navigation](#6-instance-navigation)
7. [Customizing Colors](#7-customizing-colors)
8. [User Annotations](#8-user-annotations)
9. [Common Workflows](#9-common-workflows)
10. [Command Reference](#10-command-reference)

---

## 1. Getting Started

### Verify Installation

After installing and restarting PyMOL, you should see a welcome message.

### View All Commands

```
rmv_help
```

Displays complete command reference organized by category:
- 🔌 Source Selection (8 commands)
- 📥 Loading (4 commands)
- 🎨 Visualization (8 commands)
- 📊 Information (5 commands)

---

## 2. Data Sources

### Check All Available Sources

```
rmv_sources
```

Shows **LOCAL** sources (offline, bundled) and **ONLINE** sources (API-based):
- **Atlas**: 759 PDBs locally
- **Rfam**: 173 PDBs locally  
- **BGSU API**: ~3000+ structures online
- **Rfam API**: All Rfam-annotated PDBs online
- **User Annotations**: FR3D and RNAMotifScan formats

### Check Current Source Configuration

```
rmv_source
```

Shows current mode and active tool (if using user annotations).

### Set Source Mode

#### Using Local Databases (Offline)

```
rmv_source local       # Use both local Atlas and Rfam
rmv_source local atlas # Use only RNA 3D Motif Atlas
rmv_source local rfam  # Use only Rfam database
```

#### Using Online APIs (Requires Internet)

```
rmv_source web         # Auto-select best online API
rmv_source web bgsu    # Use BGSU RNA 3D Hub API (~3000+ structures)
rmv_source web rfam    # Use Rfam API (named motifs)
```

#### Using Combined/Auto Modes

```
rmv_source auto        # Smart selection (default) - tries local first, then APIs
rmv_source all         # Combine all sources for comprehensive results
```

#### Using User Annotations

```
rmv_source user fr3d           # Load FR3D analysis output
rmv_source user rnamotifscan   # Load RNAMotifScan analysis output
```

---

## 3. Loading Structures

### Method 1: Fast Load (Data Only)

Use `rmv_fetch` for quick structure loading without automatic visualization:

```
rmv_fetch 1S72
```

This loads the PDB structure and fetches motif data without rendering objects.

### Method 2: Full Load (with Visualization)

Use `rmv_load` to load and automatically visualize all motifs:

```
rmv_load 1S72
```

The plugin will:
1. Download structure from RCSB PDB
2. Detect all motifs from selected source
3. Display them with different colors
4. Print summary with next steps

### Load with Specific Background Color

```
rmv_fetch 1S72 white
rmv_load 1S72 gray80
```

### Force Refresh from API

```
rmv_refresh        # Refresh currently loaded PDB
rmv_refresh 4V9F   # Refresh specific PDB (bypass cache)
```

### Switch Database

```
rmv_switch atlas   # Switch to Atlas database
rmv_switch rfam    # Switch to Rfam database
```

---

## 4. Viewing Motif Summary

### Show Summary of All Motifs

```
rmv_summary
```

Output:
```
==================================================
  MOTIF SUMMARY - 1S72
==================================================
  Database: RNA 3D Motif Atlas
--------------------------------------------------
  MOTIF TYPE              INSTANCES
--------------------------------------------------
  HL                            45
  IL                            32
  J3                             8
  J4                             2
--------------------------------------------------
  TOTAL                         87
==================================================
```

### Show Instances of Specific Motif Type

```
rmv_summary HL         # Show all HL instances
rmv_summary GNRA       # Show all GNRA instances
```

### Show Specific Instance Details

```
rmv_summary HL 1       # Details of HL instance #1
rmv_summary GNRA 5     # Details of GNRA instance #5
```

---

## 5. Exploring Motifs

### Show Specific Motif Type

```
rmv_show HL            # Highlight all hairpin loops
rmv_show IL            # Highlight all internal loops
rmv_show GNRA          # Highlight all GNRA tetraloops
```

Output displays instance table with chain and residue information.

### Show Specific Instance with Zoom

```
rmv_show HL 1          # Show & zoom to HL instance #1
rmv_show GNRA 5        # Show & zoom to GNRA instance #5
```

### Show All Motifs

```
rmv_all
```

Resets view to show all motif types with equal visibility.

### Toggle Motif Visibility

```
rmv_toggle HL on       # Show hairpin loops
rmv_toggle HL off      # Hide hairpin loops
rmv_toggle IL on       # Show internal loops
```

---

## 6. Instance Navigation

### View Single Instance with Details

```
rmv_instance HL 1
```

Output:
```
==================================================
  HL INSTANCE #1
==================================================
  Instance ID: 1S72_001
  Annotation: Hairpin loop in rRNA
  Residues: 4
--------------------------------------------------
  CHAIN    RESI     NUCLEOTIDE  
--------------------------------------------------
  1        100      G           
  1        101      A           
  1        102      A           
  1        103      A           
==================================================
  Object: HL_1
==================================================
```

Camera zooms to the instance location.

### Navigate Between Instances

```
rmv_instance HL 1      # View first instance
rmv_instance HL 2      # View second instance
rmv_instance HL 3      # View third instance
```

### Switch Between Motif Types

```
rmv_instance IL 1      # View first IL instance
rmv_instance GNRA 1    # View first GNRA instance
```

---

## 7. Customizing Colors

### View Current Color Scheme

```
rmv_colors
```

Shows all motif types with their current colors.

### Change Motif Type Color

```
rmv_color HL blue              # Hairpin loops → blue
rmv_color IL red               # Internal loops → red
rmv_color GNRA forest          # GNRA → forest green
rmv_color J3 yellow            # J3 junctions → yellow
```

### Available Colors

**Basic**: red, green, blue, yellow, cyan, magenta  
**Extended**: orange, purple, pink, white, gray, lime, teal, salmon, forest, marine, slate

### Change Background Color

```
rmv_bg_color white             # White background
rmv_bg_color gray80            # Gray background
rmv_bg_color black             # Black background
rmv_bg_color lightgray         # Light gray
```

---

## 8. User Annotations

Load analysis results from FR3D or RNAMotifScan.

### Select User Annotations Source

```
rmv_source user fr3d           # Use FR3D annotations
rmv_source user rnamotifscan   # Use RNAMotifScan annotations
```

After selecting, you can see the active tool:
```
rmv_source                     # Shows "User Annotations Tool: fr3d"
```

### Load with User Annotations

```
rmv_source user fr3d
rmv_fetch 1S72
rmv_summary                    # Shows FR3D motifs (HAIRPIN, BULGE, etc.)
```

### Explore User Annotation Motifs

```
rmv_show HAIRPIN               # Show hairpin motifs
rmv_show BULGE                 # Show bulge motifs
rmv_show HELIX                 # Show helix motifs
rmv_instance HAIRPIN 1         # View specific instance
rmv_color HAIRPIN red          # Customize color
```

### Switch Back to Standard Sources

```
rmv_source auto                # Return to auto-selection
rmv_fetch 1S72
```

---

## 9. Common Workflows

### Workflow 1: Quick Structure Analysis

```
rmv_fetch 1S72         # Load structure
rmv_summary            # See motif types
rmv_show HL            # Focus on one type
rmv_all                # Reset view
```

### Workflow 2: Detailed Motif Inspection

```
rmv_load 1S72
rmv_show GNRA          # Focus on GNRA tetraloops
rmv_instance GNRA 1    # Examine first GNRA
rmv_instance GNRA 2    # Next GNRA
rmv_instance GNRA 3    # Another GNRA
rmv_all                # Back to full view
```

### Workflow 3: Compare Data Sources

```
rmv_source local
rmv_fetch 1S72
rmv_summary            # Count from local database

rmv_source bgsu
rmv_fetch 1S72
rmv_summary            # Count from BGSU API

rmv_source all
rmv_fetch 1S72
rmv_summary            # Combined results
```

### Workflow 4: User Annotation Analysis

```
rmv_source user fr3d
rmv_fetch 1S72
rmv_summary            # Show FR3D motifs
rmv_show HAIRPIN       # View hairpins
rmv_color HAIRPIN red  # Customize
rmv_instance HAIRPIN 1 # Inspect each one
```

### Workflow 5: Publication Figure

```
rmv_fetch 1S72
rmv_show GNRA          # Focus on specific motif
rmv_instance GNRA 1    # Zoom to instance
rmv_color GNRA red     # Custom color
rmv_bg_color white     # White background
ray 2400, 2400         # High resolution
png "gnra_tetraloop.png"
```

---

## 10. Command Reference

### 🔌 Source Selection Commands (Two-Level Hierarchy)

#### Local Sources (Offline)
| Command | Purpose | Example |
|---------|---------|---------|
| `rmv_source local` | Use all local databases | `rmv_source local` |
| `rmv_source local atlas` | Use only RNA 3D Motif Atlas | `rmv_source local atlas` |
| `rmv_source local rfam` | Use only Rfam database | `rmv_source local rfam` |

#### Online Sources (Requires Internet)
| Command | Purpose | Example |
|---------|---------|---------|
| `rmv_source web` | Auto-select best online API | `rmv_source web` |
| `rmv_source web bgsu` | Use BGSU RNA 3D Hub API | `rmv_source web bgsu` |
| `rmv_source web rfam` | Use Rfam API | `rmv_source web rfam` |

#### Combined/Special Modes
| Command | Purpose | Example |
|---------|---------|---------|
| `rmv_source auto` | Auto-select (local first, then API) | `rmv_source auto` |
| `rmv_source all` | Combine all available sources | `rmv_source all` |
| `rmv_source user fr3d` | Use FR3D annotations | `rmv_source user fr3d` |
| `rmv_source user rnamotifscan` | Use RNAMotifScan annotations | `rmv_source user rnamotifscan` |
| `rmv_source` | Show current config | `rmv_source` |
| `rmv_sources` | List all available sources | `rmv_sources` |

### 📥 Loading Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `rmv_fetch <PDB>` | Load PDB (fast) | `rmv_fetch 1S72` |
| `rmv_load <PDB>` | Load & visualize | `rmv_load 1S72` |
| `rmv_refresh` | Force refresh API | `rmv_refresh` |

### 🎨 Visualization Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `rmv_all` | Show all motifs | `rmv_all` |
| `rmv_show <TYPE>` | Show motif type | `rmv_show HL` |
| `rmv_show <TYPE> <NO>` | Show & zoom | `rmv_show HL 1` |
| `rmv_instance <TYPE> <NO>` | View & zoom | `rmv_instance HL 1` |
| `rmv_toggle <TYPE> on/off` | Toggle visibility | `rmv_toggle IL on` |
| `rmv_bg_color <COLOR>` | Background color | `rmv_bg_color white` |
| `rmv_color <TYPE> <COLOR>` | Motif color | `rmv_color HL blue` |
| `rmv_colors` | Show color legend | `rmv_colors` |

### 📊 Information Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `rmv_summary` | Show all motifs | `rmv_summary` |
| `rmv_summary <TYPE>` | Show type instances | `rmv_summary HL` |
| `rmv_summary <TYPE> <NO>` | Show instance details | `rmv_summary HL 1` |
| `rmv_status` | Show status | `rmv_status` |
| `rmv_help` | Show help | `rmv_help` |

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| Plugin not appearing | Restart PyMOL, check plugin path |
| "No motifs found" | Try `rmv_source all` or different source |
| API errors | Check internet; try `rmv_source local` |
| Slow first load | API calls are cached; future loads are fast |

---

## 📚 Further Reading

- **[README.md](README.md)** - Installation & quick reference
- **[DEVELOPER.md](DEVELOPER.md)** - Architecture & extending
- **rmv_help** - In PyMOL command reference
