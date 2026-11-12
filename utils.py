"""
gmxFlow Utility Functions
File validation, GROMACS checks, and helper functions.
"""

import os
import shutil
import subprocess
from typing import List, Tuple, Optional, Dict, Any


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
                ["gmx", "--version"], capture_output=True, text=True, timeout=10
            )
            # Extract version from output
            version_line = (
                result.stdout.split("\n")[0] if result.stdout else "Unknown version"
            )
            return True, f"GROMACS found: {version_line}"
        except subprocess.TimeoutExpired:
            return True, f"GROMACS found at {gmx_path} (version check timed out)"
        except Exception as e:
            return True, f"GROMACS found at {gmx_path}"
    return (
        False,
        "GROMACS (gmx) not found in PATH. Please install GROMACS and ensure 'gmx' is accessible.",
    )


def check_mandatory_files(
    required_files: List[str], directory: str = "."
) -> Tuple[List[str], List[str]]:
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
    for unit in ["B", "KB", "MB", "GB"]:
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
    lines = output.split("\n")
    if len(lines) <= max_lines:
        return output

    truncated = lines[-max_lines:]
    return f"... [{len(lines) - max_lines} lines truncated] ...\n" + "\n".join(
        truncated
    )


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
        5: ["complex_solv.gro", "topol.top", "ions.mdp"],
        6: ["complex_ions.gro", "topol.top", "minim.mdp"],
        7: ["em.gro"],
        8: ["em.gro", "topol.top", "nvt.mdp", "index.ndx"],
        9: ["nvt.gro", "nvt.cpt", "topol.top", "npt.mdp", "index.ndx"],
        10: ["npt.gro", "npt.cpt", "topol.top", "md.mdp", "index.ndx"],
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
    1: [],      # pdb2gmx
    2: [1],     # insert-molecules
    3: [2],     # editconf
    4: [3],     # solvate
    5: [4],     # genion
    6: [5],     # EM
    7: [6],     # make_ndx
    8: [7],     # NVT
    9: [8],     # NPT
    10: [9],    # MD
}

STEP_NAMES = {
    1: "Generate Protein Topology",
    2: "Insert Ligand",
    3: "Define Simulation Box",
    4: "Solvate System",
    5: "Add Ions (Neutralize)",
    6: "Energy Minimization",
    7: "Index Generation",
    8: "NVT Equilibration",
    9: "NPT Equilibration",
    10: "Production MD",
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
    with open(flag_path, "w") as f:
        from datetime import datetime

        f.write(f"Completed: {datetime.now().isoformat()}\n")


def clear_step_flag(step_id: int, directory: str = ".") -> None:
    """Remove .done flag for a step."""
    flag_path = get_done_flag_path(step_id, directory)
    if os.path.exists(flag_path):
        os.remove(flag_path)


def clear_all_flags(directory: str = ".") -> None:
    """Remove all .done flags."""
    for step_id in range(1, 11):
        clear_step_flag(step_id, directory)


def bypass_step_flag(step_id: int, directory: str = ".") -> Tuple[bool, str]:
    """
    Bypass (clear) the .done flag for a specific step, allowing it to be re-run.

    Args:
        step_id: Pipeline step ID (1-9)
        directory: Working directory

    Returns:
        Tuple of (success: bool, message: str)
    """
    flag_path = get_done_flag_path(step_id, directory)
    if not os.path.exists(flag_path):
        return False, f"Step {step_id} flag not found (step not marked complete)"

    try:
        os.remove(flag_path)
        return True, f"Step {step_id} flag cleared - step can now be re-run"
    except Exception as e:
        return False, f"Failed to clear step {step_id} flag: {str(e)}"


def get_step_flags_status(directory: str = ".") -> list:
    """
    Get status of all step flags for display.

    Returns:
        List of tuples: (step_id, step_name, is_complete)
    """
    status = []
    for step_id in range(1, 11):
        name = STEP_NAMES.get(step_id, f"Step {step_id}")
        complete = is_step_complete(step_id, directory)
        status.append((step_id, name, complete))
    return status


def check_step_dependencies(
    step_id: int, directory: str = "."
) -> Tuple[bool, List[int]]:
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
    return {step_id: is_step_complete(step_id, directory) for step_id in range(1, 11)}


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
        5: ["complex_ions.gro"],
        6: ["em.gro", "em.tpr"],
        7: ["index.ndx"],
        8: ["nvt.gro", "nvt.tpr"],
        9: ["npt.gro", "npt.tpr"],
        10: ["md.xtc", "md.tpr"],
    }

    step_outputs = outputs.get(step_id, [])
    existing = []

    for filename in step_outputs:
        if os.path.exists(os.path.join(directory, filename)):
            existing.append(filename)

    return len(existing) > 0, existing


