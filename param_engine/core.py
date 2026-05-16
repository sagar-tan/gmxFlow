"""
param_engine.core - Main orchestrator for ligand parameterization.

Routes molecule input to the appropriate backend based on the
selected force field. Provides a unified interface regardless
of which backend is used.
"""

import os
import shutil
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field


@dataclass
class ParamResult:
    """Result of a parameterization run."""

    success: bool
    force_field: str
    backend_used: str
    output_files: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    molecule_info: Dict[str, Any] = field(default_factory=dict)
    log: List[str] = field(default_factory=list)


# Available backends and their supported force fields
BACKEND_REGISTRY = {
    "openff": {
        "force_fields": ["smirnoff", "openff", "parsley", "sage"],
        "package": "openff.toolkit",
        "install_cmd": "conda install -c conda-forge openff-toolkit openff-interchange",
        "description": "OpenFF SMIRNOFF - modern, atom-type-free, fully local",
    },
    "acpype": {
        "force_fields": ["gaff", "gaff2", "amber"],
        "package": "acpype",
        "install_cmd": "pip install acpype && conda install -c conda-forge ambertools",
        "description": "ACPYPE + AmberTools - GAFF/GAFF2, industry standard",
    },
    "rdkit": {
        "force_fields": ["mmff94", "mmff94s", "uff"],
        "package": "rdkit",
        "install_cmd": "conda install -c conda-forge rdkit",
        "description": "RDKit MMFF94/UFF - fast fallback for quick estimates",
    },
    "opls_local": {
        "force_fields": ["oplsaa", "opls", "opls-aa"],
        "package": "rdkit",
        "install_cmd": "conda install -c conda-forge rdkit",
        "description": "Local OPLS-AA - SMARTS-based typing + Gasteiger charges",
    },
}


