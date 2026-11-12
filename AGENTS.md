# AGENTS.md - gmxFlow Development Guide

## Project Overview

gmxFlow is a terminal UI for GROMACS molecular dynamics simulation pipelines, built in Python with the Rich library. Entry point: `gmxflow.py` → `main()`.

## Build / Test / Dev Commands

### Development (Run Locally)
```bash
python gmxflow.py              # Run app interactively
python gmxflow.py --dry-run    # Show commands without executing GROMACS
python gmxflow.py --protein    # Start in protein-only mode
python gmxflow.py --ligand     # Start in protein+ligand mode
python gmxflow.py --version    # Check version
```

### Build Binary (Linux only)
```bash
./build.sh                     # Uses Nuitka to compile to dist/gmflo (~5-10 min)
./dist/gmflo --version         # Test built binary
```

### Install / Uninstall
```bash
./install.sh                   # Install to /usr/local/bin
./uninstall.sh                 # Remove installation
./update.sh                    # Self-update
```

### Testing
There is **no formal test framework** (no pytest, unittest, etc.). Testing is manual:
- Run with `--dry-run` to validate command paths without executing GROMACS
- Test binary with `./dist/gmflo --version`
- Fresh install test: `curl -sSL https://bit.ly/gmxFlow-1 | sudo bash`

To add a single test, create a test file and run: `python -m pytest <test_file>` (pytest not currently installed).

## Code Style & Conventions

### Language & Version
- Python 3.8+ (see `pyproject.toml`: `requires-python = ">=3.8"`)
- No external linter/formatter configured. Follow existing patterns.

### Imports
- Standard library imports first, then third-party, then local
- Group imports with a blank line between groups
- Use explicit imports from modules, not `import *`
- Local module imports: `from config import ...`, `from utils import ...`, etc.
- Third-party (rich) uses try/except fallback pattern for graceful degradation

### Type Hints
- Use type hints on function signatures: `def foo(x: int) -> str:`
- Import from `typing`: `List`, `Optional`, `Dict`, `Tuple`, `Callable`, etc.
- Use built-in generics for newer Python: `list[str]`, `dict[str, Any]` (mixed style in codebase)
- Return types: use `Tuple[bool, str]` for status/message pairs, `Optional[X]` for nullable

### Naming Conventions
- **Modules**: `snake_case.py` (e.g., `pipeline.py`, `license_check.py`)
- **Classes**: `PascalCase` (e.g., `GmxFlowApp`, `PipelineExecutor`, `AnalysisRunner`)
- **Functions/methods**: `snake_case` (e.g., `check_gromacs_available`, `run_pipeline_step`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `APP_NAME`, `PIPELINE_STEPS`, `VALID_KEY_HASHES`)
- **Private helpers**: prefix with `_` (e.g., `_run_captured`, `_update_mode_config`)

### Formatting
- 4-space indentation (no tabs)
- Line length: ~80-100 chars (not strictly enforced)
- Blank lines: 2 between top-level classes/functions, 1 between methods
- Docstrings: triple double-quotes `"""..."""` for modules, classes, and public functions

### Error Handling
- Use `try/except Exception as e:` for broad catches in utility functions
- Return `Tuple[bool, str]` (success, message) instead of raising for expected failures
- Log errors via `self.add_log(message, "ERROR")` in the main app
- Use `sys.exit(1)` for fatal startup failures (e.g., license check)
- Graceful fallback when `rich` is unavailable (`PlainConsole` class)

### Data Structures
- Use `@dataclass` from `dataclasses` for structured data (`PipelineStep`, `AnalysisStep`, `StepResult`)
- Use `Enum` for fixed status values (`StepStatus`)
- Settings stored as `Dict[str, Any]` loaded/saved via JSON (`.gmxflow_settings.json`)

### Module Architecture
| File | Purpose |
|------|---------|
| `gmxflow.py` | Main TUI app, entry point |
| `config.py` | Constants, step definitions, dataclasses |
| `pipeline.py` | GROMACS command execution |
| `analysis.py` | Post-simulation analysis commands |
| `visualization.py` | VMD/xmgrace launchers |
| `utils.py` | File checks, step locking, topology patching |
| `settings.py` | Settings I/O, MDP file generation |
| `license_check.py` | License validation system |

### Key Patterns
- Rich TUI with `PlainConsole` fallback when rich is unavailable
- Step dependency locking via `.step{N}.done` flag files
- `shell=True` subprocess for GROMACS commands (handles `&&` chaining)
- Real-time output capture via threads reading stdout/stderr pipes
- Mode switching: `protein_only` vs `protein_ligand` with separate step/analysis lists

### No Cursor/Copilot rules found in this repository.
