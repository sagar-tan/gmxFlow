# gmxFlow - Complete Problem/Solution Reference & Edge Case Guide

> Comprehensive catalog of ALL known issues, edge cases, and fixes across protein types, ligand types, complex types, and system configurations for GROMACS MD simulations.

---

## TABLE OF CONTENTS

1. [Input File Validation Pipeline](#1-input-file-validation-pipeline)
2. [Protein-Specific Edge Cases](#2-protein-specific-edge-cases)
3. [Ligand-Specific Edge Cases](#3-ligand-specific-edge-cases)
4. [Complex-Specific Edge Cases](#4-complex-specific-edge-cases)
5. [Topology Assembly & Force Field Issues](#5-topology-assembly--force-field-issues)
6. [System Building Issues](#6-system-building-issues)
7. [GROMPP Preprocessor Errors](#7-grompp-preprocessor-errors)
8. [MDRUN Runtime Crashes](#8-mdrun-runtime-crashes)
9. [Analysis & Advanced Simulation Issues](#9-analysis--advanced-simulation-issues)
10. [GROMACS Version-Specific Issues](#10-gromacs-version-specific-issues)
11. [Local Ligand Parameterization (LigParGen Replacement)](#11-local-ligand-parameterization-ligpargen-replacement)
12. [Automated Fix Matrix](#12-automated-fix-matrix)

---

## 1. INPUT FILE VALIDATION PIPELINE

### Pre-Pipeline Checks (All Fully Automatable)

| Check | What It Detects | Severity | Fix |
|-------|----------------|----------|-----|
| PDB format compliance | Column widths, required fields | Warning | Auto-correct or reject |
| ALTLOC / alternate conformations | Duplicate atom positions | **Fatal** | Strip to highest occupancy |
| HETATM records | Non-standard residues, ligands, ions, waters | **Fatal** | Separate before pdb2gmx |
| Missing residues (REMARK 465/470) | Unresolved regions in PDB | Warning | Flag for PDBFixer/Modeller |
| Chain continuity | Gaps in residue numbering | Warning | Flag for review |
| Duplicate atoms | Same residue+atom combination | **Fatal** | Remove duplicates |
| Occupancy values | Non-standard occupancy (<1.0 or >1.0) | Warning | Normalize or flag |
| Residue name validation | Residues not in selected FF's RTP | **Fatal** | Convert, remove, or parameterize |
| Total charge calculation | Net non-zero charge | Warning | Suggest counter-ion addition |
| Coordinate count vs topology | Mismatch between .gro and .top | **Fatal** | Rebuild topology |
| Box size vs cutoff | Box too small for van der Waals cutoff | **Fatal** | Enlarge box |
| Overlapping atoms | Atoms <0.1 nm apart | **Fatal** | Energy minimize or remove |

---

## 2. PROTEIN-SPECIFIC EDGE CASES

### 2.1 Multi-chain Proteins & Multimers

**Problem:** `Chain identifier 'X' was used in two non-sequential blocks` (fatal)
- **Root Cause:** Non-contiguous chain residues in PDB (e.g., chain A interrupted by chain B)
- **Triggers:** Heterodimers, antibody heavy/light chains, multimeric proteins
- **Fix:** `pdb2gmx -chainsep id` or renumber chains to be sequential
- **Automatable:** YES - script chain renumbering

**Problem:** Inter-chain disulfide bonds not recognized
- **Root Cause:** pdb2gmx treats chains as separate molecules by default
- **Fix:** `pdb2gmx -merge all` to merge chains into single moleculetype
- **Automatable:** YES - detect CYS-CYS across chains, auto-add `-merge`

### 2.2 Disulfide Bridges (CYS-CYS)

**Problem:** `Residue 'CYX' not found in residue topology database` (GitLab #4929)
- **Root Cause:** CYX (disulfide-bonded CYS) not in default specbond.dat
- **Fix:** Add to specbond.dat: `CYX SG 1 CYX SG 1 0.2 CYS2 CYS2`
- **Automatable:** YES - script mod of specbond.dat

**Problem:** Disulfides break during simulation (LINCS warnings)
- **Root Cause:** Missing CYS2 bonded parameters for S-S angles/dihedrals
- **Fix:** Use CHARMM36m or Amber ff19SB (validated CYS2 params)
- **Automatable:** YES - FF selection

**Problem:** Distorted disulfide bonds (>0.22 nm S-S distance)
- **Root Cause:** Cryo-EM/low-res structures have stretched disulfides
- **Fix:** Adjust specbond.dat reference length; pre-minimize structure
- **Automatable:** Partially - detect and warn, human decides

### 2.3 Glycosylated Proteins

**Problem:** `Glycosidic links not recognized by pdb2gmx`
- **Root Cause:** No .rtp entries for glycosylated ASN; GLYCAM residue names (4YB, etc.) not recognized
- **Fix:** Use CHARMM-GUI Glycan Modeler; merge GLYCAM parameters
- **Automatable:** Partially - CHARMM-GUI automates

**Problem:** LINCS warnings after 5+ ns with glycans
- **Root Cause:** GLYCAM/CHARMM36 parameter mismatch; insufficient equilibration
- **Fix:** Consistent CHARMM36m + Glycan; reduce timestep to 1 fs
- **Automatable:** NO - human judgment needed

### 2.4 Membrane Proteins

**Problem:** Membrane pore formation / "holes in membrane"
- **Root Cause:** Insufficient restraints; rapid heating; thickness mismatch
- **Triggers:** GPCRs, beta-barrels, multi-pass membrane proteins
- **Fix:** `mdrun -membed` for gentle insertion; 1000 kJ/(mol nm²) restraints for 5-10 ns
- **Automatable:** Partially - CHARMM-GUI handles insertion

**Problem:** Protein hydrophilic domains buried in membrane
- **Root Cause:** `editconf -princ` aligns along x-axis (GROMACS 4.0+ default)
- **Fix:** `editconf -princ -rotate 0 90 0` to align transmembrane along z
- **Automatable:** YES - detect membrane protein, auto-orient

### 2.5 Intrinsically Disordered Proteins (IDPs)

**Problem:** Radius of gyration underestimated by ~30%
- **Root Cause:** Protein-water LJ interactions too strong
- **Fix:** Rescale protein-water LJ by λ=1.08 (IDPs) / λ=1.04 (IDR linkers)
- **Automatable:** YES - modify .itp files

**Problem:** Over-stabilized secondary structure in IDPs
- **Root Cause:** ff14SB over-stabilizes helix/sheet in unfolded proteins
- **Fix:** Use IDP-optimized FFs (ff19SB+OPC, CHARMM36m corrections)
- **Automatable:** YES - FF selection

### 2.6 Metal-binding Proteins

**Problem:** `Residue 'Zn' not found in residue topology database`
- **Root Cause:** Metal ions not in FF .rtp; missing bonded parameters
- **Fix:** Use MCPB.py for bonded metal parameters; add to ffnonbonded.itp
- **Automatable:** Partially - MCPB.py automates

**Problem:** Metal coordination geometry distorted, ligand dissociation
- **Root Cause:** 12-6 LJ underestimates coordination energy
- **Fix:** Use 12-6-4 LJ model; add metal-ligand angle/dihedral params
- **Automatable:** NO - requires QM calculations

### 2.7 Phosphorylated/Modified Proteins (PTMs)

**Problem:** `Residue 'PHO' (phospho-Ser/Thr/Tyr) not found in rtp`
- **Root Cause:** Standard FFs lack PTM parameters
- **Fix:** Use PhosphoPep parameters; add PTM entries to .rtp via SwissParam
- **Automatable:** Partially - SwissParam automates

### 2.8 NMR vs X-ray Structures

**Problem:** High RMSD, unstable simulation from NMR ensembles
- **Root Cause:** NMR models are averaged, not single conformations
- **Fix:** Select lowest-energy representative; simulated annealing
- **Automatable:** NO - human model selection

**Problem:** Missing atoms from low-res X-ray/cryo-EM (>2.5 Å)
- **Fix:** Modeller/SWISS-MODEL to fill missing atoms; `-ignh` flag
- **Automatable:** Partially - Modeller automates

### 2.9 Cryo-EM Structures

**Problem:** Overlapping atoms, LINCS warnings (3-4 Å resolution)
- **Root Cause:** Low res → incorrect side chain placement
- **Fix:** Refine with Phenix/ChimeraX; remove unresolved regions
- **Automatable:** Partially - Phenix automates refinement

### 2.10 Protonation of Catalytic Residues

**Problem:** Histidine tautomer (HID/HIE/HIP) incorrectly assigned
- **Root Cause:** pdb2gmx assigns default HIS, not pH-specific
- **Fix:** Use H++ server for pKa-based prediction; manually assign
- **Automatable:** Partially - PROPKA/H++ automates, ambiguous cases need human

### 2.11 Terminal Capping

**Problem:** `Residue 'ACE' (acetyl) not found in rtp`
- **Fix:** `pdb2gmx -ter` to apply ACE/NME terminal patches
- **Automatable:** YES

### 2.12 Non-Standard Amino Acids

**Problem:** `Residue 'MSE' (selenomethionine) not found in rtp`
- **Fix:** Mutate to MET if non-critical; parameterize with CGenFF
- **Automatable:** Partially - MSE→MET auto, novel residues need CGenFF

### 2.13 Homology Models

**Problem:** Steric clashes, crashes (<30% sequence identity)
- **Root Cause:** Incorrect side chain packing, missing loops
- **Fix:** Modeller/GalaxyWEB for quality models; position restraints during equilibration
- **Automatable:** Partially - Modeller automates

---

## 3. LIGAND-SPECIFIC EDGE CASES

### 3.1 Metal-containing Ligands

**Problem:** `Atom type 'Fe' not found` for metallocene ligands
- **Root Cause:** Metal atoms in ligands not parameterized
- **Fix:** MCPB.py for bonded metal parameters; add to ffnonbonded.itp
- **Automatable:** Partially

### 3.2 Macrocycles & Ring Systems

**Problem:** LINCS warnings, high ring strain for macrocycles
- **Root Cause:** Incorrect dihedral params for large rings; puckering not captured
- **Fix:** Use CGenFF; add improper dihedrals for ring conformation
- **Automatable:** Partially

### 3.3 Charged Ligands

**Problem:** `System has non-zero total charge` after ligand addition
- **Fix:** Add counterions with `genion`; verify charge with `gmx check`
- **Automatable:** YES

### 3.4 Tautomers

**Problem:** Ligand tautomer interconverts, incorrect binding mode
- **Root Cause:** FF does not maintain tautomer state
- **Fix:** Assign correct tautomer based on active site; distance restraints
- **Automatable:** NO - human judgment of active site

### 3.5 Stereochemistry

**Problem:** Ligand chirality inverted during simulation
- **Root Cause:** Incorrect stereochemistry in mol2; dihedrals don't maintain chirality
- **Fix:** Verify stereochemistry; use CGenFF (preserves chirality)
- **Automatable:** YES - CGenFF preserves

### 3.6 Large Ligands (>50 atoms)

**Problem:** CGenFF parameterization fails for large ligands
- **Root Cause:** CGenFF server size limits; QM calculations exceed capacity
- **Fix:** Split into fragments; use MATCH FF
- **Automatable:** NO - manual fragmentation

### 3.7 Covalently Bound Ligands

**Problem:** Covalent protein-ligand bond not recognized
- **Root Cause:** Topology missing covalent bond; pdb2gmx doesn't support covalent ligands
- **Fix:** Manually add bond to [bonds] section; parameterize adduct with CGenFF
- **Automatable:** NO - manual topology editing

### 3.8 Unusual Elements (S, P, B, Si, Halogens)

**Problem:** `Atom type 'Br' not found` for halogenated ligands
- **Fix:** Add atom types to ffnonbonded.itp; use CGenFF
- **Automatable:** Partially

### 3.9 Multiple Ligands

**Problem:** `Invalid order for directive atomtypes` with 2+ ligands
- **Root Cause:** Multiple [atomtypes] sections must come before all [moleculetype]
- **Fix:** Merge all [atomtypes] into one section at top of topology
- **Automatable:** YES - script .itp merging

---

## 4. COMPLEX-SPECIFIC EDGE CASES

### 4.1 Protein-Protein Complexes

**Problem:** Interface unfolds during simulation
- **Root Cause:** Insufficient restraints; FF misrepresents interface
- **Fix:** Position restraints on interface during equilibration; CHARMM36m
- **Automatable:** Partially

### 4.2 Protein-DNA/RNA Complexes

**Problem:** `Residue 'DA' (DNA) not found in rtp`
- **Fix:** Amber ff99SB + parmbsc0 for DNA; CHARMM36 with nucleic acids
- **Automatable:** YES

**Problem:** DNA/RNA denatures during simulation
- **Root Cause:** Insufficient salt (<0.15 M NaCl)
- **Fix:** Add 0.15 M NaCl with `genion`
- **Automatable:** YES

### 4.3 Membrane-Protein-Ligand Systems

**Problem:** Ligand partitions into membrane instead of binding protein
- **Root Cause:** Ligand logP >3 (too hydrophobic)
- **Fix:** Membrane restraints; accelerated MD
- **Automatable:** NO - logP check + human decision

### 4.4 Multi-Protein Assemblies (Ribosome, Virus Capsid)

**Problem:** `System too large for domain decomposition`
- **Fix:** Use Martini coarse-grained FF; MPI multi-node
- **Automatable:** YES

### 4.5 GPCRs

**Problem:** GPCR stabilized in inactive conformation
- **Root Cause:** Membrane missing 30% cholesterol
- **Fix:** 30% cholesterol membrane; active-state structure
- **Automatable:** Partially - CHARMM-GUI

### 4.6 Docking Poses (AutoDock, etc.)

**Problem:** Docking pose unstable, ligand dissociates within 10 ns
- **Root Cause:** Steric clashes; incorrect active site protonation
- **Fix:** Induced fit docking; short MD with ligand restraints
- **Automatable:** NO - pose validation required

### 4.7 Antibody-Antigen Complexes

**Problem:** Antibody-antigen interface dissociates
- **Root Cause:** CDR loop flexibility not captured; insufficient sampling
- **Fix:** Enhanced sampling (metadynamics); interface restraints
- **Automatable:** NO

---

## 5. TOPOLOGY ASSEMBLY & FORCE FIELD ISSUES

### 5.1 Force Field Mismatch (CRITICAL)

**Problem:** Protein FF ≠ Ligand FF → simulation crashes or garbage results
- **Root Cause:** Different atom types, combination rules, 1-4 scaling, LJ params
- **Matching Table:**

| Ligand Source | Ligand FF | Use For Protein | Notes |
|--------------|-----------|----------------|-------|
| LigParGen | OPLS-AA | oplsaa | Default match |
| ACPYPE/Antechamber | GAFF | amber99sb-ildn, amber14sb | AMBER-compatible |
| CGenFF | CHARMM General FF | charmm36 | CHARMM only |
| SwissParam | CHARMM36 | charmm36 | CHARMM only |
| ATB | GROMOS 54A7 | gromos54a7 | GROMOS only |
| Local OPLS-AA (gmxFlow) | OPLS-AA | oplsaa | See Section 11 |

**Automatable:** YES - validate FF match

### 5.2 Water Model Compatibility

| Force Field | Recommended Water | Also Compatible |
|------------|------------------|-----------------|
| AMBER99SB-ILDN | TIP3P | SPC/E |
| AMBER14SB | TIP3P (modified) | OPC |
| CHARMM36 | TIP3P (CHARMM-modified) | — |
| OPLS-AA/M | TIP4P (recommended) | TIP3P, SPC/E |
| GROMOS 54A7 | SPC | — |

**Automatable:** YES - validate water model vs FF

### 5.3 Combining Rules

| Force Field | Rule | Method |
|------------|------|--------|
| AMBER | 2 | Lorentz-Berthelot (σ additive, ε geometric) |
| OPLS | 1 | Geometric (σ geometric, ε geometric) |
| CHARMM | 2 | Lorentz-Berthelot |
| GROMOS | 1 | Geometric |

**Problem:** Mixing FFs with different combining rules → wrong LJ interactions
**Automatable:** YES

### 5.4 ITP Include Order (MOST COMMON ERROR)

**Problem:** `Invalid order for directive atomtypes`
- **Root Cause:** [atomtypes] must come BEFORE any [moleculetype]
- **Correct Order:**
```
#include "forcefield.ff/forcefield.itp"     ; parent FF
#include "ligand.itp"                        ; introduces new atom types
#include "protein_chain_A.itp"              ; first [moleculetype]
#include "water.itp"
#include "ions.itp"
[ system ]
[ molecules ]
```
**Automatable:** YES

### 5.5 gen_pairs / 1-4 Interaction Settings

| Force Field | gen_pairs | fudgeLJ | fudgeQQ |
|------------|-----------|---------|---------|
| OPLS-AA | yes | 0.5 | 0.5 |
| AMBER | yes | 0.5 | 0.8333 |
| CHARMM | yes | 1.0 | 1.0 |
| GROMOS | no | — | — |

**Problem:** Ligand ITP missing [pairs] when gen_pairs=no
**Automatable:** YES - validate gen_pairs setting matches FF

### 5.6 Empty [ pairs ] Section

**Problem:** 100+ "No default LJ-14 types" warnings
- **Root Cause:** LigParGen ITP has empty [pairs] section
- **Fix:** Remove empty [pairs] section; let FF's gen_pairs auto-generate
- **Automatable:** YES

### 5.7 -maxwarn Flag Abuse

**Problem:** `-maxwarn 1` fails with legitimate warnings (100+ from ligand topology)
- **Fix:** Increase to `-maxwarn 10` for ligand systems; `-maxwarn 200` for problematic ligands
- **Warning:** Blind -maxwarn usage → simulation blowup
- **Automatable:** YES - auto-detect ligand presence, adjust -maxwarn

---

## 6. SYSTEM BUILDING ISSUES

### 6.1 Box Size

**Problem:** `The cut-off length is longer than half the shortest box vector`
- **Root Cause:** Box < 2×cutoff in any dimension
- **Fix:** `editconf -d 1.4` (1.4 nm buffer for pressure coupling stability)
- **Automatable:** YES

**Problem:** Box shrinks during NPT, eventually violating minimum image
- **Fix:** Extra margin (1.4 nm vs 1.0 nm); check after NPT
- **Automatable:** YES

### 6.2 Solvation

**Problem:** Water inside protein/membrane → bad contacts
- **Root Cause:** vdW radii too small for certain atom types
- **Fix:** Increase vdW radii in vdwradii.dat; use `-scale 0.57`
- **Automatable:** Partially

### 6.3 Ion Placement

**Problem:** `No such moleculetype SOL` (genion can't find solvent)
- **Root Cause:** SOL not in [molecules] section
- **Fix:** Ensure SOL is defined; `genion -pname NA -nname CL` (no +/- signs)
- **Automatable:** YES

**Problem:** Ion naming convention errors
- **Fix:** Use `NA` not `NA+`, `CL` not `CL-`
- **Automatable:** YES

### 6.4 Net Charge Neutralization

**Problem:** `System has non-zero total charge` (PME warning)
- **Fix:** `genion -neutral` for counter-ions; `-conc 0.15` for physiological salt
- **Automatable:** YES - check if charge >0.01 from integer, suggest neutralization

### 6.5 Coordinate/Topology Mismatch

**Problem:** `Number of coordinates (X) does not match topology (Y)`
- **Root Cause:** [molecules] section not updated after solvation
- **Automatable:** YES - count atoms in .gro, validate against [molecules]

---

## 7. GROMPP PREPROCESSOR ERRORS

### 7.1 Missing Topology Includes

**Problem:** `Atomtype XXX not found` / `No such moleculetype SOL`
- **Root Cause:** Missing #include for ions.itp, water.itp, ligand.itp
- **Automatable:** YES - validate all referenced types exist

### 7.2 Duplicate Moleculetype

**Problem:** `moleculetype XXX is redefined`
- **Root Cause:** Same moleculetype in both topol.top and included .itp
- **Automatable:** YES

### 7.3 Unknown Atom Types

**Problem:** `Atomtype XXX not found`
- **Root Cause:** Used in [atoms] but not defined in [atomtypes]
- **Automatable:** YES

### 7.4 Missing Bonded Parameters

**Problem:** No bond/angle/dihedral parameters for ligand atom type combinations
- **Root Cause:** Ligand has bonded interactions between FF-unparameterized types
- **Automatable:** YES - validate all bonded interactions have params

### 7.5 Invalid Directive Order

**Problem:** `Syntax error - Invalid order for directive atomtypes`
- **Root Cause:** Type/parameter directives after [moleculetype]
- **Automatable:** YES

---

## 8. MDRUN RUNTIME CRASHES

### 8.1 LINCS/SETTLE Warnings → Crash

**Problem:** `LINCS WARNING: bonds rotated more than 30 degrees` → `Too many LINCS warnings` → crash
- **Root Cause (not the real cause):** System is "blowing up" due to:
  - Bad initial contacts
  - Insufficient energy minimization
  - Timestep too large
  - Invalid topology parameters
  - Overlapping atoms from solvation/insertion
- **Diagnosis Checklist:**
  1. `gmx check -c` for overlapping atoms
  2. Check initial Epot (if 10^30+, bad contacts)
  3. Shorter EM with steepest descent
  4. Smaller timestep (0.001 ps)
  5. Position restraints on heavy atoms
  6. Double precision for debugging
  7. Increase lincs_iter (2→4)
- **Automatable:** YES for pre-checks; NO for runtime diagnosis

### 8.2 1-4 Interaction Beyond Cutoff

**Problem:** `1-4 interaction between X and Y at distance >1 nm` → ignored
- **Root Cause:** System exploding (NOT a cutoff issue)
- **Fix:** Better EM, lower T, smaller timestep, check topology
- **Automatable:** Partially

### 8.3 Blown Up Systems

**Problem:** `Range Checking error` / `A charge group moved too far` / `Total potential energy is nan`
- **Common Causes:**
  - Overlapping atoms from insert-molecules or solvate
  - Bad contacts between protein and ligand
  - Missing topology parameters
  - Water inside protein/membrane
  - Charge groups too large
  - Unit confusion (Angstrom vs nm)
- **Automatable:** YES for pre-checks

### 8.4 GPU Assertion Failures

**Problem:** `Assertion failed: isHostMemoryPinned(hostBuffer)` / segfaults
- **Root Cause:**
  - Small systems (<23k particles) with separate PME rank + thread-MPI + CUDA
  - Version-specific bugs in GROMACS 2024/2025
- **Fix:** Don't use separate PME rank for small systems (`-npme 0`)
- **Automatable:** Partially - flag small systems with problematic GPU settings

### 8.5 NaN Forces

**Problem:** `Total potential energy is nan, which is not finite`
- **Root Causes:**
  - Overlapping bonded interactions
  - Very large/NaN coordinates
  - Badly equilibrated initial config
  - Invalid topology parameters
- **Automatable:** Partially - check extreme coordinates, topology issues

---

## 9. ANALYSIS & ADVANCED SIMULATION ISSUES

### 9.1 Free Energy Calculations (FEP, TI, BAR)

**Problem:** BAR error >1 kcal/mol
- **Root Cause:** Insufficient lambda points (<10); poor phase space overlap
- **Fix:** 20+ lambda points; soft-core potentials (sc-alpha=0.5, sc-power=48)
- **Automatable:** Partially

### 9.2 Umbrella Sampling

**Problem:** WHAM convergence fails
- **Root Cause:** Window spacing >0.2 nm; overlap <0.8
- **Fix:** 0.1-0.2 nm spacing; ensure overlap >0.8
- **Automatable:** Partially

### 9.3 Replica Exchange (REMD)

**Problem:** Replicas not exchanging (probability <5%)
- **Fix:** 2-5 K spacing; `-replex 500`
- **Automatable:** YES

### 9.4 Metadynamics

**Problem:** Gaussian hills too large, system explodes
- **Fix:** Hill height 0.5-1 kJ/mol; deposition rate 500-1000 steps
- **Automatable:** NO

### 9.5 MMPBSA/GBSA

**Problem:** gmx_MMPBSA fails (ligand residue not recognized)
- **Fix:** gmx_MMPBSA with GLYCAM FF; add non-standard residue params
- **Automatable:** Partially

---

## 10. GROMACS VERSION-SPECIFIC ISSUES

### 10.1 Breaking Changes

| Version | Breaking Change | Fix |
|---------|----------------|-----|
| 2021+ | Group cutoff removed, Verlet mandatory | Remove `cutoff-scheme = group` from mdp |
| 2024 | Separate PME ranks + thread-MPI + CUDA broken | Use library MPI; disable GMX_ENABLE_DIRECT_GPU_COMM |
| 2025 | Expanded ensemble checkpoint bug | Use modular simulator; avoid checkpoint restarts |

### 10.2 GPU/CUDA

**Problem:** `cuFFT R2C execution failure` on RTX 40xx
- **Fix:** CUDA 11.8+; GROMACS 2024+

**Problem:** AMD GPU crashes with >4 instances
- **Fix:** Set `ROCR_VISIBLE_DEVICES`; upgrade AdaptiveCpp 24.02+

### 10.3 Domain Decomposition

**Problem:** `No domain decomposition for n ranks` (2024+)
- **Fix:** Reduce rank count; `-ntmpi 1` for small systems
- **Automatable:** YES

---

## 11. LOCAL LIGAND PARAMETERIZATION (LigParGen REPLACEMENT)

### The Problem with LigParGen Web Server
- Requires internet access
- Server goes down periodically
- No batch processing
- No programmatic control
- OPLS-AA only (can't generate AMBER/CHARMM params)
- Slow queue times during peak usage

### Local Pipeline Architecture

A fully local LigParGen replacement needs these components:

```
SMILES / PDB / MOL2 / SDF
         │
         ▼
  ┌──────────────┐
  │  1. Structure │  RDKit: MolFromSmiles → EmbedMultipleConfs
  │  Generation   │  Generate 3D conformer(s)
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  2. Geometry  │  RDKit MMFF94 or UFF optimization
  │  Optimization │  Quick pre-optimization
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  3. Atom      │  SMARTS pattern matching
  │  Typing       │  Port MKTOP rules to Python
  │  (OPLS-AA)    │  Assign opls_xxx types
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  4. Charge    │  MOPAC (AM1) → Mulliken → scale 1.14
  │  Calculation  │  OR: RDKit Gasteiger (fast, approximate)
  │               │  OR: xtb (GFN-xTB, more accurate)
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  5. Bonded    │  Lookup from OPLS-AA parameter files
  │  Parameters   │  ffbonded.itp → bonds, angles, dihedrals
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  6. Topology  │  Write .itp file with all sections
  │  Generation   │  [atomtypes], [moleculetype], [atoms],
  │               │  [bonds], [angles], [dihedrals], [pairs]
  └──────┬───────┘
         │
         ▼
  ligand.itp + ligand.gro (ready for GROMACS!)
```

### Required Dependencies

| Component | Tool | Open Source? | Required? |
|-----------|------|--------------|-----------|
| 3D Structure | RDKit | YES | YES |
| Geometry Opt | RDKit MMFF94/UFF | YES | YES |
| Atom Typing | MolPy or custom SMARTS | YES | YES |
| Charges (accurate) | MOPAC (AM1) | Free academic | Optional |
| Charges (fast) | RDKit Gasteiger | YES | YES (fallback) |
| Charges (better) | xtb (GFN-xTB) | YES | Optional |
| Parameters | GROMACS oplsaa.ff files | YES | YES |
| Topology Writer | Custom Python | — | YES |

### OPLS-AA Parameter Files

Extract from GROMACS source: `share/top/oplsaa.ff/`
- `atomtypes.atp` — atom type list with masses
- `ffnonbonded.itp` — σ, ε, charge for each atom type
- `ffbonded.itp` — bond, angle, dihedral parameters

Available at: `https://github.com/gromacs/gromacs/tree/main/share/top/oplsaa.ff`

### Atom Typing Rules (from MKTOP)

OPLS-AA atom types assigned by:
1. Element (C, N, O, S, H, P, F, Cl, Br, I)
2. Hybridization (sp³, sp², sp)
3. Number of bonded neighbors
4. Types of neighboring atoms
5. Presence in aromatic rings
6. Functional group context (carbonyl, hydroxyl, amine, etc.)

Example: Carbon types
- `opls_135`: sp³ C in alkane (CT)
- `opls_136`: sp³ C bonded to heteroatom (CT)
- `opls_140`: sp² C in aromatic ring (CA)
- `opls_145`: sp² C in carbonyl (C)
- `opls_261`: sp³ C in methyl (CT3)
- `opls_263`: sp³ C in methylene (CT2)
- `opls_265`: sp³ C in methine (CT1)

### Charge Models

| Model | Method | Accuracy | Speed |
|-------|--------|----------|-------|
| CM1A (LigParGen) | AM1 Mulliken × 1.14 | High | Medium (needs AM1) |
| CM1A-LBCC | CM1A + 19 corrections | Highest | Medium |
| Gasteiger (RDKit) | Iterative electronegativity | Low | Instant |
| RESP/ESP | DFT ESP fitting | Highest | Slow (needs QM) |
| AM1-BCC (ACPYPE) | AM1 + bond charge corrections | High | Medium |

**Recommended:** Start with Gasteiger (instant, works for any molecule), offer MOPAC AM1 as upgrade for higher accuracy.

### LBCC Corrections (for CM1A-LBCC)

From Dodda 2017 Table S1 — 19 bond-specific corrections applied after CM1A:
- C=O bonds: +0.05 to O, -0.05 to C
- O-H bonds: +0.10 to O, -0.10 to H
- N-H bonds: +0.08 to N, -0.08 to H
- etc.

These can be implemented as SMARTS-based corrections.

### Output Format

Generated `.itp` file structure:
```
; Ligand parameterized by gmxFlow local OPLS-AA generator
; Input: SMILES / PDB / MOL2
; Charge model: Gasteiger / AM1-CM1A

[ atomtypes ]
; name  bond_type  mass  charge  ptype  sigma  epsilon
  opls_135  CT  12.011  0.000  A  0.350  0.276144
  ...

[ moleculetype ]
; name  nrexcl
  LIG     3

[ atoms ]
; nr  type  resnr  residue  atom  cgnr  charge  mass
   1  opls_135  1  LIG  C1  1  -0.180  12.011
   ...

[ bonds ]
; ai  aj  funct  b0  kb
   1   2   1  0.1529  269576.0
   ...

[ angles ]
; ai  aj  ak  funct  theta0  ktheta
   1   2   3  1  109.5  418.4
   ...

[ dihedrals ]
; ai  aj  ak  al  funct  phi0  kphi  multiplicity
   1   2   3   4  9  0  0.0  3
   ...

[ pairs ]
; ai  aj  funct  sigma  epsilon
   1   5  1  0.350  0.276144
   ...
```

### Feasibility Assessment

| Component | Difficulty | Time Estimate |
|-----------|-----------|---------------|
| Atom typing (SMARTS) | Medium | 2-3 days |
| Parameter lookup | Easy | 1 day |
| Gasteiger charges | Easy | 2 hours (RDKit built-in) |
| MOPAC integration | Medium | 1-2 days |
| Topology writer | Easy | 1 day |
| LBCC corrections | Medium | 1-2 days |
| Bonded parameter generation | Hard | 3-5 days |
| **Total** | | **2-3 weeks** |

### Integration with gmxFlow

```python
# New module: opls_local.py
from opls_local import generate_ligand_topology

# Usage in gmxFlow:
result = generate_ligand_topology(
    input_file="ligand.sdf",     # SMILES, PDB, MOL2, SDF
    molname="LIG",               # molecule name
    charge=0,                    # net charge
    charge_model="gasteiger",    # "gasteiger", "mopac_am1", "xtb"
    ff_path="/path/to/oplsaa.ff" # GROMACS OPLS-AA parameter dir
)
# Returns: ligand.itp, ligand.gro
```

---

## 12. AUTOMATED FIX MATRIX

### Fully Automatable (No Human Input Needed)

| # | Check | Fix |
|---|-------|-----|
| 1 | PDB format compliance | Auto-correct column widths |
| 2 | ALTLOC stripping | Keep highest occupancy |
| 3 | HETATM separation | Extract ligands, ions, waters |
| 4 | Chain renumbering | Make sequential |
| 5 | Duplicate atom removal | Remove duplicates |
| 6 | Water (HOH) removal | Strip before pdb2gmx |
| 7 | FF compatibility check | Validate protein FF vs ligand FF |
| 8 | Water model vs FF | Validate compatibility |
| 9 | Combining rules match | Validate rule consistency |
| 10 | Topology directive order | Reorder [atomtypes] before [moleculetype] |
| 11 | Atom type existence | Validate all types defined |
| 12 | Moleculetype duplication | Detect and flag duplicates |
| 13 | Box size vs cutoff | Enlarge if needed |
| 14 | Total charge calculation | Calculate and suggest neutralization |
| 15 | Coordinate/topology atom count | Validate match |
| 16 | gen_pairs / fudge consistency | Validate against FF |
| 17 | Include order for ligand ITPs | Auto-assemble correct topology |
| 18 | Ion naming (NA not NA+) | Auto-correct |
| 19 | Empty [pairs] section | Remove empty sections |
| 20 | -maxwarn auto-adjust | Detect ligand, increase -maxwarn |
| 21 | Disulfide bond detection | Detect CYS-CYS, add to specbond.dat |
| 22 | Terminal capping | Apply ACE/NME via pdb2gmx -ter |
| 23 | Multiple ligand ITP merging | Merge [atomtypes] sections |
| 24 | GPU rank configuration | Flag small systems, suggest -npme 0 |
| 25 | Domain decomposition | Adjust rank count for system size |

### Flag for Human Review (Semi-Automatable)

| # | Check | What to Flag |
|---|-------|-------------|
| 1 | Missing residues | REMARK 465/470 → suggest PDBFixer |
| 2 | Histidine protonation | PROPKA prediction, flag ambiguous HIS |
| 3 | Non-standard residues | Auto-convert MSE→MET, flag others |
| 4 | Missing heavy atoms | PDBFixer can add, flag for review |
| 5 | CGenFF penalty scores | Flag >10 for human review |
| 6 | Solvation quality | Flag water inside protein |
| 7 | Initial energy | Flag Epot >10^6 kJ/mol |
| 8 | Ligand-protein clashes | Flag distances <0.15 nm |
| 9 | Protein-ligand FF match | Warn if different FFs detected |
| 10 | Membrane protein orientation | Flag if not aligned along z-axis |
| 11 | IDP force field selection | Suggest IDP-optimized FF |
| 12 | Metal binding sites | Flag for MCPB.py parameterization |

### Requires Human Judgment

| # | Check | Why |
|---|-------|-----|
| 1 | Active site protonation | Context-dependent (pH, mechanism) |
| 2 | Keep/remove crystallographic waters | Structural waters may be important |
| 3 | Novel PTM parameterization | Each PTM is unique |
| 4 | Covalent ligand topology | Manual bond definition needed |
| 5 | Docking pose validation | Human must assess binding mode |
| 6 | Tautomer selection | Depends on active site chemistry |
| 7 | Metal parameterization | Requires QM calculations |
| 8 | Membrane composition | System-specific |
| 9 | Force field choice for novel systems | Depends on validation data |
| 10 | Convergence assessment | Human interpretation needed |

---

## PROPOSED PRE-VALIDATION PIPELINE FOR gmxFlow

```
STAGE 1: INPUT FILE SCAN
  ├── Parse PDB format
  ├── Strip ALTLOC → keep highest occupancy
  ├── Separate ATOM (protein) from HETATM (ligand/ions/water)
  ├── Detect missing residues (REMARK 465/470)
  ├── Check chain continuity
  ├── Detect duplicate atoms
  ├── Validate occupancy values
  └── Output: clean_protein.pdb + ligand_list

STAGE 2: PROTEIN PREP
  ├── Run PDBFixer (missing atoms/hydrogens)
  ├── Handle non-standard residues (MSE→MET auto, flag others)
  ├── PROPKA for HIS protonation (flag ambiguous)
  ├── Detect disulfide bonds (CYS-CYS within 0.22 nm)
  ├── Handle termini (FF-specific naming)
  └── Output: prepped_protein.pdb

STAGE 3: LIGAND PARAMETERIZATION
  ├── Detect ligand format (SMILES, PDB, MOL2, SDF)
  ├── Select parameterization based on protein FF:
  │   ├── OPLS-AA → Local gmxFlow generator (Section 11)
  │   ├── AMBER → ACPYPE/Antechamber
  │   └── CHARMM → CGenFF
  ├── Validate net charge
  ├── Check for missing parameters/atom types
  └── Output: ligand.itp + ligand.gro

STAGE 4: TOPOLOGY ASSEMBLY
  ├── Validate directive order
  ├── Check for duplicate moleculetypes
  ├── Validate all atom types defined
  ├── Validate gen_pairs/fudgeLJ/fudgeQQ
  ├── Validate [molecules] matches coordinate file
  ├── Validate water model vs FF
  └── Output: assembled topol.top

STAGE 5: SYSTEM BUILDING
  ├── Validate box size > 2×cutoff
  ├── Calculate total charge → suggest neutralization
  ├── Check for overlapping atoms
  ├── Validate coordinate/topology match
  └── Output: validated system

STAGE 6: PRE-RUN CHECKS
  ├── Run gmx check -c for close contacts
  ├── Validate grompp completes (flag -maxwarn usage)
  ├── Check initial potential energy
  ├── Validate charge group sizes
  ├── Validate MDP parameters vs FF
  └── Flag problematic GPU configurations
```

---

*Document Version: 1.0*
*Created: 2026-05-05*
*Sources: GROMACS forum, mailing list, bug tracker, Reddit, Biostars, ResearchGate, peer-reviewed literature*
*For use in gmxFlow automated pre-validation system design*
