#!/bin/bash
# Aero test, step 3: mesh and solve one variant.  Run from spoiler/:  bash aero/src/a3_run.sh no_spoiler|with_spoiler
set -e
VAR=$1; NPROC=${NPROC:-4}
source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1 || true
python3 aero/src/a2_case.py $VAR
cd aero/out/$VAR
log() { echo "[$(date +%H:%M:%S)] $*"; }
log surfaceFeatureExtract; surfaceFeatureExtract > log.surfaceFeatureExtract 2>&1
log blockMesh;             blockMesh > log.blockMesh 2>&1
log decomposePar;          decomposePar -force > log.decomposePar 2>&1
log snappyHexMesh;         mpirun --allow-run-as-root --oversubscribe -np $NPROC snappyHexMesh -parallel -overwrite > log.snappyHexMesh 2>&1
for d in processor*; do rm -rf $d/0; cp -r 0.orig $d/0; done
log checkMesh;             mpirun --allow-run-as-root --oversubscribe -np $NPROC checkMesh -parallel -constant > log.checkMesh 2>&1 || true
log potentialFoam;         mpirun --allow-run-as-root --oversubscribe -np $NPROC potentialFoam -parallel -writephi > log.potentialFoam 2>&1
NITER=${NITER:-1500}; NUP=${NUP:-300}
sed -i "s/^endTime .*/endTime         $NUP;/" system/controlDict
log "simpleFoam stage 1 (upwind, $NUP it)"
mpirun --allow-run-as-root --oversubscribe -np $NPROC simpleFoam -parallel > log.simpleFoam 2>&1
sed -i "s/^endTime .*/endTime         $NITER;/" system/controlDict
sed -i "s|div(phi,U)      bounded Gauss upwind;.*|div(phi,U)      bounded Gauss linearUpwindV grad(U);|" system/fvSchemes
log "simpleFoam stage 2 (linearUpwind, to $NITER)"
mpirun --allow-run-as-root --oversubscribe -np $NPROC simpleFoam -parallel > log.simpleFoam2 2>&1
log reconstruct;           reconstructParMesh -constant > log.reconstructParMesh 2>&1; reconstructPar > log.reconstructPar 2>&1
log done
