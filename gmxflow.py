#!/usr/bin/env python3
"""
gmxFlow - GROMACS Pipeline Manager
A terminal user interface for running molecular dynamics simulations.

Usage:
    gmxflow [--version] [--help] [--dry-run]

Author: gmxFlow Development Team
Version: 1.0.0
"""

import sys
import os
import argparse

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to import rich, fall back to plain output if not available
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.markdown import Markdown
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from config import (
    APP_NAME, APP_VERSION, APP_DESCRIPTION, BANNER,
    PIPELINE_STEPS, ANALYSIS_STEPS, MANDATORY_FILES,
    STATUS_SYMBOLS
)
from utils import (
    check_gromacs_available, check_mandatory_files,
    validate_step_ready, format_log_line,
    check_step_dependencies, is_step_complete, mark_step_complete,
    clear_all_flags, check_output_exists, STEP_NAMES
)
from pipeline import PipelineExecutor, StepStatus
from analysis import AnalysisRunner
from visualization import VisualizationManager


class PlainConsole:
    """Fallback console when rich is not available."""
    
    def print(self, text, **kwargs):
        # Strip rich markup for plain output
        import re
        clean = re.sub(r'\[/?[^\]]+\]', '', str(text))
        print(clean)


class GmxFlowApp:
    """Main gmxFlow TUI Application."""
    
    def __init__(self, dry_run: bool = False):
        self.console = Console() if RICH_AVAILABLE else PlainConsole()
        self.working_dir = os.getcwd()
        self.pipeline = PipelineExecutor(self.working_dir)
        self.analysis = AnalysisRunner(self.working_dir)
        self.visualization = VisualizationManager(self.working_dir)
        self.log_messages: list = []
        self.max_log_lines = 15
        self.dry_run = dry_run
    
    def add_log(self, message: str, level: str = "INFO"):
        """Add a message to the log."""
        formatted = format_log_line(message, level)
        self.log_messages.append(formatted)
        if len(self.log_messages) > self.max_log_lines:
            self.log_messages = self.log_messages[-self.max_log_lines:]
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def prompt(self, message: str, choices: list = None, default: str = None) -> str:
        """Cross-compatible prompt."""
        if RICH_AVAILABLE:
            if choices:
                return Prompt.ask(message, choices=choices, default=default)
            return Prompt.ask(message, default=default)
        else:
            if choices:
                print(f"{message} [{'/'.join(choices)}] (default: {default}): ", end="")
            else:
                print(f"{message}: ", end="")
            response = input().strip()
            return response if response else default
    
    def confirm(self, message: str) -> bool:
        """Cross-compatible confirmation."""
        if RICH_AVAILABLE:
            return Confirm.ask(message)
        else:
            print(f"{message} [y/n]: ", end="")
            return input().strip().lower() in ['y', 'yes']
    
    def show_banner(self):
        """Display the application banner."""
        if RICH_AVAILABLE:
            banner_text = Text(BANNER, style="bold cyan")
            mode_text = " [DRY-RUN MODE]" if self.dry_run else ""
            self.console.print(Panel(
                banner_text,
                subtitle=f"{APP_DESCRIPTION} v{APP_VERSION}{mode_text}",
                border_style="cyan",
                padding=(0, 2)
            ))
        else:
            print(BANNER)
            mode_text = " [DRY-RUN MODE]" if self.dry_run else ""
            print(f"  {APP_DESCRIPTION} v{APP_VERSION}{mode_text}")
            print("=" * 60)
    
    def show_system_status(self):
        """Display system status (GROMACS, files)."""
        if RICH_AVAILABLE:
            table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
            table.add_column("Item", style="white")
            table.add_column("Status", style="white")
        
        # GROMACS check
        gmx_ok, gmx_msg = check_gromacs_available()
        
        if RICH_AVAILABLE:
            gmx_style = "green" if gmx_ok else "red"
            gmx_symbol = "✓" if gmx_ok else "✗"
            table.add_row("GROMACS", f"[{gmx_style}]{gmx_symbol} {gmx_msg}[/]")
            table.add_row("Working Dir", f"[dim]{self.working_dir}[/]")
        else:
            symbol = "OK" if gmx_ok else "MISSING"
            print(f"  GROMACS: [{symbol}] {gmx_msg}")
            print(f"  Working Dir: {self.working_dir}")
        
        # Mandatory files check
        found, missing = check_mandatory_files(MANDATORY_FILES, self.working_dir)
        
        if RICH_AVAILABLE:
            if missing:
                file_status = f"[yellow]⚠ {len(found)}/{len(MANDATORY_FILES)} files found[/]"
            else:
                file_status = f"[green]✓ All {len(MANDATORY_FILES)} files found[/]"
            table.add_row("Input Files", file_status)
            self.console.print(Panel(table, title="System Status", border_style="dim"))
        else:
            status = f"{len(found)}/{len(MANDATORY_FILES)} files found"
            print(f"  Input Files: {status}")
            print()
    
    def show_pipeline_menu(self):
        """Display the pipeline steps menu with lock status."""
        if RICH_AVAILABLE:
            table = Table(
                show_header=True,
                header_style="bold white",
                box=box.ROUNDED,
                border_style="cyan",
                padding=(0, 1)
            )
            table.add_column("#", justify="center", width=3)
            table.add_column("Step", width=35)
            table.add_column("Locked", justify="center", width=10)
            table.add_column("Status", justify="center", width=12)
        else:
            print("Pipeline Steps:")
            print("-" * 60)
        
        for step in PIPELINE_STEPS:
            # Check step locking
            can_run, missing_deps = check_step_dependencies(step.id, self.working_dir)
            done = is_step_complete(step.id, self.working_dir)
            
            if RICH_AVAILABLE:
                # Lock status
                if not can_run:
                    dep_names = [f"Step {d}" for d in missing_deps]
                    lock_text = f"[red]🔒 Need {', '.join(dep_names)}[/]"
                else:
                    lock_text = "[green]✓ Ready[/]"
                
                # Done status from .done flag
                if done:
                    status_text = f"[green]{STATUS_SYMBOLS['complete']} Complete[/]"
                else:
                    status_text = f"[dim]{STATUS_SYMBOLS['pending']} Pending[/]"
                
                step_num = f"[bold cyan]{step.id}[/]"
                step_name = step.name
                if step.user_input_required:
                    step_name += " [dim](interactive)[/]"
                
                table.add_row(step_num, step_name, lock_text, status_text)
            else:
                lock = "LOCKED" if not can_run else "READY"
                status = "DONE" if done else "PENDING"
                print(f"  [{step.id}] {step.name} - {lock} - {status}")
        
        if RICH_AVAILABLE:
            self.console.print(Panel(table, title="Pipeline Steps", border_style="cyan"))
        else:
            print()
    
    def show_quick_actions(self):
        """Display quick action keys."""
        if RICH_AVAILABLE:
            actions = Table(show_header=False, box=None, padding=(0, 2))
            actions.add_column()
            actions.add_column()
            actions.add_column()
            actions.add_column()
            
            actions.add_row(
                "[cyan][1-9][/] Run Step",
                "[cyan][A][/] Analysis",
                "[cyan][P][/] Full Pipeline",
                "[cyan][Q][/] Quit"
            )
            actions.add_row(
                "[cyan][F][/] File Check",
                "[cyan][R][/] Reset All",
                "[cyan][H][/] Help",
                "[cyan][V][/] Visualization"
            )
            self.console.print(Panel(actions, border_style="dim"))
        else:
            print("Actions: [1-9] Run Step | [A] Analysis | [P] Full Pipeline | [Q] Quit")
            print("         [F] File Check | [R] Reset | [H] Help | [V] Visualization")
            print()
    
    def show_log_panel(self):
        """Display the log output panel."""
        if self.log_messages:
            log_text = "\n".join(self.log_messages[-10:])
        else:
            log_text = "> Ready. Select a step to begin..." if not RICH_AVAILABLE else "[dim]> Ready. Select a step to begin...[/]"
        
        if RICH_AVAILABLE:
            self.console.print(Panel(log_text, title="Log Output", border_style="dim", height=12))
        else:
            print("Log:")
            print(log_text)
            print()
    
    def show_main_screen(self):
        """Display the main application screen."""
        self.clear_screen()
        self.show_banner()
        self.show_system_status()
        self.show_pipeline_menu()
        self.show_quick_actions()
        self.show_log_panel()
    
    def run_pipeline_step(self, step_id: int):
        """Execute a pipeline step with locking and resume detection."""
        step = self.pipeline.get_step(step_id)
        if not step:
            self.add_log(f"Invalid step ID: {step_id}", "ERROR")
            return False
        
        # === STEP LOCKING CHECK ===
        can_run, missing_deps = check_step_dependencies(step_id, self.working_dir)
        if not can_run:
            dep_names = [f"Step {d} ({STEP_NAMES[d]})" for d in missing_deps]
            self.console.print(f"[red]✗ BLOCKED: Step {step_id} requires completion of:[/]")
            for name in dep_names:
                self.console.print(f"[red]  • {name}[/]")
            self.add_log(f"Step {step_id} blocked - dependencies not met", "ERROR")
            input("\n[Press Enter to continue...]")
            return False
        
        # === RESUME DETECTION ===
        outputs_exist, existing_files = check_output_exists(step_id, self.working_dir)
        if outputs_exist:
            self.console.print(f"[yellow]⚠ Output files already exist: {', '.join(existing_files)}[/]")
            if not self.confirm("Overwrite existing files?"):
                self.add_log(f"Step {step_id} cancelled - user declined overwrite", "INFO")
                return False
        
        # === DRY RUN MODE ===
        if self.dry_run:
            self.console.print(f"\n[bold yellow]DRY-RUN: Would execute Step {step_id}: {step.name}[/]")
            self.console.print(f"[dim]Command: {step.command}[/]")
            if step.produces:
                self.console.print(f"[dim]Would produce: {', '.join(step.produces)}[/]")
            self.add_log(f"DRY-RUN: Step {step_id} command shown", "INFO")
            input("\n[Press Enter to continue...]")
            return True
        
        # Check prerequisites files
        ready, missing = validate_step_ready(step_id, self.working_dir)
        if missing:
            self.console.print(f"[yellow]⚠ Missing input files: {', '.join(missing)}[/]")
            if not self.confirm("Continue anyway?"):
                return False
        
        # Show manual intervention warning
        if step.manual_intervention:
            if RICH_AVAILABLE:
                self.console.print(Panel(
                    f"[yellow]⚠ After this step, please manually edit:[/]\n"
                    f"  File: [bold]{step.manual_intervention['file']}[/]\n"
                    f"  Actions:\n" + "\n".join(f"    • {a}" for a in step.manual_intervention['actions']),
                    title="Manual Intervention Required",
                    border_style="yellow"
                ))
            else:
                print(f"WARNING: After this step, edit {step.manual_intervention['file']}")
            if not self.confirm("Continue?"):
                return False
        
        self.add_log(f"Starting step {step_id}: {step.name}")
        self.console.print(f"\n[bold cyan]>>> Executing Step {step_id}: {step.name}[/]")
        self.console.print(f"[dim]Command: {step.command}[/]\n")
        self.console.print("[yellow]" + "─" * 60 + "[/]\n")
        
        # Execute
        interactive = step.user_input_required or step.id == 6
        result = self.pipeline.execute_step(
            step_id,
            on_output=lambda msg: self.console.print(msg),
            interactive=interactive
        )
        
        self.console.print("\n[yellow]" + "─" * 60 + "[/]")
        
        if result.status == StepStatus.COMPLETE:
            # === MARK STEP COMPLETE ===
            mark_step_complete(step_id, self.working_dir)
            self.add_log(f"Step {step_id} completed successfully", "INFO")
            self.console.print(f"\n[green]✓ Step {step_id} completed successfully![/]")
            if step.produces:
                self.console.print(f"[dim]  Produced: {', '.join(step.produces)}[/]")
            input("\n[Press Enter to continue...]")
            return True
        else:
            self.add_log(f"Step {step_id} failed", "ERROR")
            self.console.print(f"\n[red]✗ Step {step_id} failed![/]")
            if result.error_message:
                self.console.print(f"[red]  Error: {result.error_message}[/]")
            input("\n[Press Enter to continue...]")
            return False
    
    def run_full_pipeline(self):
        """Run all pipeline steps in sequence."""
        self.clear_screen()
        self.console.print(f"\n[bold cyan]>>> Full Pipeline Execution[/]")
        
        if self.dry_run:
            self.console.print("[bold yellow]DRY-RUN MODE: Showing all commands without execution[/]\n")
        
        for step in PIPELINE_STEPS:
            self.console.print(f"\n[bold]Step {step.id}: {step.name}[/]")
            
            if self.dry_run:
                self.console.print(f"[dim]  Command: {step.command}[/]")
                if step.produces:
                    self.console.print(f"[dim]  Produces: {', '.join(step.produces)}[/]")
                continue
            
            # Check if already complete
            if is_step_complete(step.id, self.working_dir):
                self.console.print(f"[green]  ✓ Already complete, skipping[/]")
                continue
            
            # Run the step
            success = self.run_pipeline_step(step.id)
            if not success:
                self.console.print(f"\n[red]Pipeline halted at step {step.id}[/]")
                break
        
        if self.dry_run:
            self.console.print("\n[bold yellow]DRY-RUN complete. No commands were executed.[/]")
        
        input("\n[Press Enter to continue...]")
    
    def show_analysis_menu(self):
        """Display and handle the analysis menu."""
        self.clear_screen()
        self.console.print("[bold cyan]Analysis Tools[/]\n")
        
        # Check if MD complete
        if not is_step_complete(9, self.working_dir):
            self.console.print("[yellow]⚠ Production MD (Step 9) not complete.[/]")
            self.console.print("[dim]Analysis may fail without MD output files.[/]\n")
        
        for i, step in enumerate(ANALYSIS_STEPS, 1):
            self.console.print(f"  [{i}] {step.name}")
            self.console.print(f"      [dim]→ {step.output_file}[/]")
        
        self.console.print(f"\n  [B] Back to main menu")
        
        choice = self.prompt("\nSelect analysis", choices=["1", "2", "3", "4", "b", "B"], default="b")
        
        if choice.lower() == "b":
            return
        
        if self.dry_run:
            step = ANALYSIS_STEPS[int(choice) - 1]
            self.console.print(f"\n[bold yellow]DRY-RUN: Would run {step.name}[/]")
            self.console.print(f"[dim]Command: {step.command}[/]")
            input("\n[Press Enter to continue...]")
            return
        
        step_idx = int(choice) - 1
        result = self.analysis.run_analysis(step_idx, on_output=lambda msg: self.console.print(msg), interactive=True)
        
        if result.success:
            self.add_log(f"Analysis '{result.name}' completed", "INFO")
            self.console.print(f"\n[green]✓ {result.name} completed![/]")
        else:
            self.add_log(f"Analysis '{result.name}' failed", "ERROR")
            self.console.print(f"\n[red]✗ {result.name} failed![/]")
        
        input("\n[Press Enter to continue...]")
    
    def show_visualization_menu(self):
        """Display and handle the visualization menu."""
        self.clear_screen()
        self.console.print("[bold cyan]Visualization Tools[/]\n")
        
        options = self.visualization.get_visualization_options()
        
        vmd = options["vmd"]
        xmg = options["xmgrace"]
        
        if vmd["available"] and vmd["has_files"]:
            self.console.print("  [1] Launch VMD (trajectory viewer)")
        else:
            self.console.print(f"  [dim][1] VMD - {'files not found' if vmd['available'] else vmd['message']}[/]")
        
        if xmg["available"]:
            self.console.print("  [2] Launch xmgrace (plot viewer)")
        else:
            self.console.print(f"  [dim][2] xmgrace - {xmg['message']}[/]")
        
        self.console.print("\n  [B] Back")
        
        choice = self.prompt("Select option", choices=["1", "2", "b", "B"], default="b")
        
        if choice.lower() == "b":
            return
        
        if choice == "1":
            success, msg = self.visualization.launch_vmd()
            self.console.print(f"[green]✓ {msg}[/]" if success else f"[red]✗ {msg}[/]")
        elif choice == "2":
            xvg_files = xmg.get("xvg_files", [])
            if xvg_files:
                for i, f in enumerate(xvg_files, 1):
                    self.console.print(f"  [{i}] {f}")
                fc = self.prompt("Select file", choices=[str(i) for i in range(1, len(xvg_files)+1)])
                success, msg = self.visualization.launch_xmgrace(xvg_files[int(fc) - 1])
                self.console.print(f"[green]✓ {msg}[/]" if success else f"[red]✗ {msg}[/]")
        
        input("\n[Press Enter to continue...]")
    
    def show_file_check(self):
        """Display detailed file check."""
        self.clear_screen()
        self.console.print("[bold cyan]Input File Check[/]\n")
        
        found, missing = check_mandatory_files(MANDATORY_FILES, self.working_dir)
        
        for f in found:
            self.console.print(f"  [green]✓[/] {f}")
        for f in missing:
            self.console.print(f"  [red]✗[/] {f}")
        
        self.console.print(f"\n[dim]Directory: {self.working_dir}[/]")
        input("\n[Press Enter to continue...]")
    
    def show_help(self):
        """Display help information."""
        self.clear_screen()
        
        help_text = """
# gmxFlow Help

## Step Locking
Steps must be completed in order. Each step creates a .done flag.
You cannot run Step 5 until Steps 1-4 are complete.

## Interactive Steps
- Step 1 (pdb2gmx): Select force field (use 15 for OPLS-AA)
- Step 6 (make_ndx): Create custom index groups

## Force Field Recommendation
For workshops, use OPLS-AA (option 15 in pdb2gmx).

## Manual Steps
After Step 4, edit topol.top to:
1. Add: #include "ligand.itp"
2. Add ligand to [ molecules ] section

## Keys
[1-9] Run step | [P] Full pipeline | [A] Analysis | [V] Visualization
[F] File check | [R] Reset all flags | [H] Help | [Q] Quit
        """
        
        if RICH_AVAILABLE:
            self.console.print(Panel(Markdown(help_text), title="Help", border_style="cyan"))
        else:
            print(help_text)
        input("\n[Press Enter to continue...]")
    
    def run(self):
        """Main application loop."""
        self.add_log("gmxFlow started" + (" (dry-run mode)" if self.dry_run else ""))
        
        gmx_ok, gmx_msg = check_gromacs_available()
        if not gmx_ok:
            self.add_log(gmx_msg, "WARNING")
        
        while True:
            self.show_main_screen()
            
            choice = self.prompt("\n[bold cyan]Enter choice[/]" if RICH_AVAILABLE else "Enter choice", default="q").strip().lower()
            
            if choice == 'q':
                if self.confirm("Exit gmxFlow?"):
                    print("Goodbye!")
                    break
            
            elif choice in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                self.run_pipeline_step(int(choice))
            
            elif choice == 'p':
                self.run_full_pipeline()
            
            elif choice == 'a':
                self.show_analysis_menu()
            
            elif choice == 'v':
                self.show_visualization_menu()
            
            elif choice == 'f':
                self.show_file_check()
            
            elif choice == 'r':
                if self.confirm("Reset all step completion flags?"):
                    clear_all_flags(self.working_dir)
                    self.pipeline.reset_all()
                    self.add_log("All step flags cleared", "INFO")
            
            elif choice == 'h':
                self.show_help()
            
            else:
                self.add_log(f"Unknown command: {choice}", "WARNING")


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} - {APP_DESCRIPTION}",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--version', '-V', action='version', version=f'{APP_NAME} {APP_VERSION}')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Show commands without executing them')
    
    args = parser.parse_args()
    
    app = GmxFlowApp(dry_run=args.dry_run)
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[Interrupted]")
        sys.exit(0)


if __name__ == "__main__":
    main()
