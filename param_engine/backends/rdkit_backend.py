"""
param_engine.backends.rdkit_backend - RDKit MMFF94/UFF parameterization.

Fast fallback parameterization using RDKit's built-in force fields.
Not intended for production MD but useful for quick conformational analysis
and preliminary screening.

Requires: RDKit
"""

import os
from typing import Optional, Any

from param_engine.core import ParamResult


class RDKitBackend:
    """RDKit MMFF94/UFF parameterization backend."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._log("Initializing RDKit backend...")

    def _log(self, msg: str):
        if self.verbose:
            print(f"[rdkit] {msg}")

    def run(
        self,
        input_file: str,
        molname: str = "LIG",
        net_charge: Optional[int] = None,
        output_dir: str = ".",
        charge_model: str = "gasteiger",
        optimize_geometry: bool = True,
        force_field: str = "mmff94",
        **kwargs: Any,
    ) -> ParamResult:
        """
        Parameterize using RDKit MMFF94 or UFF.

        Args:
            input_file: SMILES string or path to SDF/MOL2/PDB/MOL
            molname: Molecule name
            net_charge: Net charge (auto-detected if None)
            output_dir: Output directory
            charge_model: Charge model (gasteiger only for RDKit)
            optimize_geometry: Whether to optimize geometry
            force_field: RDKit FF (mmff94, mmff94s, uff)
            **kwargs: Additional parameters

        Returns:
            ParamResult with output files
        """
        from rdkit import Chem
        from rdkit.Chem import AllChem

        log_lines = []
        errors = []
        warnings = []

        try:
            # Load molecule
            mol = self._load_molecule(input_file, molname, log_lines)
            if mol is None:
                return ParamResult(
                    success=False,
                    force_field=force_field,
                    backend_used="rdkit",
                    errors=["Failed to load molecule"],
                    log=log_lines,
                )

            # Add hydrogens
            mol = Chem.AddHs(mol)

            # Generate 3D conformer
            self._log("Generating 3D conformer...")
            result = AllChem.EmbedMolecule(mol, randomSeed=42)
            if result != 0:
                warnings.append("3D embedding failed, using 2D coordinates")

            # Compute Gasteiger charges
            self._log("Computing Gasteiger charges...")
            AllChem.ComputeGasteigerCharges(mol)

            total_charge = sum(
                mol.GetAtomWithIdx(i).GetDoubleProp("_GasteigerCharge")
                for i in range(mol.GetNumAtoms())
            )
            self._log(f"  Total Gasteiger charge: {total_charge:.4f}")

            # Optimize geometry
            if optimize_geometry:
                self._log(f"Optimizing with {force_field}...")
                if force_field == "mmff94":
                    props = AllChem.MMFFGetMoleculeProperties(mol)
                    ff = AllChem.MMFFGetMoleculeForceField(mol, props)
                elif force_field == "mmff94s":
                    props = AllChem.MMFFGetMoleculeProperties(
                        mol, mmffVariant="MMFF94s"
                    )
                    ff = AllChem.MMFFGetMoleculeForceField(mol, props)
                elif force_field == "uff":
                    ff = AllChem.UFFGetMoleculeForceField(mol)
                else:
                    errors.append(f"Unknown force field: {force_field}")
                    return ParamResult(
                        success=False,
                        force_field=force_field,
                        backend_used="rdkit",
                        errors=errors,
                        log=log_lines,
                    )

                if ff:
                    ff.Minimize(maxIts=200)
                    self._log("  Geometry optimized")
                else:
                    warnings.append(f"{force_field} optimization not available")

            # Write output files
            out_prefix = os.path.join(output_dir, molname.lower())
            out_files = {}

            # Write GRO file
            gro_file = f"{out_prefix}.gro"
            self._write_gro(mol, gro_file, molname, log_lines)
            out_files["coordinates"] = gro_file

            # Write ITP file
            itp_file = f"{out_prefix}.itp"
            self._write_itp(mol, itp_file, molname, force_field, log_lines)
            out_files["itp"] = itp_file

            # Write SDF
            sdf_file = f"{out_prefix}_param.sdf"
            writer = Chem.SDWriter(sdf_file)
            writer.write(mol)
            writer.close()

            return ParamResult(
                success=True,
                force_field=force_field,
                backend_used="rdkit",
                output_files=out_files,
                molecule_info={
                    "smiles": Chem.MolToSmiles(mol),
                    "n_atoms": mol.GetNumAtoms(),
                    "n_bonds": mol.GetNumBonds(),
                    "total_charge": round(total_charge, 4),
                    "ff": force_field,
                },
                warnings=warnings,
                errors=errors,
                log=log_lines,
            )

        except ImportError:
            return ParamResult(
                success=False,
                force_field=force_field,
                backend_used="rdkit",
                errors=[
                    "RDKit not installed.",
                    "Install with: conda install -c conda-forge rdkit",
                ],
                log=log_lines,
            )
        except Exception as e:
            errors.append(f"RDKit backend failed: {str(e)}")
            return ParamResult(
                success=False,
                force_field=force_field,
                backend_used="rdkit",
                errors=errors,
                log=log_lines,
            )

    def _load_molecule(self, input_file: str, molname: str, log_lines: list):
        """Load molecule from various formats."""
        from rdkit import Chem

        if not os.path.exists(input_file):
            # SMILES
            log_lines.append(f"  Parsing SMILES: {input_file}")
            mol = Chem.MolFromSmiles(input_file)
        else:
            ext = os.path.splitext(input_file)[1].lower()
            log_lines.append(f"  Loading {ext}: {input_file}")

            if ext in (".sdf", ".mol"):
                mol = Chem.MolFromMolFile(input_file, removeHs=False)
            elif ext == ".mol2":
                mol = Chem.MolFromMol2File(input_file, removeHs=False)
            elif ext == ".pdb":
                mol = Chem.MolFromPDBFile(input_file, removeHs=False)
            else:
                log_lines.append(f"  Unsupported format: {ext}")
                return None

        if mol is None:
            log_lines.append("  Failed to parse molecule")
            return None

        mol.SetProp("_Name", molname)
        return mol

    def _write_gro(self, mol, gro_file: str, molname: str, log_lines: list):
        """Write GROMACS .gro file from RDKit molecule."""
        from rdkit import Chem

        conf = mol.GetConformer()
        positions = conf.GetPositions()

        with open(gro_file, "w") as f:
            f.write(f"Generated by gmxFlow param_engine (RDKit {molname})\n")
            f.write(f"  {mol.GetNumAtoms()}\n")

            for i, atom in enumerate(mol.GetAtoms()):
                res_id = 1
                res_name = molname[:5]
                atom_name = atom.GetSymbol().upper()
                atom_id = i + 1

                x, y, z = positions[i] * 0.1  # Angstrom to nm
                f.write(
                    f"{res_id:>5}{res_name:<5}{atom_name:>5}{atom_id:>5}"
                    f"{x:8.3f}{y:8.3f}{z:8.3f}\n"
                )

            f.write("  1.00000   1.00000   1.00000\n")

        log_lines.append(f"  Wrote GRO: {gro_file}")

    def _write_itp(self, mol, itp_file: str, molname: str, ff: str, log_lines: list):
        """Write GROMACS .itp file from RDKit molecule."""
        from rdkit import Chem

        with open(itp_file, "w") as f:
            f.write(f"; Ligand topology: {molname}\n")
            f.write(f"; Force field: {ff} (RDKit)\n")
            f.write("; WARNING: RDKit parameters are approximate.\n")
            f.write("; Use for preliminary analysis only.\n")
            f.write("\n")

            # moleculetype
            f.write("[ moleculetype ]\n")
            f.write(f"; molname    nrexcl\n")
            f.write(f" {molname:<12} 3\n")
            f.write("\n")

            # atoms
            f.write("[ atoms ]\n")
            f.write("; nr  type  resnr  residue  atom  cgnr  charge  mass\n")

            conf = mol.GetConformer()
            for i, atom in enumerate(mol.GetAtoms()):
                charge = atom.GetDoubleProp("_GasteigerCharge")
                mass = atom.GetMass()
                res_id = 1
                atom_name = atom.GetSymbol().upper() + str(i + 1)
                # Use element-based atom type
                atom_type = f"{atom.GetSymbol().lower()}_{i + 1}"
                cgnr = i + 1

                f.write(
                    f"  {i + 1:>4}  {atom_type:<8}  {res_id:>4}  {molname:<6}  "
                    f"{atom_name:<6}  {cgnr:>4}  {charge:>8.4f}  {mass:>8.4f}\n"
                )

            f.write("\n")

            # bonds
            f.write("[ bonds ]\n")
            f.write("; ai  aj  funct  length  kb\n")
            for bond in mol.GetBonds():
                i = bond.GetBeginAtomIdx() + 1
                j = bond.GetEndAtomIdx() + 1
                f.write(f"  {i:>4}  {j:>4}     1\n")

            f.write("\n")

            # angles
            f.write("[ angles ]\n")
            f.write("; ai  aj  ak  funct  angle  ka\n")
            for atom in mol.GetAtoms():
                idx = atom.GetIdx()
                neighbors = [n.GetIdx() for n in atom.GetNeighbors()]
                for n1 in range(len(neighbors)):
                    for n2 in range(n1 + 1, len(neighbors)):
                        i = neighbors[n1] + 1
                        j = idx + 1
                        k = neighbors[n2] + 1
                        f.write(f"  {i:>4}  {j:>4}  {k:>4}     1\n")

            f.write("\n")

        log_lines.append(f"  Wrote ITP: {itp_file}")
