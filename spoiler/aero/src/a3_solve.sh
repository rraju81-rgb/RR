#!/bin/bash
# Aero test: re-solve an already meshed variant from its 0.orig (no re-meshing).  Run from spoiler/:  bash aero/src/a3_solve.sh <variant>
set -e
VAR=$1; NPROC=${NPROC:-4}; NITER=${NITER:-1500}; NUP=${NUP:-300}
source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1 || true
cd aero/out/$VAR
log() { echo "[$(date +%H:%M:%S)] $*"; }
rm -rf [1-9]* processor*/[1-9]* log.simpleFoam log.simpleFoam2
for d in processor*; do rm -rf $d/0; cp -r 0.orig $d/0; done
sed -i "s|div(phi,U)      bounded Gauss linearUpwindV grad(U);|div(phi,U)      bounded Gauss upwind;      // stage 1|" system/fvSchemes
log potentialFoam;  mpirun --allow-run-as-root --oversubscribe -np $NPROC potentialFoam -parallel -writephi > log.potentialFoam 2>&1
sed -i "s/^endTime .*/endTime         $NUP;/" system/controlDict
log "simpleFoam stage 1 (upwind, $NUP it)"
mpirun --allow-run-as-root --oversubscribe -np $NPROC simpleFoam -parallel > log.simpleFoam 2>&1
sed -i "s/^endTime .*/endTime         $NITER;/" system/controlDict
sed -i "s|div(phi,U)      bounded Gauss upwind;.*|div(phi,U)      bounded Gauss linearUpwindV grad(U);|" system/fvSchemes
log "simpleFoam stage 2 (linearUpwind, to $NITER)"
mpirun --allow-run-as-root --oversubscribe -np $NPROC simpleFoam -parallel > log.simpleFoam2 2>&1
log reconstruct;    reconstructPar > log.reconstructPar 2>&1
log done
