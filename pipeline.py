"""
gmxFlow Pipeline Execution Module
Handles running GROMACS commands and capturing output.
"""

import subprocess
import threading
import queue
import os
from typing import Callable, Optional, Generator
from dataclasses import dataclass
from enum import Enum

from config import PipelineStep, PIPELINE_STEPS


class StepStatus(Enum):
    """Pipeline step execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class StepResult:
    """Result of a pipeline step execution."""
    step_id: int
    status: StepStatus
    return_code: int
    stdout: str
    stderr: str
    error_message: Optional[str] = None


class PipelineExecutor:
    """Executes pipeline steps and manages state."""
    
    def __init__(self, working_dir: str = ".", steps: list = None):
        self.working_dir = working_dir
        self.steps = steps if steps is not None else PIPELINE_STEPS
        self.step_status: dict[int, StepStatus] = {
            step.id: StepStatus.PENDING for step in self.steps
        }
        self.current_process: Optional[subprocess.Popen] = None
        self._output_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
    
    def get_step(self, step_id: int) -> Optional[PipelineStep]:
        """Get pipeline step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_status(self, step_id: int) -> StepStatus:
        """Get current status of a step."""
        return self.step_status.get(step_id, StepStatus.PENDING)
    
    def set_status(self, step_id: int, status: StepStatus):
        """Set status of a step."""
        self.step_status[step_id] = status
    
    def execute_step(
        self,
        step_id: int,
        on_output: Optional[Callable[[str], None]] = None,
        interactive: bool = False
    ) -> StepResult:
        """
        Execute a pipeline step.
        
        Args:
            step_id: ID of the step to execute
            on_output: Callback function for real-time output
            interactive: If True, allow user input (for steps like pdb2gmx)
        
        Returns:
            StepResult with execution details
        """
        step = self.get_step(step_id)
        if not step:
            return StepResult(
                step_id=step_id,
                status=StepStatus.ERROR,
                return_code=-1,
                stdout="",
                stderr="",
                error_message=f"Invalid step ID: {step_id}"
            )
        
        self.set_status(step_id, StepStatus.RUNNING)
        
        if on_output:
            on_output(f">>> Executing Step {step_id}: {step.name}")
            on_output(f">>> Command: {step.command}")
            on_output("-" * 60)
        
        try:
            if interactive:
                # Interactive mode - user can provide input
                result = self._run_interactive(step.command, on_output)
            else:
                # Non-interactive mode - capture all output
                result = self._run_captured(step.command, on_output)
            
            if result.return_code == 0:
                self.set_status(step_id, StepStatus.COMPLETE)
                if on_output:
                    on_output("-" * 60)
                    on_output(f">>> Step {step_id} completed successfully")
            else:
                self.set_status(step_id, StepStatus.ERROR)
                if on_output:
                    on_output("-" * 60)
                    on_output(f">>> Step {step_id} failed with return code {result.return_code}")
            
            return StepResult(
                step_id=step_id,
                status=self.get_status(step_id),
                return_code=result.return_code,
                stdout=result.stdout,
                stderr=result.stderr
            )
            
        except Exception as e:
            self.set_status(step_id, StepStatus.ERROR)
            error_msg = str(e)
            if on_output:
                on_output(f">>> Error: {error_msg}")
            
            return StepResult(
                step_id=step_id,
                status=StepStatus.ERROR,
                return_code=-1,
                stdout="",
                stderr="",
                error_message=error_msg
            )
    
    def _run_interactive(
        self,
        command: str,
        on_output: Optional[Callable[[str], None]] = None
    ) -> StepResult:
        """Run command in interactive mode using system shell."""
        # For interactive commands, we use os.system which allows terminal interaction
        return_code = os.system(f"cd {self.working_dir} && {command}")
        
        return StepResult(
            step_id=0,
            status=StepStatus.COMPLETE if return_code == 0 else StepStatus.ERROR,
            return_code=return_code,
            stdout="[Interactive mode - output shown in terminal]",
            stderr=""
        )
    
    def _run_captured(
        self,
        command: str,
        on_output: Optional[Callable[[str], None]] = None
    ) -> StepResult:
        """Run command and capture output."""
        stdout_lines = []
        stderr_lines = []
        
        # Use shell=True to handle command chaining (&&)
        # Pass env to ensure CUDA/GPU environment variables are available
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=self.working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=os.environ
        )
        self.current_process = process
        
        # Read output in real-time using threads
        def read_stream(stream, lines_list, prefix=""):
            for line in iter(stream.readline, ''):
                if line:
                    lines_list.append(line.rstrip())
                    if on_output:
                        on_output(f"{prefix}{line.rstrip()}")
        
        stdout_thread = threading.Thread(
            target=read_stream,
            args=(process.stdout, stdout_lines)
        )
        # Note: GROMACS writes most output to stderr, not just errors
        # So we don't prefix stderr with [ERR] to avoid confusion
        stderr_thread = threading.Thread(
            target=read_stream,
            args=(process.stderr, stderr_lines, "")
        )
        
        stdout_thread.start()
        stderr_thread.start()
        
        process.wait()
        stdout_thread.join()
        stderr_thread.join()
        
        self.current_process = None
        
        return StepResult(
            step_id=0,
            status=StepStatus.COMPLETE if process.returncode == 0 else StepStatus.ERROR,
            return_code=process.returncode,
            stdout='\n'.join(stdout_lines),
            stderr='\n'.join(stderr_lines)
        )
    
    def cancel_current(self):
        """Cancel the currently running process."""
        if self.current_process:
            self.current_process.terminate()
            self._stop_event.set()
    
    def reset_all(self):
        """Reset all step statuses to pending."""
        for step in self.steps:
            self.step_status[step.id] = StepStatus.PENDING