# === Topology Patching (Auto-add ligand after Step 4) ===


def get_ligand_name_from_itp(itp_path: str) -> Optional[str]:
    """
    Extract ligand molecule name from ligand.itp file.
    Looks for [ moleculetype ] section.
    """
    if not os.path.exists(itp_path):
        return None

    try:
        with open(itp_path, "r") as f:
            in_moleculetype = False
            for line in f:
                line = line.strip()
                if line.startswith("[ moleculetype ]"):
                    in_moleculetype = True
                    continue
                if (
                    in_moleculetype
                    and line
                    and not line.startswith(";")
                    and not line.startswith("[")
                ):
                    # First non-comment line after [ moleculetype ]
                    parts = line.split()
                    if parts:
                        return parts[0]  # Molecule name is first column
    except Exception:
        pass
    return None


def patch_topology_for_ligand(
    topol_path: str,
    ligand_itp: str = "ligand.itp",
    ligand_name: Optional[str] = None,
    directory: str = ".",
) -> Tuple[bool, str]:
    """
    Automatically patch topol.top to include ligand.

    Adds:
    1. #include "ligand.itp" after forcefield include
    2. Ligand entry in [ molecules ] section

    Returns:
        Tuple of (success: bool, message: str)
    """
    full_topol = os.path.join(directory, topol_path)
    full_itp = os.path.join(directory, ligand_itp)

    if not os.path.exists(full_topol):
        return False, f"Topology file not found: {topol_path}"

    if not os.path.exists(full_itp):
        return False, f"Ligand ITP not found: {ligand_itp}"

    # Get ligand name from ITP if not provided
    if not ligand_name:
        ligand_name = get_ligand_name_from_itp(full_itp)
        if not ligand_name:
            ligand_name = "UNK"  # Default fallback

    try:
        with open(full_topol, "r") as f:
            lines = f.readlines()

        # Check if already patched
        include_line = f'#include "{ligand_itp}"'
        already_included = any(include_line in line for line in lines)

        if already_included:
            return True, f"Topology already contains {ligand_itp}"

        # Find insertion points
        new_lines = []
        ff_include_found = False
        molecules_section = False
        ligand_added = False

        for i, line in enumerate(lines):
            new_lines.append(line)

            # Add ligand.itp after forcefield.itp include
            if not ff_include_found and "#include" in line and "forcefield.itp" in line:
                new_lines.append(f"; Include ligand topology\n")
                new_lines.append(f"{include_line}\n")
                new_lines.append("\n")
                ff_include_found = True

            # Track [ molecules ] section to add ligand at end
            if "[ molecules ]" in line:
                molecules_section = True

        # Add ligand to molecules section (at the end, before SOL)
        # We need to find the last molecule entry and add ligand before SOL
        final_lines = []
        sol_found = False

        for line in new_lines:
            # Insert ligand before SOL line
            stripped = line.strip()
            if molecules_section and stripped.startswith("SOL") and not ligand_added:
                final_lines.append(f"{ligand_name:<20} 1\n")
                ligand_added = True
            final_lines.append(line)

        # If no SOL found, add at the very end
        if not ligand_added:
            final_lines.append(f"{ligand_name:<20} 1\n")

        # Write back
        with open(full_topol, "w") as f:
            f.writelines(final_lines)

        return True, f"Patched topology: added {ligand_itp} and {ligand_name} molecule"

    except Exception as e:
        return False, f"Failed to patch topology: {str(e)}"


def check_topology_has_ligand(topol_path: str, directory: str = ".") -> bool:
    """Check if topology already includes a ligand."""
    full_path = os.path.join(directory, topol_path)
    if not os.path.exists(full_path):
        return False

    try:
        with open(full_path, "r") as f:
            content = f.read()
            return "ligand.itp" in content
    except Exception:
        return False


# === Smart Force Field Detection ===


def detect_ligand_forcefield(itp_path: str) -> str:
    """
    Analyze ligand.itp to guess the force field.
    Returns: "OPLS", "AMBER", "CHARMM", "GROMOS", or "Unknown"
    """
    if not os.path.exists(itp_path):
        return "Unknown"

    try:
        with open(itp_path, "r") as f:
            content = f.read().lower()
            if "opls_" in content:
                return "OPLS"
            if "ca" in content and "ha" in content and "os" in content:
                return "AMBER"
            if "cga" in content or "cng2" in content:
                return "CHARMM"
            if "ch1" in content or "ch2" in content or "oa" in content:
                return "GROMOS"
    except Exception:
        pass
    return "Unknown"


