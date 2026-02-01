#!/usr/bin/env python3
"""
gmxFlow - GROMACS Pipeline Manager
A terminal user interface for running molecular dynamics simulations.

Usage:
    python gmxflow.py [--version] [--help]

Author: gmxFlow Development Team
Version: 1.0.0
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich import box

from config import (
    APP_NAME, APP_VERSION, APP_DESCRIPTION, BANNER,
    PIPELINE_STEPS, ANALYSIS_STEPS, MANDATORY_FILES,
    UI_COLORS, STATUS_SYMBOLS
)
from utils import (
    check_gromacs_available, check_mandatory_files,
    validate_step_ready, format_log_line
)
from pipeline import PipelineExecutor, StepStatus
from analysis import AnalysisRunner
from visualization import VisualizationManager


class GmxFlowApp:
    """Main gmxFlow TUI Application."""
    
    def __init__(self):
        self.console = Console()
        self.working_dir = os.getcwd()
        self.pipeline = PipelineExecutor(self.working_dir)
        self.analysis = AnalysisRunner(self.working_dir)
        self.visualization = VisualizationManager(self.working_dir)
        self.log_messages: list[str] = []
        self.max_log_lines = 15
    
    def add_log(self, message: str, level: str = "INFO"):
        """Add a message to the log."""
        formatted = format_log_line(message, level)
        self.log_messages.append(formatted)
        # Keep only last N messages
        if len(self.log_messages) > self.max_log_lines:
            self.log_messages = self.log_messages[-self.max_log_lines:]
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_banner(self):
        """Display the application banner."""
        banner_text = Text(BANNER, style="bold cyan")
        subtitle = Text(f"{APP_DESCRIPTION} v{APP_VERSION}", style="dim white", justify="center")
        
        self.console.print(Panel(
            banner_text,
            subtitle=f"{APP_DESCRIPTION} v{APP_VERSION}",
            border_style="cyan",
            padding=(0, 2)
        ))
    
    def show_system_status(self):
        """Display system status (GROMACS, files)."""
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        table.add_column("Item", style="white")
        table.add_column("Status", style="white")
        
        # GROMACS check
        gmx_ok, gmx_msg = check_gromacs_available()
        gmx_style = "green" if gmx_ok else "red"
        gmx_symbol = "✓" if gmx_ok else "✗"
        table.add_row("GROMACS", f"[{gmx_style}]{gmx_symbol} {gmx_msg}[/]")
        
        # Working directory
        table.add_row("Working Dir", f"[dim]{self.working_dir}[/]")
        
        # Mandatory files check
        found, missing = check_mandatory_files(MANDATORY_FILES, self.working_dir)
        if missing:
            file_status = f"[yellow]⚠ {len(found)}/{len(MANDATORY_FILES)} files found[/]"
        else:
            file_status = f"[green]✓ All {len(MANDATORY_FILES)} files found[/]"
        table.add_row("Input Files", file_status)
        
        self.console.print(Panel(table, title="System Status", border_style="dim"))
    
    def show_pipeline_menu(self):
        """Display the pipeline steps menu."""
        table = Table(
            show_header=True,
            header_style="bold white",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 1)
        )
        table.add_column("#", justify="center", width=3)
        table.add_column("Step", width=35)
        table.add_column("Status", justify="center", width=12)
        table.add_column("Ready", justify="center", width=8)
        
        for step in PIPELINE_STEPS:
            status = self.pipeline.get_status(step.id)
            
            # Status styling
            if status == StepStatus.PENDING:
                status_text = f"[dim]{STATUS_SYMBOLS['pending']} Pending[/]"
            elif status == StepStatus.RUNNING:
                status_text = f"[yellow]{STATUS_SYMBOLS['running']} Running[/]"
            elif status == StepStatus.COMPLETE:
                status_text = f"[green]{STATUS_SYMBOLS['complete']} Done[/]"
            else:
                status_text = f"[red]{STATUS_SYMBOLS['error']} Error[/]"
            
            # Check if ready
            ready, missing = validate_step_ready(step.id, self.working_dir)
            ready_text = "[green]✓[/]" if ready else f"[red]✗[/]"
            
            # Step number
            step_num = f"[bold cyan]{step.id}[/]"
            
            # Step name with indicators
            step_name = step.name
            if step.user_input_required:
                step_name += " [dim](interactive)[/]"
            if step.manual_intervention:
                step_name += " [yellow]⚠[/]"
            
            table.add_row(step_num, step_name, status_text, ready_text)
        
        self.console.print(Panel(table, title="Pipeline Steps", border_style="cyan"))
    
    def show_quick_actions(self):
        """Display quick action keys."""
        actions = Table(show_header=False, box=None, padding=(0, 2))
        actions.add_column()
        actions.add_column()
        actions.add_column()
        actions.add_column()
        
        actions.add_row(
            "[cyan][1-9][/] Run Step",
            "[cyan][A][/] Analysis",
            "[cyan][V][/] Visualization",
            "[cyan][Q][/] Quit"
        )
        actions.add_row(
            "[cyan][F][/] File Check",
            "[cyan][R][/] Reset Status",
            "[cyan][H][/] Help",
            ""
        )
        
        self.console.print(Panel(actions, border_style="dim"))
    
    def show_log_panel(self):
        """Display the log output panel."""
        if self.log_messages:
            log_text = "\n".join(self.log_messages[-10:])
        else:
            log_text = "[dim]> Ready. Select a step to begin...[/]"
        
        self.console.print(Panel(
            log_text,
            title="Log Output",
            border_style="dim",
            height=12
        ))
    
    def show_main_screen(self):
        """Display the main application screen."""
        self.clear_screen()
        self.show_banner()
        self.show_system_status()
        self.show_pipeline_menu()
        self.show_quick_actions()
        self.show_log_panel()
    
    def run_pipeline_step(self, step_id: int):
        """Execute a pipeline step."""
        step = self.pipeline.get_step(step_id)
        if not step:
            self.add_log(f"Invalid step ID: {step_id}", "ERROR")
            return
        
        # Check prerequisites
        ready, missing = validate_step_ready(step_id, self.working_dir)
        if not missing:
            pass  # Ready to run
        else:
            self.add_log(f"Missing files for step {step_id}: {', '.join(missing)}", "WARNING")
            if not Confirm.ask(f"[yellow]Missing files. Continue anyway?[/]"):
                return
        
        # Show manual intervention warning if applicable
        if step.manual_intervention:
            self.console.print(Panel(
                f"[yellow]⚠ After this step, please manually edit:[/]\n"
                f"  File: [bold]{step.manual_intervention['file']}[/]\n"
                f"  Actions:\n" + "\n".join(f"    • {a}" for a in step.manual_intervention['actions']),
                title="Manual Intervention Required",
                border_style="yellow"
            ))
            if not Confirm.ask("Continue?"):
                return
        
        self.add_log(f"Starting step {step_id}: {step.name}")
        self.console.print(f"\n[bold cyan]>>> Executing Step {step_id}: {step.name}[/]\n")
        self.console.print(f"[dim]Command: {step.command}[/]\n")
        self.console.print("[yellow]" + "─" * 60 + "[/]\n")
        
        # Determine if interactive
        interactive = step.user_input_required or step.id == 6  # pdb2gmx and make_ndx need interaction
        
        # Execute
        result = self.pipeline.execute_step(
            step_id,
            on_output=lambda msg: self.console.print(msg),
            interactive=interactive
        )
        
        self.console.print("\n[yellow]" + "─" * 60 + "[/]")
        
        if result.status == StepStatus.COMPLETE:
            self.add_log(f"Step {step_id} completed successfully", "INFO")
            self.console.print(f"\n[green]✓ Step {step_id} completed successfully![/]")
            if step.produces:
                self.console.print(f"[dim]  Produced: {', '.join(step.produces)}[/]")
        else:
            self.add_log(f"Step {step_id} failed", "ERROR")
            self.console.print(f"\n[red]✗ Step {step_id} failed![/]")
            if result.error_message:
                self.console.print(f"[red]  Error: {result.error_message}[/]")
        
        input("\n[Press Enter to continue...]")
    
    def show_analysis_menu(self):
        """Display and handle the analysis menu."""
        self.clear_screen()
        self.console.print(Panel("[bold cyan]Analysis Tools[/]", border_style="cyan"))
        
        # Check prerequisites
        ready, missing = self.analysis.check_prerequisites()
        if not ready:
            self.console.print(f"[yellow]⚠ Missing files: {', '.join(missing)}[/]")
            self.console.print("[dim]Complete the production MD first.[/]\n")
        
        # Show options
        for i, step in enumerate(ANALYSIS_STEPS, 1):
            self.console.print(f"  [cyan][{i}][/] {step.name}")
            self.console.print(f"      [dim]→ {step.output_file}[/]")
        
        self.console.print(f"\n  [cyan][B][/] Back to main menu")
        
        choice = Prompt.ask("\nSelect analysis", choices=["1", "2", "3", "4", "b", "B"], default="b")
        
        if choice.lower() == "b":
            return
        
        step_idx = int(choice) - 1
        self.console.print(f"\n[bold cyan]>>> Running {ANALYSIS_STEPS[step_idx].name}[/]\n")
        
        result = self.analysis.run_analysis(
            step_idx,
            on_output=lambda msg: self.console.print(msg),
            interactive=True
        )
        
        if result.success:
            self.add_log(f"Analysis '{result.name}' completed", "INFO")
            self.console.print(f"\n[green]✓ {result.name} completed![/]")
            self.console.print(f"[dim]  Output: {result.output_file}[/]")
        else:
            self.add_log(f"Analysis '{result.name}' failed", "ERROR")
            self.console.print(f"\n[red]✗ {result.name} failed![/]")
        
        input("\n[Press Enter to continue...]")
    
    def show_visualization_menu(self):
        """Display and handle the visualization menu."""
        self.clear_screen()
        self.console.print(Panel("[bold cyan]Visualization Tools[/]", border_style="cyan"))
        
        options = self.visualization.get_visualization_options()
        
        # VMD option
        vmd = options["vmd"]
        if vmd["available"]:
            if vmd["has_files"]:
                self.console.print("  [cyan][1][/] Launch VMD (trajectory viewer)")
            else:
                self.console.print("  [dim][1] VMD - trajectory files not found[/]")
        else:
            self.console.print(f"  [dim][1] VMD - {vmd['message']}[/]")
        
        # xmgrace option
        xmg = options["xmgrace"]
        if xmg["available"]:
            self.console.print("  [cyan][2][/] Launch xmgrace (plot viewer)")
            if xmg["xvg_files"]:
                self.console.print(f"      [dim]Available: {', '.join(xmg['xvg_files'][:5])}[/]")
        else:
            self.console.print(f"  [dim][2] xmgrace - {xmg['message']}[/]")
        
        self.console.print(f"\n  [cyan][B][/] Back to main menu")
        
        choice = Prompt.ask("\nSelect option", choices=["1", "2", "b", "B"], default="b")
        
        if choice.lower() == "b":
            return
        
        if choice == "1":
            success, msg = self.visualization.launch_vmd()
            if success:
                self.add_log("VMD launched", "INFO")
                self.console.print(f"[green]✓ {msg}[/]")
            else:
                self.console.print(f"[red]✗ {msg}[/]")
        
        elif choice == "2":
            xvg_files = options["xmgrace"]["xvg_files"]
            if not xvg_files:
                self.console.print("[yellow]No .xvg files found[/]")
            else:
                self.console.print("\nAvailable .xvg files:")
                for i, f in enumerate(xvg_files, 1):
                    self.console.print(f"  [{i}] {f}")
                
                file_choice = Prompt.ask("Select file", choices=[str(i) for i in range(1, len(xvg_files)+1)])
                selected = xvg_files[int(file_choice) - 1]
                
                success, msg = self.visualization.launch_xmgrace(selected)
                if success:
                    self.add_log(f"xmgrace launched with {selected}", "INFO")
                    self.console.print(f"[green]✓ {msg}[/]")
                else:
                    self.console.print(f"[red]✗ {msg}[/]")
        
        input("\n[Press Enter to continue...]")
    
    def show_file_check(self):
        """Display detailed file check."""
        self.clear_screen()
        self.console.print(Panel("[bold cyan]Input File Check[/]", border_style="cyan"))
        
        found, missing = check_mandatory_files(MANDATORY_FILES, self.working_dir)
        
        table = Table(show_header=True, header_style="bold")
        table.add_column("File", width=25)
        table.add_column("Status", justify="center", width=10)
        
        for f in found:
            table.add_row(f, "[green]✓ Found[/]")
        for f in missing:
            table.add_row(f, "[red]✗ Missing[/]")
        
        self.console.print(table)
        self.console.print(f"\n[dim]Directory: {self.working_dir}[/]")
        
        input("\n[Press Enter to continue...]")
    
    def show_help(self):
        """Display help information."""
        self.clear_screen()
        
        help_text = """
