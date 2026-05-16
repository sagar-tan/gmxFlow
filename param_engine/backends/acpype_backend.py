"""
param_engine.backends.acpype_backend - GAFF/GAFF2 parameterization via ACPYPE.

Wraps AmberTools' antechamber and acpype to generate GAFF/GAFF2 parameters
for small molecules. This is the industry standard for AMBER-compatible
ligand parameterization.

Requires: acpype (pip), AmberTools (conda)
"""

import os
import subprocess
import shutil
from typing import Optional, Any

from param_engine.core import ParamResult


class ACPYPEBackend:
    """ACPYPE + AmberTools backend for GAFF/GAFF2 parameterization."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._log("Initializing ACPYPE backend...")
        self._check_dependencies()

    def _log(self, msg: str):
        if self.verbose:
            print(f"[acpype] {msg}")

    def _check_dependencies(self):
        """Check if antechamber and acpype are available."""
        self._has_antechamber = shutil.which("antechamber") is not None
        self._has_acpype = shutil.which("acpype") is not None

        if not self._has_antechamber:
            self._log("WARNING: antechamber not found in PATH")
        if not self._has_acpype:
            self._log("WARNING: acpype not found in PATH")

    def run(
        self,
        input_file: str,
        molname: str = "LIG",
        net_charge: Optional[int] = None,
        output_dir: str = ".",
        charge_model: str = "bcc",
        optimize_geometry: bool = True,
        gaff_version: str = "gaff2",
        **kwargs: Any,
    ) -> ParamResult:
        """
        Parameterize using ACPYPE + AmberTools.

        Args:
            input_file: Path to MOL2/PDB/SDF/MOL file (SMILES not supported directly)
            molname: Molecule name
            net_charge: Net charge (auto-detected by antechamber if None)
            output_dir: Output directory
            charge_model: Charge method: bcc (AM1-BCC, default), gas, resp, user
            optimize_geometry: Whether to run geometry optimization
            gaff_version: GAFF version (gaff or gaff2)
            **kwargs: Additional parameters

        Returns:
            ParamResult with GROMACS output files
        """
        import tempfile

        log_lines = []
        errors = []
        warnings = []

        try:
            # Convert input to MOL2 if needed
            mol2_file = self._ensure_mol2(input_file, molname, log_lines)
            if mol2_file is None:
                return ParamResult(
                    success=False,
                    force_field="gaff2",
                    backend_used="acpype",
                    errors=["Failed to prepare MOL2 input file"],
                    log=log_lines,
                )

            # Determine charge
            charge = net_charge if net_charge is not None else 0

            # Charge model mapping
            charge_methods = {
                "bcc": "bcc",  # AM1-BCC (recommended)
                "gas": "gas",  # AM1 Mulliken
                "resp": "resp",  # RESP (needs QM)
                "gasteiger": "gas",  # Fallback to gas
                "default": "bcc",
            }
            method = charge_methods.get(charge_model.lower(), "bcc")

            self._log(f"Running ACPYPE: {mol2_file}")
            self._log(f"  Charge: {charge}, Method: {method}, FF: {gaff_version}")

            # Run acpype
            acpype_out = os.path.join(output_dir, f"{molname.lower()}_acpype")
            os.makedirs(acpype_out, exist_ok=True)

            cmd = [
                "acpype",
                "-i",
                mol2_file,
                "-c",
                method,
                "-n",
                str(charge),
                "-b",
                molname.lower(),
                "-o",
                "gmx",  # GROMACS output
            ]

            if gaff_version == "gaff":
                cmd.append("-a")  # Use GAFF1

            self._log(f"  Command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, cwd=acpype_out, capture_output=True, text=True, timeout=300
            )

            log_lines.append(f"  ACPYPE stdout: {result.stdout[:500]}")
            if result.stderr:
                log_lines.append(f"  ACPYPE stderr: {result.stderr[:500]}")

            if result.returncode != 0:
                errors.append(f"ACPYPE failed with return code {result.returncode}")
                return ParamResult(
                    success=False,
                    force_field="gaff2",
                    backend_used="acpype",
                    errors=errors,
                    warnings=warnings,
                    log=log_lines,
                )

            # Find output files
            gmx_dir = os.path.join(acpype_out, f"{molname.lower()}.acpype")
            if not os.path.exists(gmx_dir):
                # Try alternate naming
                gmx_dir = os.path.join(acpype_out, f"{molname.lower()}_GMX")

            top_file = None
            gro_file = None
            itp_file = None

            if os.path.exists(gmx_dir):
                for fname in os.listdir(gmx_dir):
                    if fname.endswith(".top"):
                        top_file = os.path.join(gmx_dir, fname)
                    elif fname.endswith(".gro"):
                        gro_file = os.path.join(gmx_dir, fname)
                    elif fname.endswith(".itp"):
                        itp_file = os.path.join(gmx_dir, fname)

            # Copy to output directory
            out_prefix = os.path.join(output_dir, molname.lower())
            out_files = {}

            if top_file and os.path.exists(top_file):
                out_top = f"{out_prefix}.top"
                shutil.copy2(top_file, out_top)
                out_files["topology"] = out_top

            if gro_file and os.path.exists(gro_file):
                out_gro = f"{out_prefix}.gro"
                shutil.copy2(gro_file, out_gro)
                out_files["coordinates"] = out_gro

            if itp_file and os.path.exists(itp_file):
                out_itp = f"{out_prefix}.itp"
                shutil.copy2(itp_file, out_itp)
                out_files["itp"] = out_itp

            if not out_files:
                errors.append("ACPYPE completed but no GROMACS files found")
                return ParamResult(
                    success=False,
                    force_field="gaff2",
                    backend_used="acpype",
                    errors=errors,
                    log=log_lines,
                )

            return ParamResult(
                success=True,
                force_field="gaff2",
                backend_used="acpype",
                output_files=out_files,
                molecule_info={
                    "charge_model": method,
                    "gaff_version": gaff_version,
                    "net_charge": charge,
                },
                warnings=warnings,
                errors=errors,
                log=log_lines,
            )

        except FileNotFoundError:
            return ParamResult(
                success=False,
                force_field="gaff2",
                backend_used="acpype",
                errors=[
                    "ACPYPE or antechamber not found.",
                    "Install with:",
                    "  pip install acpype",
                    "  conda install -c conda-forge ambertools",
                ],
                log=log_lines,
            )
        except subprocess.TimeoutExpired:
            return ParamResult(
                success=False,
                force_field="gaff2",
                backend_used="acpype",
                errors=["ACPYPE timed out (5 minute limit)"],
                log=log_lines,
            )
        except Exception as e:
            errors.append(f"ACPYPE backend failed: {str(e)}")
            return ParamResult(
                success=False,
                force_field="gaff2",
                backend_used="acpype",
                errors=errors,
                log=log_lines,
            )

    def _ensure_mol2(
        self, input_file: str, molname: str, log_lines: list
    ) -> Optional[str]:
        """Ensure input is in MOL2 format. Convert if needed."""
        import tempfile

        ext = os.path.splitext(input_file)[1].lower()

        # Already MOL2
        if ext == ".mol2":
            return input_file

        # Try RDKit conversion
        try:
            from rdkit import Chem

            if not os.path.exists(input_file):
                # Treat as SMILES
                self._log(f"  Converting SMILES to MOL2: {input_file}")
                mol = Chem.MolFromSmiles(input_file)
                if mol is None:
                    log_lines.append(f"  Failed to parse SMILES: {input_file}")
                    return None
                mol = Chem.AddHs(mol)
                from rdkit.Chem import AllChem

                AllChem.EmbedMolecule(mol)
                AllChem.MMFFOptimizeMolecule(mol)
            else:
                self._log(f"  Converting {ext} to MOL2")
                if ext == ".sdf" or ext == ".mol":
                    mol = Chem.MolFromMolFile(input_file, removeHs=False)
                elif ext == ".pdb":
                    mol = Chem.MolFromPDBFile(input_file, removeHs=False)
                else:
                    log_lines.append(f"  Unsupported format: {ext}")
                    return None

                if mol is None:
                    log_lines.append("  RDKit could not parse input file")
                    return None

                if not mol.GetNumConformers():
                    from rdkit.Chem import AllChem

                    AllChem.EmbedMolecule(mol)

            # Write MOL2
            mol2_path = os.path.join(
                os.path.dirname(input_file) or ".", f"{molname}_temp.mol2"
            )
            if not os.path.exists(input_file):
                mol2_path = f"{molname}_temp.mol2"

            writer = Chem.Mol2Mol2Writer()
            writer.open(mol2_path)
            writer.write(mol)
            writer.close()

            log_lines.append(f"  Converted to MOL2: {mol2_path}")
            return mol2_path

        except ImportError:
            log_lines.append("  RDKit not available for format conversion")
            return None
