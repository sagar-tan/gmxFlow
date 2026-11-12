"""
param_engine - Unified Ligand Parameterization Module for gmxFlow

A single package that replaces LigParGen, CGenFF server, SwissParam,
ATB, PRODRG, and other web-based parameterization services.

Supports: OPLS-AA, GAFF/GAFF2 (AMBER), CHARMM/CGenFF, GROMOS, SMIRNOFF/OpenFF

Author: gmxFlow Development Team
Version: 0.1.0
"""

from param_engine.core import ParamEngine

__all__ = ["ParamEngine"]
__version__ = "0.1.0"
