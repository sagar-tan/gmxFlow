"""
param_engine.validators.topology_validator - Validates generated .itp files.

Checks for common issues that would cause grompp to fail:
- Directive order ([atomtypes] before [moleculetype])
- Missing atom types
- Duplicate moleculetypes
- Empty sections
- Charge consistency
- Coordinate/topology atom count match
"""

import os
from typing import List, Tuple


class TopologyValidator:
    """Validates GROMACS topology files for common issues."""

    SECTIONS_ORDER = [
        "atomtypes",
        "bondtypes",
        "angletypes",
        "dihedraltypes",
        "pairtypes",
        "moleculetype",
        "atoms",
        "bonds",
        "angles",
        "dihedrals",
        "pairs",
        "exclusions",
        "system",
        "molecules",
    ]

    def validate(self, itp_file: str, gro_file: str = None) -> Tuple[bool, List[str]]:
        """
        Validate a topology file.

        Args:
            itp_file: Path to .itp file
            gro_file: Optional path to .gro file for atom count check

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        if not os.path.exists(itp_file):
            return False, [f"File not found: {itp_file}"]

        with open(itp_file, "r") as f:
            content = f.read()
            lines = content.split("\n")

        # Check directive order
        self._check_directive_order(lines, issues)

        # Check for duplicate moleculetypes
        self._check_duplicate_moleculetypes(lines, issues)

        # Check for empty sections
        self._check_empty_sections(lines, issues)

        # Check atom type consistency
        self._check_atom_types(lines, issues)

        # Check charge consistency
        self._check_charges(lines, issues)

        # Check atom count vs gro file
        if gro_file and os.path.exists(gro_file):
            self._check_atom_count(lines, gro_file, issues)

        # Check for dangerous patterns
        self._check_dangerous_patterns(lines, issues)

        is_valid = len(issues) == 0 or all(i.startswith("WARNING") for i in issues)
        return is_valid, issues

    def _check_directive_order(self, lines: List[str], issues: List[str]):
        """Check that type directives come before moleculetype."""
        moleculetype_seen = False
        type_directives = [
            "atomtypes",
            "bondtypes",
            "angletypes",
            "dihedraltypes",
            "pairtypes",
        ]

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(";"):
                continue

            if "[ moleculetype ]" in stripped:
                moleculetype_seen = True

            for directive in type_directives:
                if f"[ {directive} ]" in stripped and moleculetype_seen:
                    issues.append(
                        f"FATAL: [{directive}] section appears after [moleculetype]. "
                        f"All type directives must come before [moleculetype]."
                    )
                    return

    def _check_duplicate_moleculetypes(self, lines: List[str], issues: List[str]):
        """Check for duplicate moleculetype definitions."""
        molnames = set()

        for i, line in enumerate(lines):
            stripped = line.strip()
            if "[ moleculetype ]" in stripped:
                # Next non-comment line should have the molname
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith(";"):
                        parts = next_line.split()
                        if parts:
                            name = parts[0]
                            if name in molnames:
                                issues.append(f"FATAL: Duplicate moleculetype '{name}'")
                            molnames.add(name)
                        break

    def _check_empty_sections(self, lines: List[str], issues: List[str]):
        """Check for empty sections (common cause of grompp warnings)."""
        current_section = None
        section_content = False

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(";"):
                continue

            if stripped.startswith("[ ") and stripped.endswith(" ]"):
                # Check if previous section was empty
                if current_section and not section_content:
                    issues.append(
                        f"WARNING: Empty section [{current_section}]. "
                        f"This may cause grompp warnings."
                    )
                current_section = stripped[2:-2].strip()
                section_content = False
            elif current_section and not stripped.startswith(";"):
                section_content = True

        # Check last section
        if current_section and not section_content:
            issues.append(f"WARNING: Empty section [{current_section}]")

    def _check_atom_types(self, lines: List[str], issues: List[str]):
        """Check that all atom types used in [atoms] are defined in [atomtypes]."""
        defined_types = set()
        used_types = set()
        in_atomtypes = False
        in_atoms = False

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(";"):
                continue

            if "[ atomtypes ]" in stripped:
                in_atomtypes = True
                in_atoms = False
                continue
            elif "[ atoms ]" in stripped:
                in_atoms = True
                in_atomtypes = False
                continue
            elif stripped.startswith("[ "):
                in_atomtypes = False
                in_atoms = False

            if in_atomtypes:
                parts = stripped.split()
                if parts:
                    defined_types.add(parts[0])

            if in_atoms:
                parts = stripped.split()
                if len(parts) >= 2:
                    used_types.add(parts[1])

        undefined = used_types - defined_types
        if undefined:
            issues.append(
                f"WARNING: Atom types used but not defined: {', '.join(undefined)}"
            )

    def _check_charges(self, lines: List[str], issues: List[str]):
        """Check total charge in [atoms] section."""
        in_atoms = False
        total_charge = 0.0
        atom_count = 0

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(";"):
                continue

            if "[ atoms ]" in stripped:
                in_atoms = True
                continue
            elif stripped.startswith("[ "):
                in_atoms = False

            if in_atoms:
                parts = stripped.split()
                if len(parts) >= 7:
                    try:
                        charge = float(parts[6])
                        total_charge += charge
                        atom_count += 1
                    except ValueError:
                        pass

        if atom_count > 0:
            if abs(total_charge) > 0.1:
                issues.append(
                    f"WARNING: Total charge = {total_charge:.4f} (not neutral). "
                    f"Consider adding counter-ions with genion."
                )

    def _check_atom_count(self, lines: List[str], gro_file: str, issues: List[str]):
        """Check that atom count in topology matches .gro file."""
        # Count atoms in topology [atoms] section
        topo_count = 0
        in_atoms = False
        for line in lines:
            stripped = line.strip()
            if "[ atoms ]" in stripped:
                in_atoms = True
                continue
            elif stripped.startswith("[ "):
                in_atoms = False
            elif in_atoms and stripped and not stripped.startswith(";"):
                topo_count += 1

        # Count atoms in gro file
        gro_count = 0
        with open(gro_file, "r") as f:
            gro_lines = f.readlines()
            if len(gro_lines) >= 2:
                try:
                    gro_count = int(gro_lines[1].strip())
                except ValueError:
                    pass

        if topo_count > 0 and gro_count > 0 and topo_count != gro_count:
            issues.append(
                f"FATAL: Atom count mismatch: topology has {topo_count}, "
                f"gro file has {gro_count}"
            )

    def _check_dangerous_patterns(self, lines: List[str], issues: List[str]):
        """Check for patterns that commonly cause simulation failures."""
        content = "\n".join(lines)

        # Check for very large charges
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(";"):
                continue
            parts = stripped.split()
            if len(parts) >= 7:
                try:
                    charge = float(parts[6])
                    if abs(charge) > 2.0:
                        issues.append(
                            f"WARNING: Very large atomic charge: {charge:.2f}. "
                            f"Check parameterization."
                        )
                except ValueError:
                    pass

        # Check for extremely small/large bond lengths
        for line in lines:
            stripped = line.strip()
            parts = stripped.split()
            if len(parts) >= 4 and parts[0].isdigit() and parts[1].isdigit():
                try:
                    length = float(parts[3])
                    if length < 0.05 or length > 0.25:
                        issues.append(
                            f"WARNING: Unusual bond length: {length:.4f} nm. "
                            f"Check parameters."
                        )
                except ValueError:
                    pass
