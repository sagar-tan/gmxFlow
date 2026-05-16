"""
param_engine.utils.molecule_io - Molecular file format conversion.

Supports: SMILES, SDF, MOL, MOL2, PDB, GRO
Uses RDKit for conversion.
"""

import os
from typing import Tuple, Optional


class MoleculeIO:
    """Molecular file format conversion utility."""

    def convert(
        self, input_file: str, output_file: str, output_format: str
    ) -> Tuple[bool, str]:
        """
        Convert a molecule file between formats.

        Args:
            input_file: Input file path (or SMILES string)
            output_file: Output file path
            output_format: Target format (sdf, mol2, pdb, mol, gro, smiles)

        Returns:
            Tuple of (success, message)
        """
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem
        except ImportError:
            return (
                False,
                "RDKit not installed. Install with: conda install -c conda-forge rdkit",
            )

        try:
            # Load molecule
            mol = self._load(input_file)
            if mol is None:
                return False, f"Could not parse input: {input_file}"

            # Write output
            success, msg = self._write(mol, output_file, output_format)
            return success, msg

        except Exception as e:
            return False, f"Conversion failed: {str(e)}"

    def _load(self, input_file: str):
        """Load molecule from file or SMILES."""
        from rdkit import Chem

        # Check if input is a SMILES string (no file exists)
        if not os.path.exists(input_file):
            return Chem.MolFromSmiles(input_file)

        ext = os.path.splitext(input_file)[1].lower()

        if ext in (".sdf", ".mol"):
            return Chem.MolFromMolFile(input_file, removeHs=False)
        elif ext == ".mol2":
            return Chem.MolFromMol2File(input_file, removeHs=False)
        elif ext == ".pdb":
            return Chem.MolFromPDBFile(input_file, removeHs=False)
        elif ext == ".gro":
            return self._load_gro(input_file)
        else:
            return None

    def _load_gro(self, gro_file: str):
        """Load molecule from GROMACS .gro file."""
        from rdkit import Chem

        mol = Chem.Mol()
        conformer_coords = []

        with open(gro_file, "r") as f:
            lines = f.readlines()

        if len(lines) < 3:
            return None

        n_atoms = int(lines[1].strip())

        for i in range(2, 2 + n_atoms):
            line = lines[i]
            if len(line) < 44:
                continue

            element = line[10:15].strip()[:2]
            # Parse coordinates (nm to Angstrom)
            x = float(line[20:28]) * 10
            y = float(line[28:36]) * 10
            z = float(line[36:44]) * 10
            conformer_coords.append((x, y, z))

            atom = Chem.Atom(element)
            mol.AddAtom(atom)

        if conformer_coords:
            from rdkit.Chem import AllChem

            conf = Chem.Conformer(mol.GetNumAtoms())
            for i, (x, y, z) in enumerate(conformer_coords):
                conf.SetAtomPosition(i, (x, y, z))
            mol.AddConformer(conf)

        return mol

    def _write(self, mol, output_file: str, output_format: str) -> Tuple[bool, str]:
        """Write molecule to file."""
        from rdkit import Chem

        fmt = output_format.lower()

        if fmt == "sdf":
            writer = Chem.SDWriter(output_file)
            writer.write(mol)
            writer.close()
            return True, f"Wrote SDF: {output_file}"

        elif fmt == "mol":
            Chem.MolToMolFile(mol, output_file)
            return True, f"Wrote MOL: {output_file}"

        elif fmt == "mol2":
            return self._write_mol2(mol, output_file)

        elif fmt == "pdb":
            Chem.MolToPDBFile(mol, output_file)
            return True, f"Wrote PDB: {output_file}"

        elif fmt == "gro":
            return self._write_gro(mol, output_file)

        elif fmt == "smiles":
            smiles = Chem.MolToSmiles(mol)
            with open(output_file, "w") as f:
                f.write(smiles)
            return True, f"Wrote SMILES: {output_file} ({smiles})"

        else:
            return False, f"Unsupported output format: {output_format}"

    def _write_mol2(self, mol, output_file: str) -> Tuple[bool, str]:
        """Write MOL2 file (RDKit doesn't have native support, write manually)."""
        from rdkit import Chem

        conf = mol.GetConformer()
        positions = conf.GetPositions()

        with open(output_file, "w") as f:
            f.write("@<TRIPOS>MOLECULE\n")
            f.write(f"{mol.GetProp('_Name') if mol.HasProp('_Name') else 'LIG'}\n")
            f.write(f"{mol.GetNumAtoms()} {mol.GetNumBonds()} 0 0 0\n")
            f.write("SMALL\n")
            f.write("NO_CHARGES\n")
            f.write("\n")
            f.write("@<TRIPOS>ATOM\n")

            for i, atom in enumerate(mol.GetAtoms()):
                x, y, z = positions[i]
                f.write(
                    f"{i + 1:>6} {atom.GetSymbol():<4} {x:10.4f} {y:10.4f} {z:10.4f} "
                    f"{atom.GetSymbol():<2} 1 LIG 0.0000\n"
                )

            f.write("\n@<TRIPOS>BOND\n")
            for bond in mol.GetBonds():
                i = bond.GetBeginAtomIdx() + 1
                j = bond.GetEndAtomIdx() + 1
                bt = bond.GetBondType()
                if bt == Chem.BondType.SINGLE:
                    order = 1
                elif bt == Chem.BondType.DOUBLE:
                    order = 2
                elif bt == Chem.BondType.TRIPLE:
                    order = 3
                elif bt == Chem.BondType.AROMATIC:
                    order = "ar"
                else:
                    order = 1
                bond_idx = bond.GetIdx() + 1
                f.write(f"{bond_idx:>6} {i:>6} {j:>6} {order}\n")

        return True, f"Wrote MOL2: {output_file}"

    def _write_gro(self, mol, output_file: str) -> Tuple[bool, str]:
        """Write GROMACS .gro file."""
        conf = mol.GetConformer()
        positions = conf.GetPositions()
        molname = mol.GetProp("_Name") if mol.HasProp("_Name") else "LIG"

        with open(output_file, "w") as f:
            f.write(f"Converted by gmxFlow param_engine ({molname})\n")
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

        return True, f"Wrote GRO: {output_file}"