class ParamEngine:
    """
    Unified ligand parameterization engine.

    Replaces web-based servers (LigParGen, CGenFF, SwissParam, ATB, PRODRG)
    with a fully local, scriptable Python module.

    Usage:
        engine = ParamEngine()
        result = engine.parameterize(
            input_file="ligand.sdf",
            force_field="gaff2",
            molname="LIG",
            net_charge=0,
            output_dir="./param_output"
        )
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._backends: Dict[str, Any] = {}
        self._discover_backends()

    def _discover_backends(self):
        """Check which backends are available."""
        self._log("Discovering available backends...")

        # Check RDKit (required for most backends)
        rdkit_available = self._check_package("rdkit")
        if not rdkit_available:
            self._log(
                "WARNING: RDKit not installed. Many backends will be unavailable."
            )

        # Check OpenFF
        if self._check_package("openff.toolkit"):
            from param_engine.backends.openff_backend import OpenFFBackend

            self._backends["openff"] = OpenFFBackend(verbose=self.verbose)
            self._log("  OpenFF backend: AVAILABLE")
        else:
            self._log(
                "  OpenFF backend: NOT AVAILABLE (install: conda install -c conda-forge openff-toolkit)"
            )

        # Check ACPYPE
        if self._check_package("acpype"):
            from param_engine.backends.acpype_backend import ACPYPEBackend

            self._backends["acpype"] = ACPYPEBackend(verbose=self.verbose)
            self._log("  ACPYPE backend: AVAILABLE")
        else:
            self._log("  ACPYPE backend: NOT AVAILABLE (install: pip install acpype)")

        # Check RDKit MMFF
        if rdkit_available:
            from param_engine.backends.rdkit_backend import RDKitBackend

            self._backends["rdkit"] = RDKitBackend(verbose=self.verbose)
            self._log("  RDKit MMFF94/UFF backend: AVAILABLE")

        # Local OPLS-AA (uses RDKit)
        if rdkit_available:
            from param_engine.backends.opls_backend import OPLSLocalBackend

            self._backends["opls_local"] = OPLSLocalBackend(verbose=self.verbose)
            self._log("  Local OPLS-AA backend: AVAILABLE")

    def _check_package(self, package_name: str) -> bool:
        """Check if a Python package is installed."""
        try:
            __import__(package_name)
            return True
        except ImportError:
            return False

    def _log(self, message: str):
        """Log a message if verbose."""
        if self.verbose:
            print(f"[param_engine] {message}")

    def get_available_backends(self) -> List[str]:
        """Return list of available backend names."""
        return list(self._backends.keys())

    def get_supported_force_fields(self) -> Dict[str, List[str]]:
        """Return mapping of backend name to supported force fields."""
        return {
            name: BACKEND_REGISTRY[name]["force_fields"]
            for name in self._backends
            if name in BACKEND_REGISTRY
        }

    def select_backend(self, force_field: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Select the appropriate backend for a given force field.

        Returns:
            Tuple of (backend_name, backend_instance) or (None, None) if unavailable
        """
        ff_lower = force_field.lower().replace("-", "").replace("_", "")

        for backend_name, info in BACKEND_REGISTRY.items():
            supported = [
                ff.replace("-", "").replace("_", "") for ff in info["force_fields"]
            ]
            if ff_lower in supported:
                if backend_name in self._backends:
                    return backend_name, self._backends[backend_name]
                else:
                    return None, None

        return None, None

    def parameterize(
        self,
        input_file: str,
        force_field: str,
        molname: str = "LIG",
        net_charge: Optional[int] = None,
        output_dir: str = ".",
        charge_model: str = "default",
        optimize_geometry: bool = True,
        **kwargs: Any,
    ) -> ParamResult:
        """
        Parameterize a ligand for the specified force field.

        Args:
            input_file: Path to molecule file (SMILES string, PDB, MOL2, SDF, MOL)
            force_field: Target force field (gaff2, oplsaa, smirnoff, mmff94, etc.)
            molname: Molecule name for topology
            net_charge: Net molecular charge (auto-detected if None)
            output_dir: Directory for output files
            charge_model: Charge model to use (backend-specific)
            optimize_geometry: Whether to optimize 3D geometry before parameterization
            **kwargs: Additional backend-specific parameters

        Returns:
            ParamResult with success status, output files, and any warnings/errors
        """
        self._log(f"Starting parameterization: FF={force_field}, mol={molname}")
        self._log(f"  Input: {input_file}")
        self._log(f"  Output dir: {output_dir}")

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Select backend
        backend_name, backend = self.select_backend(force_field)

        if backend is None:
            # Try to provide helpful error message
            all_ffs = []
            for info in BACKEND_REGISTRY.values():
                all_ffs.extend(info["force_fields"])
            available_backends = self.get_available_backends()

            return ParamResult(
                success=False,
                force_field=force_field,
                backend_used="none",
                errors=[
                    f"No backend available for force field: {force_field}",
                    f"Supported force fields: {all_ffs}",
                    f"Available backends: {available_backends}",
                    "Install missing dependencies:",
                ]
                + [
                    f"  {info['install_cmd']}  # for {info['force_fields']}"
                    for name, info in BACKEND_REGISTRY.items()
                    if name not in available_backends
                ],
            )

        self._log(f"  Backend: {backend_name}")

        # Run parameterization
        try:
            result = backend.run(  # type: ignore[union-attr]
                input_file=input_file,
                molname=molname,
                net_charge=net_charge,
                output_dir=output_dir,
                charge_model=charge_model,
                optimize_geometry=optimize_geometry,
                **kwargs,
            )
        except Exception as e:
            result = ParamResult(
                success=False,
                force_field=force_field,
                backend_used=backend_name or "unknown",
                errors=[f"Backend {backend_name or 'unknown'} failed: {str(e)}"],
            )

        self._log(f"  Result: {'SUCCESS' if result.success else 'FAILED'}")
        if result.warnings:
            for w in result.warnings:
                self._log(f"  WARNING: {w}")
        if result.errors:
            for e in result.errors:
                self._log(f"  ERROR: {e}")

        return result

    def validate_topology(self, itp_file: str, gro_file: str) -> Tuple[bool, List[str]]:
        """
        Validate a generated topology file for common issues.

        Checks:
        - Directive order ([atomtypes] before [moleculetype])
        - Atom type consistency
        - Charge neutrality (if expected)
        - Missing bonded parameters
        - Empty sections

        Args:
            itp_file: Path to .itp file
            gro_file: Path to .gro file

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        from param_engine.validators.topology_validator import TopologyValidator

        validator = TopologyValidator()
        return validator.validate(itp_file, gro_file)

    def convert_format(
        self, input_file: str, output_file: str, output_format: str
    ) -> Tuple[bool, str]:
        """
        Convert a molecule file between formats.

        Supported formats: sdf, mol2, pdb, mol, smiles, gro

        Args:
            input_file: Input file path
            output_file: Output file path
            output_format: Target format

        Returns:
            Tuple of (success, message)
        """
        from param_engine.utils.molecule_io import MoleculeIO

        io = MoleculeIO()
        return io.convert(input_file, output_file, output_format)

    def get_backend_info(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about all registered backends."""
        info = {}
        for name, backend_info in BACKEND_REGISTRY.items():
            available = name in self._backends
            info[name] = {
                "available": available,
                "force_fields": backend_info["force_fields"],
                "description": backend_info["description"],
                "install_command": backend_info["install_cmd"],
            }
        return info

    def recommend_backend(self, protein_ff: str) -> Optional[str]:
        """
        Recommend the best backend based on the protein's force field.

        Args:
            protein_ff: Force field used for the protein (oplsaa, amber99sb, charmm36, etc.)

        Returns:
            Recommended backend name, or None if no match
        """
        ff_lower = protein_ff.lower().replace("-", "").replace("_", "")

        recommendations = {
            "oplsaa": "opls_local",
            "opls": "opls_local",
            "opls-aa": "opls_local",
            "amber99sb": "acpype",
            "amber99sb-ildn": "acpype",
            "amber14sb": "acpype",
            "amber": "acpype",
            "gaff": "acpype",
            "gaff2": "acpype",
            "charmm36": "openff",  # OpenFF can output CHARMM-compatible
            "charmm": "openff",
            "gromos54a7": None,  # No local GROMOS generator yet
            "gromos": None,
            "smirnoff": "openff",
            "openff": "openff",
        }

        # Check for partial matches
        for key, backend in recommendations.items():
            if key in ff_lower or ff_lower in key:
                if backend and backend in self._backends:
                    return backend

        return None
