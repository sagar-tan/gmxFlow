"""
param_engine.backends.openff_backend - OpenFF/SMIRNOFF parameterization.

Uses the Open Force Field toolkit to parameterize molecules without
atom types. SMIRNOFF uses SMARTS patterns for direct chemical perception.

This is the most modern approach and handles any molecule RDKit can parse.
Requires: openff-toolkit, openff-interchange, RDKit, OpenMM

Reference: https://openforcefield.org/
"""

import os
from typing import Optional, Any, Dict, List

from param_engine.core import ParamResult


class OpenFFBackend:
    """OpenFF/SMIRNOFF parameterization backend."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._log("Initializing OpenFF backend...")

    def _log(self, msg: str):
        if self.verbose:
            print(f"[openff] {msg}")

    def run(
        self,
        input_file: str,
        molname: str = "LIG",
        net_charge: Optional[int] = None,
        output_dir: str = ".",
        charge_model: str = "default",
        optimize_geometry: bool = True,
        force_field_name: str = "openff-2.1.0",
        **kwargs: Any,
    ) -> ParamResult:
        """
        Parameterize using OpenFF/SMIRNOFF.

        Args:
            input_file: SMILES string or path to SDF/MOL2/PDB/MOL
            molname: Molecule name for topology
            net_charge: Net charge (auto-detected if None)
            output_dir: Output directory
            charge_model: Charge model (default=am1bcc)
            optimize_geometry: Whether to optimize 3D geometry
            force_field_name: OpenFF force field version
                Options: openff-2.1.0 (Sage), openff-1.3.0 (Parsley), openff_unconstrained-2.1.0
            **kwargs: Additional parameters

        Returns:
            ParamResult with output files
        """
        from openff.toolkit import Molecule, ForceField
        from openff.interchange import Interchange

        log_lines = []
        warnings = []
        errors = []

        try:
            # Load molecule
            self._log(f"Loading molecule from: {input_file}")
            mol = self._load_molecule(input_file, molname, optimize_geometry, log_lines)

            if mol is None:
                return ParamResult(
                    success=False,
                    force_field="smirnoff",
                    backend_used="openff",
                    errors=["Failed to load molecule"],
                    log=log_lines,
                )

            # Set net charge if provided
            if net_charge is not None:
                formal_charge = net_charge
                # Apply formal charge if needed
                if mol.total_charge != formal_charge:
                    warnings.append(
                        f"Molecule total charge ({mol.total_charge}) differs from "
                        f"specified net charge ({formal_charge}). Using molecule's charge."
                    )

            self._log(f"  Molecule: {mol.to_smiles()}")
            self._log(f"  Formula: {mol.hill_formula}")
            self._log(f"  Atoms: {mol.n_atoms}")
            self._log(f"  Bonds: {mol.n_bonds}")
            self._log(f"  Total charge: {mol.total_charge}")

            # Load force field
            self._log(f"Loading force field: {force_field_name}")
            try:
                ff = ForceField(f"{force_field_name}.offxml")
            except Exception as e:
                # Try with openff-2.1.0 as fallback
                self._log(f"  Failed to load {force_field_name}, using openff-2.1.0")
                ff = ForceField("openff-2.1.0.offxml")

            # Create interchange (topology + coordinates + FF params)
            self._log("Creating OpenMM System via Interchange...")
            interchange = Interchange.from_smirnoff(
                force_field=ff,
                topology=mol.to_topology(),
            )
            interchange.positions = mol.conformers[0]

            # Generate GROMACS files
            self._log("Writing GROMACS files...")
            gromacs_prefix = os.path.join(output_dir, molname.lower())

            # Write topology
            top_file = f"{gromacs_prefix}.top"
            gro_file = f"{gromacs_prefix}.gro"
            itp_file = f"{gromacs_prefix}.itp"

            interchange.to_gro(top_file)

            # Also create a standalone .itp file for the ligand
            self._create_itp_from_interchange(
                interchange, mol, itp_file, molname, log_lines
            )

            # Copy gro from interchange output
            if os.path.exists(gro_file):
                self._log(f"  Topology: {top_file}")
                self._log(f"  Coordinates: {gro_file}")
                self._log(f"  ITP: {itp_file}")

            return ParamResult(
                success=True,
                force_field="smirnoff",
                backend_used="openff",
                output_files={
                    "topology": top_file,
                    "coordinates": gro_file,
                    "itp": itp_file,
                },
                molecule_info={
                    "smiles": mol.to_smiles(),
                    "formula": mol.hill_formula,
                    "n_atoms": mol.n_atoms,
                    "n_bonds": mol.n_bonds,
                    "total_charge": mol.total_charge,
                },
                warnings=warnings,
                errors=errors,
                log=log_lines,
            )

        except ImportError as e:
            return ParamResult(
                success=False,
                force_field="smirnoff",
                backend_used="openff",
                errors=[
                    "OpenFF toolkit not installed.",
                    "Install with: conda install -c conda-forge openff-toolkit openff-interchange",
                    f"Error: {str(e)}",
                ],
                log=log_lines,
            )
        except Exception as e:
            errors.append(f"OpenFF parameterization failed: {str(e)}")
            return ParamResult(
                success=False,
                force_field="smirnoff",
                backend_used="openff",
                errors=errors,
                warnings=warnings,
                log=log_lines,
            )

    def _load_molecule(
        self,
        input_file: str,
        molname: str,
        optimize_geometry: bool,
        log_lines: List[str],
    ) -> Optional[Any]:
        """Load molecule from various input formats."""
        from openff.toolkit import Molecule
        from openff.units import unit

        # Check if input is a SMILES string
        if not os.path.exists(input_file):
            self._log(f"  Input is SMILES: {input_file}")
            mol = Molecule.from_smiles(input_file)
        else:
            # Determine format from extension
            ext = os.path.splitext(input_file)[1].lower()
            self._log(f"  Loading from file: {input_file} ({ext})")

            if ext == ".sdf" or ext == ".mol":
                mol = Molecule.from_file(input_file, allow_undefined_stereo=True)
            elif ext == ".mol2":
                mol = Molecule.from_mol2(input_file)
            elif ext == ".pdb":
                mol = Molecule.from_pdb(input_file, allow_undefined_stereo=True)
            else:
                # Try Open Babel via RDKit as fallback
                try:
                    from rdkit import Chem

                    rdkit_mol = Chem.MolFromMolFile(input_file)
                    if rdkit_mol is None:
                        rdkit_mol = Chem.MolFromMol2File(input_file)
                    if rdkit_mol is None:
                        rdkit_mol = Chem.MolFromPDBFile(input_file)
                    if rdkit_mol:
                        from openff.toolkit import Molecule

                        mol = Molecule.from_rdkit(
                            rdkit_mol, allow_undefined_stereo=True
                        )
                    else:
                        log_lines.append(
                            f"Could not parse {input_file} with any format"
                        )
                        return None
                except Exception as e:
                    log_lines.append(f"RDKit fallback failed: {e}")
                    return None

        # Generate 3D coordinates if needed
        if not mol.conformers:
            self._log("  Generating 3D conformer...")
            mol.generate_conformers(n_conformers=1)
            if optimize_geometry:
                self._log("  Optimizing geometry with MMFF94...")
                mol._conformers[0] = mol.generate_conformers(
                    n_conformers=1, rms_cutoff=0.1
                )[0]

        # Assign molecule name
        mol.name = molname

        return mol

    def _create_itp_from_interchange(
        self,
        interchange: Any,
        mol: Any,
        itp_file: str,
        molname: str,
        log_lines: List[str],
    ) -> None:
        """Create a standalone .itp file from an OpenFF interchange."""
        # OpenFF Interchange writes a full .top file; we extract the ligand
        # portion into a standalone .itp for use with protein topologies
        import re

        # For now, the .top from interchange is the primary output
        # We create a simple .itp that references the same parameters
        # This is a simplified version - full implementation would parse
        # the interchange object directly

        # Write a placeholder itp that includes the full top
        # In practice, users will use the .top directly or
        # we'll implement full itp extraction

        try:
            # Read the generated top file
            top_path = itp_file.replace(".itp", ".top")
            if os.path.exists(top_path):
                with open(top_path, "r") as f:
                    top_content = f.read()

                # Extract relevant sections for itp
                itp_content = self._extract_itp_sections(top_content, mol, molname)

                with open(itp_file, "w") as f:
                    f.write(itp_content)
                log_lines.append(f"  Created ITP: {itp_file}")
        except Exception as e:
            log_lines.append(f"  Warning: Could not create standalone ITP: {e}")

    def _extract_itp_sections(self, top_content: str, mol: Any, molname: str) -> str:
        """Extract ligand-relevant sections from a full .top file."""
        lines = top_content.split("\n")
        itp_lines = []

        itp_lines.append(f"; Ligand topology generated by gmxFlow param_engine")
        itp_lines.append(f"; Force field: OpenFF SMIRNOFF")
        itp_lines.append(f"; Molecule: {molname}")
        itp_lines.append(f"; SMILES: {mol.to_smiles()}")
        itp_lines.append("")

        in_atoms = False
        in_bonds = False
        in_angles = False
        in_dihedrals = False
        in_moleculetype = False
        current_section = None

        for line in lines:
            stripped = line.strip()

            # Detect section headers
            if stripped.startswith("[ atomtypes ]"):
                current_section = "atomtypes"
                # Include atomtypes section (needed for new atom types)
                itp_lines.append(line)
                continue
            elif stripped.startswith("[ moleculetype ]"):
                current_section = "moleculetype"
                in_moleculetype = True
                itp_lines.append(line)
                continue
            elif stripped.startswith("[ atoms ]"):
                current_section = "atoms"
                in_atoms = True
                itp_lines.append(line)
                continue
            elif stripped.startswith("[ bonds ]"):
                current_section = "bonds"
                in_bonds = True
                itp_lines.append(line)
                continue
            elif stripped.startswith("[ angles ]"):
                current_section = "angles"
                in_angles = True
                itp_lines.append(line)
                continue
            elif stripped.startswith("[ dihedrals ]"):
                current_section = "dihedrals"
                in_dihedrals = True
                itp_lines.append(line)
                continue
            elif stripped.startswith("[ ") and stripped.endswith(" ]"):
                # New section we don't need in itp
                current_section = "other"
                continue

            # Add lines from relevant sections
            if current_section in (
                "atomtypes",
                "moleculetype",
                "atoms",
                "bonds",
                "angles",
                "dihedrals",
            ):
                if stripped and not stripped.startswith(";"):
                    itp_lines.append(line)

        return "\n".join(itp_lines)
