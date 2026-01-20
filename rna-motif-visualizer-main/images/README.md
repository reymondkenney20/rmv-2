# Documentation Images

Screenshots for RNA Motif Visualizer v2.1.0 documentation.

## Current Images
- `1.png`, `2.png`, `3.png` - Existing screenshots

---

## Required Images for README.md

| Filename | Description | How to Create |
|----------|-------------|---------------|
| `banner.png` | Main plugin banner | Load structure, show motifs, screenshot |
| `installation_steps.png` | Plugin Manager settings | Plugin → Plugin Manager → Settings tab |

---

## Required Images for TUTORIAL.md

| Filename | Description | Commands to Run |
|----------|-------------|-----------------|
| `rna_help.png` | Command reference | `rna_help` |
| `rna_sources.png` | Data sources view | `rna_sources` |
| `rna_load.png` | Loaded structure | `rna_load 1S72` |
| `rna_show.png` | Highlighted motifs | `rna_show HL` |
| `rna_instance.png` | Single instance | `rna_instance HL 1` |
| `rna_color.png` | Custom colors | `rna_color HL blue` |

---

## How to Create Screenshots

### Console Screenshots
1. Run the command in PyMOL
2. Select the console output text
3. Screenshot with `Cmd + Shift + 4` (macOS)

### Structure Screenshots
```python
# Setup
bg_color white
set ray_shadows, 0

# Load and visualize
rna_load 1S72
rna_show HL

# High quality screenshot
ray 1200, 1200
png screenshot.png
```

### PyMOL Screenshot Command
```python
png filename.png, dpi=150
```

---

## Image Dimensions

| Type | Recommended Size |
|------|------------------|
| Banner | 1200 x 400 px |
| Console | 800 x 600 px |
| Structure | 1200 x 1200 px |
