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


# === Step Locking System ===

STEP_DEPENDENCIES = {
    1: [],          # pdb2gmx - no deps
    2: [1],         # insert-molecules needs pdb2gmx
    3: [2],         # editconf needs insert-molecules
    4: [3],         # solvate needs editconf
    5: [4],         # EM needs solvate
    6: [5],         # make_ndx needs EM
    7: [6],         # NVT needs make_ndx
    8: [7],         # NPT needs NVT
    9: [8],         # MD needs NPT
}

STEP_NAMES = {
    1: "Generate Protein Topology",
    2: "Insert Ligand",
    3: "Define Simulation Box",
    4: "Solvate System",
    5: "Energy Minimization",
    6: "Index Generation",
    7: "NVT Equilibration",
    8: "NPT Equilibration",
    9: "Production MD",
}


def get_done_flag_path(step_id: int, directory: str = ".") -> str:
    """Get path to .done flag file for a step."""
    return os.path.join(directory, f".step{step_id}.done")


def is_step_complete(step_id: int, directory: str = ".") -> bool:
    """Check if a step has completed (has .done flag)."""
    return os.path.exists(get_done_flag_path(step_id, directory))


def mark_step_complete(step_id: int, directory: str = ".") -> None:
    """Mark a step as complete by creating .done flag."""
    flag_path = get_done_flag_path(step_id, directory)
    with open(flag_path, 'w') as f:
        from datetime import datetime
        f.write(f"Completed: {datetime.now().isoformat()}\n")


def clear_step_flag(step_id: int, directory: str = ".") -> None:
    """Remove .done flag for a step."""
    flag_path = get_done_flag_path(step_id, directory)
    if os.path.exists(flag_path):
        os.remove(flag_path)


def clear_all_flags(directory: str = ".") -> None:
    """Remove all .done flags."""
    for step_id in range(1, 10):
        clear_step_flag(step_id, directory)


def check_step_dependencies(step_id: int, directory: str = ".") -> Tuple[bool, List[int]]:
    """
    Check if all dependencies for a step are satisfied.
    
    Args:
        step_id: Pipeline step ID
        directory: Working directory
    
    Returns:
        Tuple of (can_run: bool, missing_steps: list of incomplete step IDs)
    """
    deps = STEP_DEPENDENCIES.get(step_id, [])
    missing = []
    
    for dep_id in deps:
        if not is_step_complete(dep_id, directory):
            missing.append(dep_id)
    
    return len(missing) == 0, missing


def get_step_status_summary(directory: str = ".") -> dict:
    """
    Get completion status of all steps.
    
    Returns:
        Dict mapping step_id to completion status
    """
    return {
        step_id: is_step_complete(step_id, directory)
        for step_id in range(1, 10)
    }


def check_output_exists(step_id: int, directory: str = ".") -> Tuple[bool, List[str]]:
    """
    Check if output files from a step already exist (for resume detection).
    
    Args:
        step_id: Pipeline step ID
        directory: Working directory
    
    Returns:
        Tuple of (exists: bool, existing_files: list)
    """
    outputs = {
        1: ["protein.gro", "topol.top"],
        2: ["complex.gro"],
        3: ["complex_box.gro"],
        4: ["complex_solv.gro"],
        5: ["em.gro", "em.tpr"],
        6: ["index.ndx"],
        7: ["nvt.gro", "nvt.tpr"],
        8: ["npt.gro", "npt.tpr"],
        9: ["md.xtc", "md.tpr"],
    }
    
    step_outputs = outputs.get(step_id, [])
    existing = []
    
    for filename in step_outputs:
        if os.path.exists(os.path.join(directory, filename)):
            existing.append(filename)
    
    return len(existing) > 0, existing

