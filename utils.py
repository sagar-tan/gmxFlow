"""
gmxFlow Utility Functions
File validation, GROMACS checks, and helper functions.
"""

import os
import shutil
import subprocess
from typing import List, Tuple, Optional


def check_gromacs_available() -> Tuple[bool, str]:
    """
    Check if GROMACS (gmx) is available in the system PATH.
    
    Returns:
        Tuple of (available: bool, message: str)
    """
    gmx_path = shutil.which("gmx")
    if gmx_path:
        try:
            result = subprocess.run(
                ["gmx", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Extract version from output
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
            return True, f"GROMACS found: {version_line}"
        except subprocess.TimeoutExpired:
            return True, f"GROMACS found at {gmx_path} (version check timed out)"
        except Exception as e:
            return True, f"GROMACS found at {gmx_path}"
    return False, "GROMACS (gmx) not found in PATH. Please install GROMACS and ensure 'gmx' is accessible."


def check_mandatory_files(required_files: List[str], directory: str = ".") -> Tuple[List[str], List[str]]:
    """
    Check which mandatory files exist in the specified directory.
    
    Args:
        required_files: List of required file names
        directory: Directory to check (default: current directory)
    
    Returns:
        Tuple of (found_files, missing_files)
    """
    found = []
    missing = []
    
    for filename in required_files:
        filepath = os.path.join(directory, filename)
        if os.path.exists(filepath):
            found.append(filename)
        else:
            missing.append(filename)
    
    return found, missing


def check_file_exists(filepath: str) -> bool:
    """Check if a file exists."""
    return os.path.exists(filepath)


def get_file_size_human(filepath: str) -> str:
    """Get human-readable file size."""
    if not os.path.exists(filepath):
        return "N/A"
    
    size = os.path.getsize(filepath)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def check_tool_available(tool_name: str) -> Tuple[bool, str]:
    """
    Check if an external tool is available.
    
    Args:
        tool_name: Name of the tool (e.g., 'vmd', 'xmgrace')
    
    Returns:
        Tuple of (available: bool, path or error message: str)
    """
    tool_path = shutil.which(tool_name)
    if tool_path:
        return True, tool_path
    return False, f"{tool_name} not found in PATH"


def format_log_line(message: str, level: str = "INFO") -> str:
    """
    Format a log message with timestamp and level.
    
    Args:
        message: Log message
        level: Log level (INFO, WARNING, ERROR)
    
    Returns:
        Formatted log string
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    return f"[{timestamp}] [{level}] {message}"


def truncate_output(output: str, max_lines: int = 50) -> str:
    """
    Truncate output to maximum number of lines.
    
    Args:
        output: Full output string
        max_lines: Maximum lines to keep
    
    Returns:
        Truncated output with indicator if truncated
    """
    lines = output.split('\n')
    if len(lines) <= max_lines:
        return output
    
    truncated = lines[-max_lines:]
    return f"... [{len(lines) - max_lines} lines truncated] ...\n" + '\n'.join(truncated)


def get_step_prerequisites(step_id: int) -> List[str]:
    """
    Get prerequisite files needed for a pipeline step.
    
    Args:
        step_id: Pipeline step ID (1-9)
    
    Returns:
        List of required file names
    """
    prerequisites = {
        1: ["protein_only.pdb"],
        2: ["protein.gro", "ligand.gro"],
        3: ["complex.gro"],
        4: ["complex_box.gro", "topol.top", "ligand.itp"],
        5: ["complex_solv.gro", "topol.top", "minim.mdp"],
        6: ["em.gro"],
        7: ["em.gro", "topol.top", "nvt.mdp", "index.ndx"],
        8: ["nvt.gro", "nvt.cpt", "topol.top", "npt.mdp", "index.ndx"],
        9: ["npt.gro", "npt.cpt", "topol.top", "md.mdp", "index.ndx"],
    }
    return prerequisites.get(step_id, [])


def validate_step_ready(step_id: int, directory: str = ".") -> Tuple[bool, List[str]]:
    """
    Validate if a step is ready to run by checking prerequisites.
    
    Args:
        step_id: Pipeline step ID
        directory: Working directory
    
    Returns:
        Tuple of (ready: bool, missing_files: list)
    """
    prereqs = get_step_prerequisites(step_id)
    _, missing = check_mandatory_files(prereqs, directory)
    return len(missing) == 0, missing