# gmxFlow Help

## Pipeline Steps
Press **[1-9]** to run the corresponding pipeline step. Steps should generally
be executed in order.

## Interactive Steps
- **Step 1** (pdb2gmx): Requires force field selection
- **Step 6** (make_ndx): Requires index group creation

## Manual Steps
After **Step 4** (solvate), manually edit `topol.top` to:
1. Include `ligand.itp`
2. Add ligand to `[ molecules ]` section

## Analysis
Press **[A]** to access trajectory analysis tools.

## Visualization
Press **[V]** to launch VMD or xmgrace for visualization.

## Other Keys
- **[F]** - Detailed file check
- **[R]** - Reset all step statuses
- **[Q]** - Quit application
        """
        
        self.console.print(Panel(Markdown(help_text), title="Help", border_style="cyan"))
        input("\n[Press Enter to continue...]")
    
    def run(self):
        """Main application loop."""
        self.add_log("gmxFlow started")
        
        # Initial checks
        gmx_ok, gmx_msg = check_gromacs_available()
        if not gmx_ok:
            self.add_log(gmx_msg, "WARNING")
        
        while True:
            self.show_main_screen()
            
            choice = Prompt.ask(
                "\n[bold cyan]Enter choice[/]",
                default="q"
            ).strip().lower()
            
            if choice == 'q':
                if Confirm.ask("[yellow]Exit gmxFlow?[/]"):
                    self.console.print("[dim]Goodbye![/]")
                    break
            
            elif choice in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                self.run_pipeline_step(int(choice))
            
            elif choice == 'a':
                self.show_analysis_menu()
            
            elif choice == 'v':
                self.show_visualization_menu()
            
            elif choice == 'f':
                self.show_file_check()
            
            elif choice == 'r':
                if Confirm.ask("[yellow]Reset all step statuses?[/]"):
                    self.pipeline.reset_all()
                    self.add_log("All step statuses reset", "INFO")
            
            elif choice == 'h':
                self.show_help()
            
            else:
                self.add_log(f"Unknown command: {choice}", "WARNING")


def main():
    """Entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} - {APP_DESCRIPTION}",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--version', '-V',
        action='version',
        version=f'{APP_NAME} {APP_VERSION}'
    )
    
    args = parser.parse_args()
    
    # Run the application
    app = GmxFlowApp()
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[Interrupted]")
        sys.exit(0)


if __name__ == "__main__":
    main()