def get_gmx_forcefield_map() -> Dict[int, str]:
    """
    Query GROMACS for the list of available force fields.
    Returns: Dict mapping index to name
    """
    ff_map = {}
    try:
        # We run pdb2gmx with a non-existent file to get it to list force fields
        # and then we capture the output.
        process = subprocess.Popen(
            ["gmx", "pdb2gmx"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # Give it a bit of time to print the menu and then kill it
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

        # pdb2gmx prints the menu to stderr
        menu_text = stderr if stderr else stdout
        for line in menu_text.split("\n"):
            line = line.strip()
            if ":" in line and line[0].isdigit():
                parts = line.split(":", 1)
                idx = int(parts[0].strip())
                name = parts[1].strip()
                ff_map[idx] = name
    except Exception:
        pass
    return ff_map


def find_best_ff_index(target_name: str, ff_map: Dict[int, str]) -> Optional[int]:
    """
    Find the best index in ff_map for a given target force field name.
    """
    target_name = target_name.upper()
    for idx, name in ff_map.items():
        name_up = name.upper()
        if target_name in name_up:
            return idx
    return None


# === Deep Clean / Purge System ===


def purge_simulation_files(directory: str = ".") -> Tuple[int, List[str]]:
    """
    Delete all generated simulation files to allow a fresh start.
    Keeps mandatory input files.
    
    Returns:
        Tuple of (count_deleted, errors)
    """
    # Files we definitely want to delete
    patterns = [
        "*.gro", "topol.top", "*.itp", "*.tpr", "*.edr", "*.log", 
        "*.xtc", "*.trr", "*.xvg", "posre*", "*.ndx", ".step*.done",
        "*.mdp" # Delete generated MDPs too
    ]
    
    # Files we must NOT delete (inputs)
    keep = [
        "protein_only.pdb", "Protein.pdb", "ligand.gro", "ligand.itp",
        "gmxflow.py", "config.py", "utils.py", "pipeline.py", 
        "settings.py", "visualization.py", "analysis.py", "license_check.py"
    ]
    
    import glob
    
    deleted_count = 0
    errors = []
    
    for pattern in patterns:
        for filepath in glob.glob(os.path.join(directory, pattern)):
            filename = os.path.basename(filepath)
            if filename in keep:
                continue
            
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    deleted_count += 1
            except Exception as e:
                errors.append(f"Failed to delete {filename}: {str(e)}")
                
    return deleted_count, errors


# === Intelligent Error Analyzer ===


class ErrorAnalyzer:
    """Analyzes GROMACS output to suggest fixes for common errors."""
    
    KNOWLEDGE_BASE = {
        "LJ-14": {
            "pattern": r"No default LJ-14 types",
            "diagnosis": "Force Field Mismatch! Your protein force field and ligand topology don't match.",
            "fix": "Re-run Step 1 and select a force field compatible with your ligand (e.g., OPLS for OPLS ligands)."
        },
        "NET_CHARGE": {
            "pattern": r"System has non-zero total charge",
            "diagnosis": "Unbalanced system charge detected.",
            "fix": "Run the 'Add Ions (Neutralize)' step to add counter-ions."
        },
        "SOLVENT_ION": {
            "pattern": r"Not enough solvent for adding ions",
            "diagnosis": "You tried to replace a molecule that isn't solvent (like your ligand) with ions.",
            "fix": "Ensure you select the 'SOL' or 'Water' group when prompted for ion replacement."
        },
        "NS_TYPE": {
            "pattern": r"Ignoring obsolete mdp entry 'ns_type'",
            "diagnosis": "Using an outdated MDP parameter for this GROMACS version.",
            "fix": "This is just a warning, but you can remove 'ns_type' from your .mdp files to clean up logs."
        },
        "PDB2GMX_H": {
            "pattern": r"Atom H.* not found in residue",
            "diagnosis": "Missing or mismatched hydrogen atoms in your PDB.",
            "fix": "Try adding the '-ignh' flag to your pdb2gmx command (enabled by default in gmxFlow)."
        }
    }
    
    @staticmethod
    def analyze(output: str) -> List[Dict[str, str]]:
        """Scan output for known issues and return suggestions."""
        import re
        suggestions = []
        
        for key, info in ErrorAnalyzer.KNOWLEDGE_BASE.items():
            if re.search(info["pattern"], output, re.IGNORECASE):
                suggestions.append({
                    "id": key,
                    "diagnosis": info["diagnosis"],
                    "fix": info["fix"]
                })
        
        return suggestions
