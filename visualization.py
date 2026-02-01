"""
gmxFlow Visualization Module
Launchers for external visualization tools (VMD, xmgrace).
"""

import subprocess
import os
from typing import Optional, Tuple

from utils import check_tool_available


class VisualizationManager:
    """Manages external visualization tool launches."""
    
    def __init__(self, working_dir: str = "."):
        self.working_dir = working_dir
    
    def check_vmd_available(self) -> Tuple[bool, str]:
        """Check if VMD is available."""
        return check_tool_available("vmd")
    
    def check_xmgrace_available(self) -> Tuple[bool, str]:
        """Check if xmgrace is available."""
        # Try both 'xmgrace' and 'grace'
        available, path = check_tool_available("xmgrace")
        if available:
            return True, path
        return check_tool_available("grace")
    
    def launch_vmd(
        self,
        structure_file: str = "md.gro",
        trajectory_file: str = "md_fit.xtc"
    ) -> Tuple[bool, str]:
        """
        Launch VMD with structure and trajectory.
        
        Args:
            structure_file: Structure file (default: md.gro)
            trajectory_file: Trajectory file (default: md_fit.xtc)
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        available, msg = self.check_vmd_available()
        if not available:
            return False, msg
        
        struct_path = os.path.join(self.working_dir, structure_file)
        traj_path = os.path.join(self.working_dir, trajectory_file)
        
        # Check files exist
        if not os.path.exists(struct_path):
            return False, f"Structure file not found: {structure_file}"
        if not os.path.exists(traj_path):
            return False, f"Trajectory file not found: {trajectory_file}"
        
        try:
            # Launch VMD in background
            subprocess.Popen(
                ["vmd", struct_path, traj_path],
                cwd=self.working_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True, f"VMD launched with {structure_file} and {trajectory_file}"
        except Exception as e:
            return False, f"Failed to launch VMD: {str(e)}"
    
    def launch_xmgrace(self, xvg_file: str) -> Tuple[bool, str]:
        """
        Launch xmgrace to view an .xvg file.
        
        Args:
            xvg_file: Path to .xvg file
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        available, tool_path = self.check_xmgrace_available()
        if not available:
            return False, "xmgrace/grace not found in PATH"
        
        xvg_path = os.path.join(self.working_dir, xvg_file)
        
        if not os.path.exists(xvg_path):
            return False, f"XVG file not found: {xvg_file}"
        
        # Determine which command to use
        tool_name = "xmgrace" if "xmgrace" in tool_path else "grace"
        
        try:
            subprocess.Popen(
                [tool_name, xvg_path],
                cwd=self.working_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True, f"xmgrace launched with {xvg_file}"
        except Exception as e:
            return False, f"Failed to launch xmgrace: {str(e)}"
    
    def list_available_xvg_files(self) -> list[str]:
        """List all .xvg files in the working directory."""
        xvg_files = []
        try:
            for filename in os.listdir(self.working_dir):
                if filename.endswith('.xvg'):
                    xvg_files.append(filename)
        except Exception:
            pass
        return sorted(xvg_files)
    
    def get_visualization_options(self) -> dict:
        """
        Get available visualization options based on installed tools and files.
        
        Returns:
            Dict with available options and their status
        """
        vmd_available, vmd_msg = self.check_vmd_available()
        xmgrace_available, xmgrace_msg = self.check_xmgrace_available()
        
        # Check for trajectory files
        has_trajectory = (
            os.path.exists(os.path.join(self.working_dir, "md.gro")) and
            os.path.exists(os.path.join(self.working_dir, "md_fit.xtc"))
        )
        
        xvg_files = self.list_available_xvg_files()
        
        return {
            "vmd": {
                "available": vmd_available,
                "message": vmd_msg,
                "has_files": has_trajectory
            },
            "xmgrace": {
                "available": xmgrace_available,
                "message": xmgrace_msg,
                "xvg_files": xvg_files
            }
        }
