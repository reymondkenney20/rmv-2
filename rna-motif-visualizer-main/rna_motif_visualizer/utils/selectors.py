"""
RNA Motif Visualizer - Selection Module
Handles creation and management of PyMOL selections for motifs.
"""

from .parser import SelectionParser, validate_motif_data
from .logger import get_logger


class MotifSelector:
    """Manages PyMOL selections for RNA motifs."""
    
    def __init__(self, cmd):
        """
        Initialize selector.
        
        Args:
            cmd: PyMOL cmd module
        """
        self.cmd = cmd
        self.logger = get_logger()
    
    def create_motif_object(self, structure_name, motif_type, motif_id, chain, residues):
        """
        Create a PyMOL object for a single motif.
        
        Args:
            structure_name (str): Name of the loaded structure
            motif_type (str): Type of motif (e.g., 'KTURN')
            motif_id (str): Unique ID for this motif instance
            chain (str): Chain identifier
            residues (list): List of residue numbers
        
        Returns:
            str: Name of created PyMOL object
        """
        if not validate_motif_data({'chain': chain, 'residues': residues, 'motif_id': motif_id}):
            return None
        
        try:
            # Create object name
            obj_name = f"{motif_type}_{motif_id}_{chain}"
            
            # Create selection
            selection = SelectionParser.create_selection_string(chain, residues)
            if not selection:
                return None
            
            # Create object in PyMOL
            full_selection = f"({structure_name}) and {selection}"
            self.cmd.create(obj_name, full_selection)
            
            return obj_name
        except Exception as e:
            self.logger.error(f"Failed to create motif object: {e}")
            return None
    
    def create_motif_class_object(self, structure_name, motif_type, motif_list):
        """
        Create a combined PyMOL object for all motifs of a type.
        
        Args:
            structure_name (str): Name of the loaded structure
            motif_type (str): Type of motif (e.g., 'KTURN')
            motif_list (list): List of motif dictionaries with keys: chain, residues, motif_id
        
        Returns:
            str: Name of created PyMOL object (e.g., 'KTURN_ALL')
        """
        if not motif_list:
            return None
        
        try:
            obj_name = f"{motif_type}_ALL"
            
            # Collect all selection strings
            selections = []
            for motif in motif_list:
                if not validate_motif_data(motif):
                    self.logger.warning(f"Skipping invalid motif: {motif}")
                    continue
                
                chain = motif.get('chain')
                residues = motif.get('residues')
                
                selection = SelectionParser.create_selection_string(chain, residues)
                if selection:
                    selections.append(selection)
            
            if not selections:
                self.logger.warning(f"No valid selections found for {motif_type}")
                return None
            
            # Combine all selections with OR
            combined_selection = " or ".join([f"({s})" for s in selections])
            full_selection = f"({structure_name}) and ({combined_selection})"
            
            # Create combined object
            self.cmd.create(obj_name, full_selection)
            self.logger.info(f"Created motif object: {obj_name}")
            
            return obj_name
        except Exception as e:
            self.logger.error(f"Failed to create motif class object {motif_type}: {e}")
            return None
    
    def color_motif_residues(self, structure_name, motif_type, motif_list, color_rgb):
        """
        Color residues directly on the structure without creating overlapping objects.
        This avoids z-fighting/striping artifacts.
        
        Args:
            structure_name (str): Name of the loaded structure
            motif_type (str): Type of motif (e.g., 'KTURN')
            motif_list (list): List of motif dictionaries with keys: chain, residues
            color_rgb (tuple): RGB color tuple (0-1 range)
        
        Returns:
            str: Selection name for the colored residues
        """
        if not motif_list:
            return None
        
        try:
            selection_name = f"{motif_type}_sel"
            
            # Collect all selection strings
            selections = []
            for motif in motif_list:
                if not validate_motif_data(motif):
                    continue
                
                chain = motif.get('chain')
                residues = motif.get('residues')
                
                selection = SelectionParser.create_selection_string(chain, residues)
                if selection:
                    selections.append(selection)
            
            if not selections:
                return None
            
            # Combine all selections
            combined_selection = " or ".join([f"({s})" for s in selections])
            full_selection = f"({structure_name}) and ({combined_selection})"
            
            # Create a named selection (not a new object)
            self.cmd.select(selection_name, full_selection)
            
            # Define and apply color
            color_name = f"motif_{motif_type}"
            self.cmd.set_color(color_name, color_rgb)
            self.cmd.color(color_name, selection_name)
            
            # Hide the selection indicator (the pink squares)
            self.cmd.deselect()
            
            self.logger.info(f"Colored {motif_type} residues directly on structure")
            
            return selection_name
        except Exception as e:
            self.logger.error(f"Failed to color motif residues {motif_type}: {e}")
            return None
    
    def toggle_object_visibility(self, obj_name, visible):
        """
        Toggle visibility of a PyMOL object.
        
        Args:
            obj_name (str): Name of object
            visible (bool): True to show, False to hide
        """
        try:
            if visible:
                self.cmd.show('sticks', obj_name)
                self.cmd.show('cartoon', obj_name)
            else:
                self.cmd.hide('everything', obj_name)
            self.logger.debug(f"Set visibility of {obj_name} to {visible}")
        except Exception as e:
            self.logger.error(f"Failed to toggle visibility of {obj_name}: {e}")
    
    def delete_object(self, obj_name):
        """
        Delete a PyMOL object.
        
        Args:
            obj_name (str): Name of object to delete
        """
        try:
            self.cmd.delete(obj_name)
            self.logger.debug(f"Deleted object: {obj_name}")
        except Exception as e:
            self.logger.error(f"Failed to delete object {obj_name}: {e}")
    
    def highlight_object(self, obj_name):
        """
        Highlight a motif object (increase stick radius, show surfaces, etc.).
        
        Args:
            obj_name (str): Name of object to highlight
        """
        try:
            self.cmd.show('sticks', obj_name)
            self.cmd.show('cartoon', obj_name)
            self.cmd.set('stick_radius', 0.3, obj_name)
            self.cmd.set('cartoon_fancy_helices', 1)
        except Exception as e:
            self.logger.error(f"Failed to highlight object {obj_name}: {e}")
    
    def get_all_motif_objects(self):
        """
        Get all motif-related objects in the scene.
        
        Returns:
            list: Names of all objects
        """
        try:
            all_objects = self.cmd.get_names('objects')
            motif_objects = [obj for obj in all_objects if '_ALL' in obj or '_K' in obj or '_A' in obj]
            return motif_objects
        except Exception as e:
            self.logger.error(f"Failed to get motif objects: {e}")
            return []
