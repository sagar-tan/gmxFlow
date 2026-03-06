"""
gmxFlow Analysis Module
Post-simulation analysis features for MD trajectories.
"""

import subprocess
import os
from typing import Callable, Optional
from dataclasses import dataclass

from config import ANALYSIS_STEPS, PROTEIN_ANALYSIS_STEPS, AnalysisStep


@dataclass
class AnalysisResult:
    """Result of an analysis operation."""
    name: str
    success: bool
    output_file: str
    stdout: str
    stderr: str
    error_message: Optional[str] = None


class AnalysisRunner:
    """Runs post-simulation analysis commands."""
    
    def __init__(self, working_dir: str = ".", analysis_steps: list = None):
        self.working_dir = working_dir
        self.analysis_steps = analysis_steps if analysis_steps is not None else ANALYSIS_STEPS
    
    def set_analysis_steps(self, steps: list):
        """Update the analysis steps list (e.g. when switching mode)."""
        self.analysis_steps = steps
    
    def get_analysis_steps(self) -> list[AnalysisStep]:
        """Get all available analysis steps."""
        return self.analysis_steps
    
    def check_prerequisites(self) -> tuple[bool, list[str]]:
        """
        Check if required files for analysis exist.
        
        Returns:
            Tuple of (ready: bool, missing_files: list)
        """
        required = ["md.tpr", "md.xtc"]
        # index.ndx is only required for protein+ligand analysis steps
        needs_index = any("-n index.ndx" in s.command or "index.ndx" in s.command for s in self.analysis_steps)
        if needs_index:
            required.append("index.ndx")
        missing = []
        
        for filename in required:
            filepath = os.path.join(self.working_dir, filename)
            if not os.path.exists(filepath):
                missing.append(filename)
        
        return len(missing) == 0, missing
    
    def run_analysis(
        self,
        step_index: int,
        on_output: Optional[Callable[[str], None]] = None,
        interactive: bool = True
    ) -> AnalysisResult:
        """
        Run an analysis step.
        
        Args:
            step_index: Index of the analysis step (0-based)
            on_output: Callback for real-time output
            interactive: If True, allow user input for group selection
        
        Returns:
            AnalysisResult with execution details
        """
        if step_index < 0 or step_index >= len(self.analysis_steps):
            return AnalysisResult(
                name="Unknown",
                success=False,
                output_file="",
                stdout="",
                stderr="",
                error_message=f"Invalid analysis step index: {step_index}"
            )
        
        step = self.analysis_steps[step_index]
        
        if on_output:
            on_output(f">>> Running: {step.name}")
            on_output(f">>> Command: {step.command}")
            on_output("-" * 60)
        
        try:
            if interactive:
                # Interactive mode for group selection
                return_code = os.system(f"cd {self.working_dir} && {step.command}")
                
                success = return_code == 0
                return AnalysisResult(
                    name=step.name,
                    success=success,
                    output_file=step.output_file if success else "",
                    stdout="[Interactive mode]",
                    stderr=""
                )
            else:
                # Non-interactive mode
                result = subprocess.run(
                    step.command,
                    shell=True,
                    cwd=self.working_dir,
                    capture_output=True,
                    text=True
                )
                
                success = result.returncode == 0
                
                if on_output:
                    if result.stdout:
                        for line in result.stdout.split('\n'):
                            on_output(line)
                    if result.stderr:
                        for line in result.stderr.split('\n'):
                            on_output(f"[ERR] {line}")
                
                return AnalysisResult(
                    name=step.name,
                    success=success,
                    output_file=step.output_file if success else "",
                    stdout=result.stdout,
                    stderr=result.stderr
                )
                
        except Exception as e:
            error_msg = str(e)
            if on_output:
                on_output(f">>> Error: {error_msg}")
            
            return AnalysisResult(
                name=step.name,
                success=False,
                output_file="",
                stdout="",
                stderr="",
                error_message=error_msg
            )
    
    def run_trajectory_cleaning(
        self,
        on_output: Optional[Callable[[str], None]] = None
    ) -> AnalysisResult:
        """Run trajectory cleaning (first analysis step)."""
        return self.run_analysis(0, on_output, interactive=False)
    
    def run_backbone_rmsd(
        self,
        on_output: Optional[Callable[[str], None]] = None
    ) -> AnalysisResult:
        """Calculate backbone RMSD."""
        return self.run_analysis(1, on_output, interactive=False)
    
    def run_ligand_rmsd(
        self,
        on_output: Optional[Callable[[str], None]] = None
    ) -> AnalysisResult:
        """Calculate ligand RMSD."""
        return self.run_analysis(2, on_output, interactive=False)
    
    def run_distance_analysis(
        self,
        on_output: Optional[Callable[[str], None]] = None
    ) -> AnalysisResult:
        """Calculate protein-ligand distance."""
        return self.run_analysis(3, on_output, interactive=False)
