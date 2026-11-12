#!/usr/bin/env python3
"""
gmxFlow - GROMACS Pipeline Manager
A terminal user interface for running molecular dynamics simulations.

Usage:
    gmxflow [--version] [--help] [--dry-run] [--protein] [--ligand]

Author: gmxFlow Development Team
Version: 2026.0.3
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
    APP_NAME,
    APP_VERSION,
    APP_DESCRIPTION,
    BANNER,
    PIPELINE_STEPS,
    ANALYSIS_STEPS,
    MANDATORY_FILES,
    PROTEIN_PIPELINE_STEPS,
    PROTEIN_ANALYSIS_STEPS,
    PROTEIN_MANDATORY_FILES,
    STATUS_SYMBOLS,
)
from utils import (
    check_gromacs_available,
    check_mandatory_files,
    validate_step_ready,
    format_log_line,
    check_step_dependencies,
    is_step_complete,
    mark_step_complete,
    clear_all_flags,
    check_output_exists,
    STEP_NAMES,
    patch_topology_for_ligand,
    bypass_step_flag,
    get_step_flags_status,
    detect_ligand_forcefield,
    get_gmx_forcefield_map,
    find_best_ff_index,
    purge_simulation_files,
    ErrorAnalyzer,
)
from settings import (
    load_settings,
    save_settings,
    DEFAULT_SETTINGS,
    generate_all_mdp_files,
    get_md_steps,
)
from pipeline import PipelineExecutor, StepStatus
from analysis import AnalysisRunner
from visualization import VisualizationManager
from license_check import check_license


class PlainConsole:
    """Fallback console when rich is not available."""

    def print(self, text, **kwargs):
        import re

        clean = re.sub(r"\[/?[^\]]+\]", "", str(text))
        print(clean)


class GmxFlowApp:
    """Main gmxFlow TUI Application."""

    def __init__(self, dry_run: bool = False, mode: str = None):
        self.console = Console() if RICH_AVAILABLE else PlainConsole()
        self.working_dir = os.getcwd()
        self.log_messages: list = []
        self.max_log_lines = 15
        self.dry_run = dry_run

        # Load settings
        self.settings = load_settings(self.working_dir)

        # Simulation mode (protein_only or protein_ligand)
        if mode:
            self.mode = mode
        else:
            self.mode = self.settings.get("simulation_mode", "protein_only")

        # Set pipeline based on mode
        self._update_mode_config()

        # Initialize components
        self.pipeline = PipelineExecutor(self.working_dir, self.current_steps)
        self.analysis = AnalysisRunner(self.working_dir, self.current_analysis)
        self.visualization = VisualizationManager(self.working_dir)

    def _update_mode_config(self):
        """Update pipeline config based on mode."""
        if self.mode == "protein_ligand":
            self.current_steps = PIPELINE_STEPS
            self.current_analysis = ANALYSIS_STEPS
            self.current_files = MANDATORY_FILES
            self.mode_name = "Protein + Ligand"
        else:
            self.current_steps = PROTEIN_PIPELINE_STEPS
            self.current_analysis = PROTEIN_ANALYSIS_STEPS
            self.current_files = PROTEIN_MANDATORY_FILES
            self.mode_name = "Protein Only"

    def add_log(self, message: str, level: str = "INFO"):
        """Add a message to the log."""
        formatted = format_log_line(message, level)
        self.log_messages.append(formatted)
        if len(self.log_messages) > self.max_log_lines:
            self.log_messages = self.log_messages[-self.max_log_lines :]

    def clear_screen(self):
        """Clear the terminal screen."""
        os.system("cls" if os.name == "nt" else "clear")

    def print_separator(self):
        """Print a visual separator instead of clearing."""
        print("\n" + "=" * 60 + "\n")

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
            return input().strip().lower() in ["y", "yes"]

    def show_mode_selection(self) -> str:
        """Display mode selection screen on startup."""
        self.clear_screen()

        if RICH_AVAILABLE:
            banner_text = Text(BANNER, style="bold cyan")
            self.console.print(
                Panel(
                    banner_text,
                    subtitle=f"{APP_DESCRIPTION} v{APP_VERSION}",
                    border_style="cyan",
                    padding=(0, 2),
                )
            )

            self.console.print("\n[bold white]Select Simulation Type:[/]\n")
            self.console.print("  [bold cyan][1][/] Protein Only")
            self.console.print("      [dim]Single protein in water with ions[/]")
            self.console.print("  [bold cyan][2][/] Protein + Ligand")
            self.console.print("      [dim]Protein-ligand complex simulation[/]")
            self.console.print()
        else:
            print(BANNER)
            print(f"\n{APP_DESCRIPTION} v{APP_VERSION}\n")
            print("Select Simulation Type:")
            print("  [1] Protein Only")
            print("  [2] Protein + Ligand")
            print()

        choice = self.prompt("Enter choice", choices=["1", "2"], default="1")

        if choice == "2":
            return "protein_ligand"
        return "protein_only"

    def show_banner(self):
        """Display the application banner."""
        if RICH_AVAILABLE:
            banner_text = Text(BANNER, style="bold cyan")
            mode_text = f" [{self.mode_name}]"
            if self.dry_run:
                mode_text += " [DRY-RUN]"
            self.console.print(
                Panel(
                    banner_text,
                    subtitle=f"{APP_DESCRIPTION} v{APP_VERSION}{mode_text}",
                    border_style="cyan",
                    padding=(0, 2),
                )
            )
        else:
            print(BANNER)
            mode_text = f" [{self.mode_name}]" + (" [DRY-RUN]" if self.dry_run else "")
            print(f"  {APP_DESCRIPTION} v{APP_VERSION}{mode_text}")
            print("=" * 60)

    def show_system_status(self):
        """Display system status (GROMACS, files)."""
        if RICH_AVAILABLE:
            table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
            table.add_column("Item", style="white")
            table.add_column("Status", style="white")

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

        found, missing = check_mandatory_files(self.current_files, self.working_dir)

        if RICH_AVAILABLE:
            if missing:
                file_status = (
                    f"[yellow]⚠ {len(found)}/{len(self.current_files)} files found[/]"
                )
            else:
                file_status = f"[green]✓ All {len(self.current_files)} files found[/]"
            table.add_row("Input Files", file_status)

            # Show MD settings
            md_ns = self.settings.get("md_length_ns", 1)
            table.add_row(
                "MD Length",
                f"[dim]{md_ns} ns ({get_md_steps(self.settings):,} steps)[/]",
            )

            self.console.print(Panel(table, title="System Status", border_style="dim"))
        else:
            status = f"{len(found)}/{len(self.current_files)} files found"
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
                padding=(0, 1),
            )
            table.add_column("#", justify="center", width=3)
            table.add_column("Step", width=35)
            table.add_column("Locked", justify="center", width=10)
            table.add_column("Status", justify="center", width=12)
        else:
            print("Pipeline Steps:")
            print("-" * 60)

        for step in self.current_steps:
            can_run, missing_deps = check_step_dependencies(step.id, self.working_dir)
            done = is_step_complete(step.id, self.working_dir)

            if RICH_AVAILABLE:
                if not can_run:
                    dep_names = [f"Step {d}" for d in missing_deps]
                    lock_text = f"[red]🔒 Need {', '.join(dep_names)}[/]"
                else:
                    lock_text = "[green]✓ Ready[/]"

                if done:
                    status_text = f"[green]{STATUS_SYMBOLS['complete']} Complete[/]"
                else:
                    status_text = f"[dim]{STATUS_SYMBOLS['pending']} Pending[/]"

                step_num = f"[bold cyan]{step.id}[/]"
                step_name = step.name
                if step.user_input_required:
                    step_name += " [dim](interactive)[/]"
                step_name += " [dim](editable)[/]"

                table.add_row(step_num, step_name, lock_text, status_text)
            else:
                lock = "LOCKED" if not can_run else "READY"
                status = "DONE" if done else "PENDING"
                print(f"  [{step.id}] {step.name} - {lock} - {status} [editable]")

        if RICH_AVAILABLE:
            self.console.print(
                Panel(
                    table,
                    title=f"Pipeline Steps ({self.mode_name})",
                    border_style="cyan",
                )
            )
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
                "[cyan][Q][/] Quit",
            )
            actions.add_row(
                "[cyan][S][/] Settings",
                "[cyan][M][/] Switch Mode",
                "[cyan][V][/] Visualize",
                "[cyan][R][/] Reset All",
            )
            actions.add_row(
                "[cyan][F][/] Bypass Flags",
                "[cyan][D][/] Deep Clean",
                "",
                ""
            )
            self.console.print(Panel(actions, border_style="dim"))
        else:
            print(
                "Actions: [1-9] Run Step | [A] Analysis | [P] Full Pipeline | [Q] Quit"
            )
            print("         [S] Settings | [M] Switch Mode | [V] Visualize | [R] Reset")
            print("         [F] Bypass Flags | [D] Deep Clean")
            print()

    def show_log_panel(self):
        """Display the log output panel."""
        if self.log_messages:
            log_text = "\n".join(self.log_messages[-10:])
        else:
            log_text = (
                "> Ready. Select a step to begin..."
                if not RICH_AVAILABLE
                else "[dim]> Ready. Select a step to begin...[/]"
            )

        if RICH_AVAILABLE:
            self.console.print(
                Panel(log_text, title="Log Output", border_style="dim", height=12)
            )
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

    def show_settings_menu(self):
        """Display and handle the settings menu."""
        while True:
            self.print_separator()
            self.console.print("[bold cyan]Simulation Settings[/]\n")

            md_steps = get_md_steps(self.settings)

            self.console.print(
                f"  [1] MD Length:      [bold]{self.settings['md_length_ns']} ns[/] ({md_steps:,} steps)"
            )
            self.console.print(
                f"  [2] NVT Steps:      [bold]{self.settings['nvt_steps']:,}[/]"
            )
            self.console.print(
                f"  [3] NPT Steps:      [bold]{self.settings['npt_steps']:,}[/]"
            )
            self.console.print(
                f"  [4] Temperature:    [bold]{self.settings['temperature_k']} K[/]"
            )
            self.console.print(
                f"  [5] Timestep:       [bold]{self.settings['dt_ps']} ps[/]"
            )
            self.console.print()
            self.console.print("  [G] Generate MDP Files")
            self.console.print("  [R] Reset to Defaults")
            self.console.print("  [B] Back to Main Menu")

            choice = self.prompt("\nSelect option", default="b").lower()

            if choice == "b":
                save_settings(self.settings, self.working_dir)
                break
            elif choice == "1":
                val = self.prompt(
                    "MD Length (ns)", default=str(self.settings["md_length_ns"])
                )
                try:
                    self.settings["md_length_ns"] = float(val)
                    self.add_log(f"MD length set to {val} ns", "INFO")
                except ValueError:
                    self.add_log("Invalid value", "ERROR")
            elif choice == "2":
                val = self.prompt("NVT Steps", default=str(self.settings["nvt_steps"]))
                try:
                    self.settings["nvt_steps"] = int(val)
                except ValueError:
                    self.add_log("Invalid value", "ERROR")
            elif choice == "3":
                val = self.prompt("NPT Steps", default=str(self.settings["npt_steps"]))
                try:
                    self.settings["npt_steps"] = int(val)
                except ValueError:
                    self.add_log("Invalid value", "ERROR")
            elif choice == "4":
                val = self.prompt(
                    "Temperature (K)", default=str(self.settings["temperature_k"])
                )
                try:
                    self.settings["temperature_k"] = float(val)
                except ValueError:
                    self.add_log("Invalid value", "ERROR")
            elif choice == "5":
                val = self.prompt("Timestep (ps)", default=str(self.settings["dt_ps"]))
                try:
                    self.settings["dt_ps"] = float(val)
                except ValueError:
                    self.add_log("Invalid value", "ERROR")
            elif choice == "g":
                self._generate_mdp_files()
            elif choice == "r":
                self.settings = DEFAULT_SETTINGS.copy()
                self.add_log("Settings reset to defaults", "INFO")

    def _generate_mdp_files(self):
        """Generate all MDP files based on current settings."""
        self.console.print("\n[cyan]Generating MDP files...[/]")
        results = generate_all_mdp_files(self.settings, self.working_dir)

        for filename, success in results.items():
            if success:
                self.console.print(f"  [green]✓[/] {filename}")
            else:
                self.console.print(f"  [red]✗[/] {filename}")

        self.add_log("Generated MDP files", "INFO")
        input("\n[Press Enter to continue...]")

    def _get_dynamic_ff_index(self) -> str:
        """Automatically detect the best force field index."""
        self.console.print("\n[cyan]🔍 Smart Force Field Detection...[/]")

        # 1. Detect required FF from ligand.itp
        ligand_itp = os.path.join(self.working_dir, "ligand.itp")
        detected_ff = "OPLS"  # Default
        if os.path.exists(ligand_itp):
            detected_ff = detect_ligand_forcefield(ligand_itp)
            self.console.print(f"  • Detected ligand format: [bold]{detected_ff}[/]")
        else:
            self.console.print("  • No ligand.itp found, defaulting to OPLS-AA")

        # 2. Get system FF map
        self.console.print("  • Querying GROMACS force field list...")
        ff_map = get_gmx_forcefield_map()

        # 3. Find the index
        idx = find_best_ff_index(detected_ff, ff_map)
        if idx is not None:
            self.console.print(
                f"  • Found [bold]{detected_ff}[/] at index [bold]{idx}[/] on this system."
            )
            return str(idx)
        else:
            self.console.print(
                f"  • [yellow]Warning: Could not find {detected_ff} in GROMACS list.[/]"
            )
            return "15"  # Fallback

    def _offer_post_step_viz(self, step_id: int):
        """Offer visualization options after certain steps complete."""
        import os

        # Mode-specific step mapping
        if self.mode == "protein_ligand":
            em_step = 6
            nvt_step = 8
            npt_step = 9
            md_step = 10
        else:
            em_step = 6
            nvt_step = 7
            npt_step = 8
            md_step = 9

        # Energy Minimization - offer potential energy plot
        if step_id == em_step:
            em_edr = os.path.join(self.working_dir, "em.edr")
            if os.path.exists(em_edr):
                self.console.print("\n[cyan]📊 Visualization available:[/]")
                self.console.print(
                    "   Extract potential energy: [dim]gmx energy -f em.edr -o potential.xvg[/]"
                )
                if self.confirm("Extract potential energy now?"):
                    os.system(
                        f"cd {self.working_dir} && echo '10\n0' | gmx energy -f em.edr -o potential.xvg"
                    )
                    pot_file = os.path.join(self.working_dir, "potential.xvg")
                    if os.path.exists(pot_file):
                        self.console.print("[green]✓ Created potential.xvg[/]")
                        self.add_log("Created potential.xvg", "INFO")

        # NVT/NPT - offer temperature/pressure plots
        if step_id == nvt_step:
            nvt_edr = os.path.join(self.working_dir, "nvt.edr")
            if os.path.exists(nvt_edr):
                self.console.print(
                    "\n[cyan]📊 Available:[/] Temperature plot (temperature.xvg)"
                )
                if self.confirm("Extract temperature?"):
                    os.system(
                        f"cd {self.working_dir} && echo '16\n0' | gmx energy -f nvt.edr -o temperature.xvg"
                    )
                    if os.path.exists(
                        os.path.join(self.working_dir, "temperature.xvg")
                    ):
                        self.console.print("[green]✓ Created temperature.xvg[/]")

        if step_id == npt_step:
            npt_edr = os.path.join(self.working_dir, "npt.edr")
            if os.path.exists(npt_edr):
                self.console.print("\n[cyan]📊 Available:[/] Pressure/Density plots")
                if self.confirm("Extract pressure and density?"):
                    os.system(
                        f"cd {self.working_dir} && echo '18\n0' | gmx energy -f npt.edr -o pressure.xvg"
                    )
                    os.system(
                        f"cd {self.working_dir} && echo '24\n0' | gmx energy -f npt.edr -o density.xvg"
                    )
                    self.console.print(
                        "[green]✓ Created pressure.xvg and density.xvg[/]"
                    )

        # Production MD - offer VMD launch
        if step_id == md_step:
            md_xtc = os.path.join(self.working_dir, "md.xtc")
            md_gro = os.path.join(self.working_dir, "md.gro")
            if os.path.exists(md_xtc) and os.path.exists(md_gro):
                self.console.print("\n[cyan]🎬 Trajectory viewer available![/]")
                self.console.print("   Launch VMD: [dim]vmd md.gro md.xtc[/]")
                if self.confirm("Launch VMD now?"):
                    result = os.system(f"cd {self.working_dir} && vmd md.gro md.xtc &")
                    if result == 0:
                        self.console.print("[green]✓ VMD launched[/]")
                    else:
                        self.console.print(
                            "[yellow]VMD not available or failed to launch[/]"
                        )

    def run_pipeline_step(self, step_id: int):
        """Execute a pipeline step with locking and resume detection."""
        step = self.pipeline.get_step(step_id)
        if not step:
            self.add_log(f"Invalid step ID: {step_id}", "ERROR")
            return False

        # Check dependencies
        can_run, missing_deps = check_step_dependencies(step_id, self.working_dir)
        if not can_run:
            dep_names = [
                f"Step {d} ({STEP_NAMES.get(d, 'Unknown')})" for d in missing_deps
            ]
            self.console.print(
                f"[red]✗ BLOCKED: Step {step_id} requires completion of:[/]"
            )
            for name in dep_names:
                self.console.print(f"[red]  • {name}[/]")
            self.add_log(f"Step {step_id} blocked - dependencies not met", "ERROR")
            input("\n[Press Enter to continue...]")
            return False

        # Resume detection
        outputs_exist, existing_files = check_output_exists(step_id, self.working_dir)
        if outputs_exist:
            self.console.print(
                f"[yellow]⚠ Output files already exist: {', '.join(existing_files)}[/]"
            )
            if not self.confirm("Overwrite existing files?"):
                self.add_log(
                    f"Step {step_id} cancelled - user declined overwrite", "INFO"
                )
                return False

        # Dry run
        if self.dry_run:
            self.console.print(
                f"\n[bold yellow]DRY-RUN: Would execute Step {step_id}: {step.name}[/]"
            )
            self.console.print(f"[dim]Command: {step.command}[/]")
            if step.produces:
                self.console.print(f"[dim]Would produce: {', '.join(step.produces)}[/]")
            self.add_log(f"DRY-RUN: Step {step_id} command shown", "INFO")
            input("\n[Press Enter to continue...]")
            return True

        # Command editing - let user modify before running
        self.console.print(f"\n[bold cyan]>>> Step {step_id}: {step.name}[/]")
        self.console.print(f"[dim]Command: {step.command}[/]")

        if self.confirm("\nEdit command before running?"):
            self.console.print(
                "\n[cyan]Enter new command (leave empty to keep original):[/]"
            )
            self.console.print(f"[dim](Current: {step.command})[/]\n")
            new_command = self.prompt("New command", default="").strip()
            if new_command:
                self.console.print(f"[green]Using edited command: {new_command}[/]")
            else:
                new_command = step.command
                self.console.print("[dim]Using original command[/]")
        else:
            new_command = step.command

        # Dynamic Force Field Injection for Step 1 (ligand) or Step 2 (protein)
        is_ff_step = (self.mode == "protein_ligand" and step_id == 1) or (
            self.mode == "protein_only" and step_id == 2
        )

        if is_ff_step and "pdb2gmx" in new_command and "echo" not in new_command:
            ff_idx = self._get_dynamic_ff_index()
            new_command = f"echo '{ff_idx}' | {new_command}"
            self.console.print(f"[green]Smart-selected force field index: {ff_idx}[/]")

        self.add_log(f"Starting step {step_id}: {step.name}")
        self.console.print(f"\n[bold cyan]>>> Executing Step {step_id}: {step.name}[/]")
        self.console.print("[yellow]" + "─" * 60 + "[/]\n")

        interactive = step.user_input_required
        result = self.pipeline.execute_step(
            step_id,
            on_output=lambda msg: self.console.print(msg),
            interactive=interactive,
            command_override=new_command if new_command != step.command else None,
        )

        self.console.print("\n[yellow]" + "─" * 60 + "[/]")

        if result.status == StepStatus.COMPLETE:
            mark_step_complete(step_id, self.working_dir)
            self.add_log(f"Step {step_id} completed successfully", "INFO")
            self.console.print(f"\n[green]✓ Step {step_id} completed successfully![/]")
            if step.produces:
                self.console.print(f"[dim]  Produced: {', '.join(step.produces)}[/]")

            # Auto-patch topology after Step 4 (ligand mode only)
            if step_id == 4 and self.mode == "protein_ligand":
                self.console.print(
                    "\n[cyan]>>> Auto-patching topol.top with ligand...[/]"
                )
                success, msg = patch_topology_for_ligand(
                    "topol.top", "ligand.itp", directory=self.working_dir
                )
                if success:
                    self.console.print(f"[green]✓ {msg}[/]")
                    self.add_log(msg, "INFO")
                else:
                    self.console.print(f"[red]✗ {msg}[/]")
                    self.add_log(msg, "WARNING")

            # Post-step visualization prompts
            self._offer_post_step_viz(step_id)

            input("\n[Press Enter to continue...]")
            return True
        else:
            self.add_log(f"Step {step_id} failed", "ERROR")
            self.console.print(f"\n[bold red]✗ Step {step_id} failed![/]")
            
            # Smart Error Analysis
            combined_output = result.stdout + "\n" + result.stderr
            suggestions = ErrorAnalyzer.analyze(combined_output)
            
            if suggestions:
                self.console.print("\n[bold yellow]🔍 gmxFlow Auto-Analysis:[/]")
                for sugg in suggestions:
                    self.console.print(f"  [bold cyan]Diagnosis:[/] {sugg['diagnosis']}")
                    self.console.print(f"  [bold green]Suggested Fix:[/] {sugg['fix']}\n")
                self.add_log(f"Detected {len(suggestions)} known issues", "WARNING")
            
            if result.error_message:
                self.console.print(f"[red]  Internal Error: {result.error_message}[/]")
            input("\n[Press Enter to continue...]")
            return False

    def run_full_pipeline(self):
        """Run all pipeline steps in sequence."""
        self.print_separator()
        self.console.print(
            f"[bold cyan]>>> Full Pipeline Execution ({self.mode_name})[/]"
        )

        if self.dry_run:
            self.console.print(
                "[bold yellow]DRY-RUN MODE: Showing all commands without execution[/]\n"
            )
        else:
            # Collect required inputs upfront
            self.console.print("\n[bold]Pre-Run Configuration[/]")
            self.console.print(
                "[dim]Answer these questions now, then the pipeline runs hands-off.[/]\n"
            )

            # Force field selection
            self.console.print("[cyan]Available Force Fields:[/]")
            ff_map = get_gmx_forcefield_map()
            for idx, name in sorted(ff_map.items()):
                self.console.print(f"  {idx:2}: {name}")
            
            # Detect recommended
            detected_ff = "OPLS"
            ligand_itp = os.path.join(self.working_dir, "ligand.itp")
            if os.path.exists(ligand_itp):
                detected_ff = detect_ligand_forcefield(ligand_itp)
            
            rec_idx = find_best_ff_index(detected_ff, ff_map)
            default_ff = str(rec_idx) if rec_idx else "15"

            ff_choice = self.prompt(
                f"\nForce field [default={detected_ff} ({default_ff})]", default=default_ff
            )

            if self.mode == "protein_only":
                # Protein-only mode needs ion group (usually SOL = 13)
                ion_group = self.prompt("Ion replacement group [13=SOL]", default="13")
            else:
                ion_group = None

            self.console.print(
                "\n[green]✓ Configuration complete. Starting pipeline...[/]"
            )
            self.console.print("[dim]No further input required until completion.[/]\n")

            # Store inputs for command substitution
            self.pipeline_inputs = {"force_field": ff_choice, "ion_group": ion_group}

        for step in self.current_steps:
            self.console.print(f"\n[bold]Step {step.id}: {step.name}[/]")

            if self.dry_run:
                self.console.print(f"[dim]  Command: {step.command}[/]")
                if step.produces:
                    self.console.print(
                        f"[dim]  Produces: {', '.join(step.produces)}[/]"
                    )
                continue

            if is_step_complete(step.id, self.working_dir):
                self.console.print(f"[green]  ✓ Already complete, skipping[/]")
                continue

            # Run step with pre-collected inputs
            success = self._run_pipeline_step_auto(step)
            if not success:
                self.console.print(f"\n[red]Pipeline halted at step {step.id}[/]")
                break

        if self.dry_run:
            self.console.print(
                "\n[bold yellow]DRY-RUN complete. No commands were executed.[/]"
            )

        input("\n[Press Enter to continue...]")

    def _run_pipeline_step_auto(self, step):
        """Run a pipeline step with pre-collected inputs (no manual intervention)."""
        import re

        # Get the command and substitute inputs
        command = step.command
        inputs = getattr(self, "pipeline_inputs", {})

        # Substitute force field input for pdb2gmx commands
        if "pdb2gmx" in command and "echo" not in command:
            ff = inputs.get("force_field")
            if not ff:
                ff = self._get_dynamic_ff_index()
            command = f"echo '{ff}' | {command}"

        # Substitute ion group for genion commands (protein-only mode)
        if "genion" in command and "echo" not in command and inputs.get("ion_group"):
            ion = inputs["ion_group"]
            # Insert echo before genion in the chained command
            command = command.replace("gmx genion", f"echo '{ion}' | gmx genion")

        self.console.print(f"[dim]>>> {command}[/]")
        self.console.print("[yellow]" + "─" * 60 + "[/]")

        # Execute command
        result = self.pipeline.execute_step(
            step.id,
            on_output=lambda msg: self.console.print(msg),
            interactive=False,
            command_override=command,
        )

        self.console.print("\n[yellow]" + "─" * 60 + "[/]")

        if result.status == StepStatus.COMPLETE:
            mark_step_complete(step.id, self.working_dir)
            self.add_log(f"Step {step.id} completed successfully", "INFO")
            self.console.print(f"\n[green]✓ Step {step.id} completed successfully![/]")

            # Auto-patch topology after Step 4 (ligand mode only)
            if step.id == 4 and self.mode == "protein_ligand":
                self.console.print(
                    "\n[cyan]>>> Auto-patching topol.top with ligand...[/]"
                )
                success, msg = patch_topology_for_ligand(
                    "topol.top", "ligand.itp", directory=self.working_dir
                )
                if success:
                    self.console.print(f"[green]✓ {msg}[/]")
                else:
                    self.console.print(f"[red]✗ {msg}[/]")

            return True
        else:
            self.add_log(f"Step {step.id} failed", "ERROR")
            self.console.print(f"\n[red]✗ Step {step.id} failed![/]")
            if result.error_message:
                self.console.print(f"[red]  Error: {result.error_message}[/]")
            return False

    def show_analysis_menu(self):
        """Display and handle the analysis menu."""
        while True:
            self.print_separator()
            self.console.print("[bold cyan]Analysis Tools[/]\n")

            if not is_step_complete(10, self.working_dir):
                self.console.print("[yellow]⚠ Production MD (Step 10) not complete.[/]")
                self.console.print(
                    "[dim]Analysis may fail without MD output files.[/]\n"
                )

            for i, step in enumerate(self.current_analysis, 1):
                self.console.print(f"  [{i}] {step.name}")
                self.console.print(f"      [dim]→ {step.output_file}[/]")

            self.console.print(f"\n  [V] Launch VMD (Trajectory Viewer)")
            self.console.print(f"  [B] Back to main menu")

            choices = [str(i) for i in range(1, len(self.current_analysis) + 1)] + [
                "v",
                "V",
                "b",
                "B",
            ]
            choice = self.prompt("\nSelect analysis", choices=choices, default="b")

            if choice.lower() == "b":
                return

            if choice.lower() == "v":
                self._launch_vmd()
                continue

            step_idx = int(choice) - 1
            step = self.current_analysis[step_idx]

            if self.dry_run:
                self.console.print(f"\n[bold yellow]DRY-RUN: Would run {step.name}[/]")
                self.console.print(f"[dim]Command: {step.command}[/]")
                input("\n[Press Enter to continue...]")
                continue

            result = self.analysis.run_analysis(
                step_idx,
                on_output=lambda msg: self.console.print(msg),
                interactive=True,
            )

            if result.success:
                self.add_log(f"Analysis '{result.name}' completed", "INFO")
                self.console.print(f"\n[green]✓ {result.name} completed![/]")
            else:
                self.add_log(f"Analysis '{result.name}' failed", "ERROR")
                self.console.print(f"\n[red]✗ {result.name} failed![/]")

            input("\n[Press Enter to continue...]")

    def _launch_vmd(self):
        """Launch VMD for trajectory visualization."""
        import os

        md_gro = os.path.join(self.working_dir, "md.gro")
        md_fit = os.path.join(self.working_dir, "md_fit.xtc")
        md_xtc = os.path.join(self.working_dir, "md.xtc")

        # Prefer md_fit.xtc if available, otherwise use md.xtc
        traj_file = md_fit if os.path.exists(md_fit) else md_xtc
        traj_name = "md_fit.xtc" if os.path.exists(md_fit) else "md.xtc"

        if not os.path.exists(md_gro):
            self.console.print("[red]✗ md.gro not found. Run production MD first.[/]")
            input("\n[Press Enter to continue...]")
            return

        if not os.path.exists(traj_file):
            self.console.print(
                "[red]✗ No trajectory file found (md_fit.xtc or md.xtc)[/]"
            )
            input("\n[Press Enter to continue...]")
            return

        success, msg = self.visualization.launch_vmd("md.gro", traj_name)
        if success:
            self.console.print(f"[green]✓ {msg}[/]")
            self.add_log("Launched VMD", "INFO")
        else:
            self.console.print(f"[red]✗ {msg}[/]")
            self.console.print(
                "[dim]Install VMD: https://www.ks.uiuc.edu/Research/vmd/[/]"
            )

        input("\n[Press Enter to continue...]")

    def show_visualization_menu(self):
        """Display and handle the visualization menu."""
        while True:
            self.clear_screen()
            self.console.print("\n[bold cyan]📊 Visualization Menu[/]\n")

            # Get available xvg files
            xvg_files = self.visualization.list_available_xvg_files()

            if not xvg_files:
                self.console.print(
                    "[yellow]No .xvg files found in working directory.[/]"
                )
                self.console.print(
                    "[dim]Run analysis steps first to generate graphs.[/]"
                )
                input("\n[Press Enter to continue...]")
                return

            # List files
            self.console.print("[bold]Available graphs:[/]\n")
            for i, f in enumerate(xvg_files, 1):
                self.console.print(f"  [{i}] {f}")
            self.console.print(f"\n  [0] Back to menu")

            choice = self.prompt("\nSelect graph to view", default="0")

            if choice == "0":
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(xvg_files):
                    selected_file = xvg_files[idx]
                    success, msg = self.visualization.launch_xmgrace(selected_file)
                    if success:
                        self.console.print(f"[green]✓ {msg}[/]")
                        self.add_log(f"Launched xmgrace: {selected_file}", "INFO")
                    else:
                        self.console.print(f"[red]✗ {msg}[/]")
                        self.console.print(
                            "[dim]Install xmgrace: sudo apt install grace[/]"
                        )
                else:
                    self.console.print("[yellow]Invalid selection[/]")
            except ValueError:
                self.console.print("[yellow]Invalid input[/]")

            input("\n[Press Enter to continue...]")

    def show_bypass_flags_menu(self):
        """Display menu to bypass step completion flags."""
        while True:
            self.print_separator()
            self.console.print("[bold cyan]Bypass Step Flags[/]\n")
            self.console.print("[dim]Clear .done flags to re-run completed steps.[/]\n")

            flags_status = get_step_flags_status(self.working_dir)

            for step_id, name, complete in flags_status:
                if complete:
                    status = "[yellow]LOCKED (can bypass)[/]"
                else:
                    status = "[dim]Not completed[/]"
                self.console.print(f"  [{step_id}] {name} - {status}")

            self.console.print(f"\n  [A] Bypass All Flags")
            self.console.print(f"  [B] Back to Main Menu")

            choices = [str(i) for i in range(1, 10)] + ["a", "A", "b", "B"]
            choice = self.prompt(
                "\nSelect step to bypass", choices=choices, default="b"
            )

            if choice.lower() == "b":
                return
            elif choice.lower() == "a":
                if self.confirm(
                    "Clear ALL step flags? This allows re-running the entire pipeline."
                ):
                    clear_all_flags(self.working_dir)
                    self.pipeline.reset_all()
                    self.add_log("All step flags cleared", "INFO")
                    self.console.print("[green]All flags cleared[/]")
                input("\n[Press Enter to continue...]")
            else:
                try:
                    step_id = int(choice)
                    if 1 <= step_id <= 9:
                        success, msg = bypass_step_flag(step_id, self.working_dir)
                        if success:
                            self.add_log(msg, "INFO")
                            self.console.print(f"[green]{msg}[/]")
                        else:
                            self.console.print(f"[yellow]{msg}[/]")
                    else:
                        self.console.print("[yellow]Invalid step ID[/]")
                except ValueError:
                    self.console.print("[yellow]Invalid input[/]")

                input("\n[Press Enter to continue...]")

    def switch_mode(self):
        """Switch between protein-only and protein-ligand modes."""
        self.console.print("\n[bold]Switch Simulation Mode[/]\n")
        self.console.print(f"  Current: [cyan]{self.mode_name}[/]")

        if self.mode == "protein_only":
            new_mode = "protein_ligand"
            new_name = "Protein + Ligand"
        else:
            new_mode = "protein_only"
            new_name = "Protein Only"

        if self.confirm(f"Switch to {new_name}?"):
            self.mode = new_mode
            self._update_mode_config()
            self.settings["simulation_mode"] = new_mode
            save_settings(self.settings, self.working_dir)
            self.pipeline = PipelineExecutor(self.working_dir, self.current_steps)
            self.analysis.set_analysis_steps(self.current_analysis)
            self.add_log(f"Switched to {new_name} mode", "INFO")

    def run(self):
        """Main application loop."""
        self.add_log("gmxFlow started" + (" (dry-run mode)" if self.dry_run else ""))

        gmx_ok, gmx_msg = check_gromacs_available()
        if not gmx_ok:
            self.add_log(gmx_msg, "WARNING")

        while True:
            self.show_main_screen()

            choice = (
                self.prompt(
                    "\n[bold cyan]Enter choice[/]"
                    if RICH_AVAILABLE
                    else "Enter choice",
                    default="q",
                )
                .strip()
                .lower()
            )

            if choice == "q":
                if self.confirm("Exit gmxFlow?"):
                    print("Goodbye!")
                    break

            elif choice in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                self.run_pipeline_step(int(choice))

            elif choice == "p":
                self.run_full_pipeline()

            elif choice == "a":
                self.show_analysis_menu()

            elif choice == "s":
                self.show_settings_menu()

            elif choice == "m":
                self.switch_mode()

            elif choice == "v":
                self.show_visualization_menu()

            elif choice == "g":
                self._generate_mdp_files()

            elif choice == "r":
                if self.confirm("Reset all completion flags? (Doesn't delete files)"):
                    clear_all_flags(self.working_dir)
                    self.pipeline.reset_all()
                    self.add_log("All progress flags reset", "INFO")
            elif choice == "d":
                if self.confirm("[bold red]⚠️ DEEP CLEAN:[/] This will delete all generated simulation files. Proceed?"):
                    count, errors = purge_simulation_files(self.working_dir)
                    clear_all_flags(self.working_dir)
                    self.pipeline.reset_all()
                    self.add_log(f"Deep clean complete: deleted {count} files", "INFO")
                    if errors:
                        for err in errors:
                            self.add_log(err, "WARNING")
                    self.console.print(f"\n[green]✓ Deep Clean finished. Deleted {count} files.[/]")
                    input("\n[Press Enter to continue...]")

            elif choice == "f":
                self.show_bypass_flags_menu()

            else:
                self.add_log(f"Unknown command: {choice}", "WARNING")


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} - {APP_DESCRIPTION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", "-V", action="version", version=f"{APP_NAME} {APP_VERSION}"
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show commands without executing them",
    )
    parser.add_argument(
        "--protein", action="store_true", help="Start in Protein-Only mode"
    )
    parser.add_argument(
        "--ligand", action="store_true", help="Start in Protein+Ligand mode"
    )

    args = parser.parse_args()

    # Determine mode
    mode = None
    if args.protein:
        mode = "protein_only"
    elif args.ligand:
        mode = "protein_ligand"

    # License check
    if not check_license():
        print("\nLicense required. Exiting.")
        sys.exit(1)

    app = GmxFlowApp(dry_run=args.dry_run, mode=mode)

    # If no mode specified via args, show selection
    if mode is None:
        selected_mode = app.show_mode_selection()
        app.mode = selected_mode
        app._update_mode_config()
        app.pipeline = PipelineExecutor(app.working_dir, app.current_steps)

    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[Interrupted]")
        sys.exit(0)


if __name__ == "__main__":
    main()
