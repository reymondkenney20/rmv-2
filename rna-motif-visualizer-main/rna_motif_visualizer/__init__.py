"""RNA Motif Visualizer

PyMOL plugin for visualizing RNA structural motifs.

This package provides:
- Automatic loading of RNA structures from RCSB or local files
- JSON-based motif database system
- PyMOL visualization of K-turns, A-minors, GNRA tetraloops, and more
- Intuitive GUI for toggling motif visibility
- Fast, lightweight, and requires no external tools

Author: CBB Lab
Version: 2.0.0
"""

# NOTE:
# Keep this package importable outside PyMOL.
# PyMOL injects/provides the `pymol` module at runtime; importing it in a
# regular Python interpreter (e.g., during CLI tests) will fail.

__version__ = '2.0.0'
__author__ = 'CBB Lab'


def __getattr__(name):
    """Lazy imports so non-PyMOL environments can import this package."""
    if name == '__init_plugin__':
        from .plugin import __init_plugin__ as value
        return value
    if name in {'get_gui', 'initialize_gui'}:
        from . import gui as _gui
        return getattr(_gui, name)
    if name == 'VisualizationManager':
        from .loader import VisualizationManager as value
        return value
    raise AttributeError(name)


__all__ = ['__init_plugin__', 'get_gui', 'initialize_gui', 'VisualizationManager']
