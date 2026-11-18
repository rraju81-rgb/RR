"""Aero test, step 2: write the OpenFOAM (v1912) case for one variant: 'no_spoiler' or 'with_spoiler'.
Half car (symmetry plane at Y = 0), steady RANS k-omega SST (simpleFoam), 100 km/h, moving ground, rotating wheels.
Both variants use the same domain, background mesh and refinement boxes; only the spoiler surface differs.
Run from spoiler/:  python3 aero/src/a2_case.py no_spoiler|with_spoiler"""
import sys, os, json, shutil
VAR = sys.argv[1]; assert VAR in ('no_spoiler', 'with_spoiler')
SPO = VAR == 'with_spoiler'
G = json.load(open('aero/out/geometry/geometry_info.json'))
CASE = f'aero/out/{VAR}'
U = 100 / 3.6                                   # 27.78 m/s
NU = 1.5e-5; RHO = 1.205
R_W = G['wheel_radius_m']; OMEGA = U / (R_W - 0.008)   # tyre rolls on the ground at its loaded radius
XM = 0.5 * (G['x_front_axle_m'] + G['x_rear_axle_m'])   # wheelbase mid-point (moments about it, at ground level)
AREF = G['frontal_area_m2_no_spoiler'] / 2       # half model: half the frontal area -> full-car coefficients
LREF = G['wheelbase_m']
I_T, NUT_RATIO = 0.005, 10.0                     # inlet turbulence: 0.5 % intensity, eddy/molecular viscosity ratio 10
K_IN = 1.5 * (U * I_T) ** 2; OM_IN = K_IN / (NUT_RATIO * NU)   # (a length-scale based omega gave nut/nu ~ 600: far too viscous)
NPROC = int(os.environ.get('NPROC', 4)); NITER = int(os.environ.get('NITER', 1500))
walls = ['body', 'mirrors', 'wheelF', 'wheelR'] + (['spoiler'] if SPO else [])
H = 'FoamFile\n{\n    version 2.0;\n    format ascii;\n    class %s;\n    object %s;\n}\n'
def write(rel, cls, obj, body):
    p = os.path.join(CASE, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w').write(H % (cls, obj) + body)
ONLY0 = os.environ.get('ONLY0') == '1'           # rewrite only 0.orig + case_info (keeps an existing mesh)
if not ONLY0:
    if os.path.exists(CASE): shutil.rmtree(CASE)
    os.makedirs(f'{CASE}/constant/triSurface')
    for w in walls:   # without the spoiler the car is the original body (see a1_geometry.py)
        src = 'body_base' if (w == 'body' and not SPO) else w
        shutil.copy(f'aero/out/geometry/{src}.stl', f'{CASE}/constant/triSurface/{w}.stl')
_write_all = write
def write(rel, cls, obj, body):
    if ONLY0 and not rel.startswith('0.orig'): return
    _write_all(rel, cls, obj, body)

# domain: X -10..24, Y 0..6 (half), Z 0..6 ; 0.4 m background cells
write('system/blockMeshDict', 'dictionary', 'blockMeshDict', '''
convertToMeters 1;
vertices ( (-10 0 0) (24 0 0) (24 6 0) (-10 6 0) (-10 0 6) (24 0 6) (24 6 6) (-10 6 6) );
blocks ( hex (0 1 2 3 4 5 6 7) (85 15 15) simpleGrading (1 1 1) );
boundary
(
    inlet    { type patch;         faces ((0 4 7 3)); }
    outlet   { type patch;         faces ((1 2 6 5)); }
    ground   { type wall;          faces ((0 3 2 1)); }
    top      { type patch;         faces ((4 5 6 7)); }
    side     { type patch;         faces ((3 7 6 2)); }
    midplane { type symmetryPlane; faces ((0 1 5 4)); }
);
''')
feat = ''.join(f'''
{w}.stl
{{
    extractionMethod extractFromSurface;
    extractFromSurfaceCoeffs {{ includedAngle {150 if w == 'spoiler' else 140}; }}
    subsetFeatures {{ nonManifoldEdges no; openEdges yes; }}
    writeObj no;
}}''' for w in walls if not w.startswith('wheel'))
write('system/surfaceFeatureExtractDict', 'dictionary', 'surfaceFeatureExtractDict', feat + '\n')
LEV = dict(body=(4, 5), mirrors=(5, 5), spoiler=(6, 7), wheelF=(4, 4), wheelR=(4, 4))
FLEV = dict(body=5, mirrors=5, spoiler=7)
geo = ''.join(f'    {w}.stl {{ type triSurfaceMesh; name {w}; }}\n' for w in walls)
geo += '''    boxWake    { type searchableBox; min (3.0 0 0);    max (12.0 1.6 2.3); }
    boxNear    { type searchableBox; min (-0.6 0 0);   max (6.0 1.3 1.9); }
    boxRear    { type searchableBox; min (2.6 0 0.85); max (5.6 1.0 1.75); }
    boxRoofEnd { type searchableBox; min (3.2 0 1.12); max (4.2 0.85 1.58); }
    boxWheelF  { type searchableBox; min (0.36 0.52 0); max (1.25 0.90 0.72); }
    boxWheelR  { type searchableBox; min (2.83 0.52 0); max (3.72 0.90 0.72); }
'''
feats = ''.join(f'        {{ file "{w}.eMesh"; level {FLEV[w]}; }}\n' for w in walls if w in FLEV)
rs = ''.join(f'        {w} {{ level ({LEV[w][0]} {LEV[w][1]}); patchInfo {{ type wall; }} }}\n' for w in walls)
lay = ''.join(f'        {w} {{ nSurfaceLayers {2 if w.startswith("wheel") else 3}; }}\n' for w in walls)
write('system/snappyHexMeshDict', 'dictionary', 'snappyHexMeshDict', f'''
castellatedMesh true;
snap            true;
addLayers       true;
geometry
{{
{geo}}};
castellatedMeshControls
{{
    maxLocalCells 3000000;
    maxGlobalCells 8000000;
    minRefinementCells 10;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 3;
    features
    (
{feats}    );
    refinementSurfaces
    {{
{rs}    }}
    resolveFeatureAngle 30;
    refinementRegions
    {{
        boxWake    {{ mode inside; levels ((1E15 2)); }}
        boxNear    {{ mode inside; levels ((1E15 3)); }}
        boxRear    {{ mode inside; levels ((1E15 4)); }}
        boxRoofEnd {{ mode inside; levels ((1E15 5)); }}
        boxWheelF  {{ mode inside; levels ((1E15 5)); }}
        boxWheelR  {{ mode inside; levels ((1E15 5)); }}
    }}
    locationInMesh (-5.03 3.07 3.11);
    allowFreeStandingZoneFaces true;
}}
snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 60;
    nRelaxIter 5;
    nFeatureSnapIter 10;
    implicitFeatureSnap false;
    explicitFeatureSnap true;
    multiRegionFeatureSnap false;
}}
addLayersControls
{{
    relativeSizes true;
    layers
    {{
{lay}    }}
    expansionRatio 1.25;
    finalLayerThickness 0.4;
    minThickness 0.1;
    nGrow 0;
    featureAngle 60;
    slipFeatureAngle 30;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedialAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}
meshQualityControls
{{
    #includeEtc "caseDicts/meshQualityDict"
    nSmoothScale 4;
    errorReduction 0.75;
    relaxed {{ maxNonOrtho 75; }}
}}
mergeTolerance 1e-6;
''')
NSPLIT = {1: '1 1 1', 2: '2 1 1', 3: '3 1 1', 4: '2 2 1', 6: '3 2 1', 8: '2 2 2'}[NPROC]   # (Ubuntu's OpenFOAM has no scotch)
write('system/decomposeParDict', 'dictionary', 'decomposeParDict', f'\nnumberOfSubdomains {NPROC};\nmethod hierarchical;\nhierarchicalCoeffs {{ n ({NSPLIT}); delta 0.001; order xyz; }}\n')
write('system/fvSchemes', 'dictionary', 'fvSchemes', '''
ddtSchemes      { default steadyState; }
gradSchemes
{
    default         Gauss linear;
    grad(U)         cellLimited Gauss linear 1;
    grad(k)         cellLimited Gauss linear 1;
    grad(omega)     cellLimited Gauss linear 1;
}
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss upwind;      // stage 1; a3_run.sh switches to linearUpwindV grad(U) for stage 2
    div(phi,k)      bounded Gauss upwind;
    div(phi,omega)  bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes     { default Gauss linear limited corrected 0.33; }
interpolationSchemes { default linear; }
snGradSchemes        { default limited corrected 0.33; }
wallDist             { method meshWave; }
''')
write('system/fvSolution', 'dictionary', 'fvSolution', '''
solvers
{
    p   { solver GAMG; smoother GaussSeidel; tolerance 1e-7; relTol 0.01; }
    Phi { $p; }
    "(U|k|omega)" { solver smoothSolver; smoother GaussSeidel; tolerance 1e-8; relTol 0.1; nSweeps 1; }
}
SIMPLE
{
    nNonOrthogonalCorrectors 1;
    consistent no;
}
potentialFlow { nNonOrthogonalCorrectors 10; }
relaxationFactors { fields { p 0.25; } equations { U 0.6; k 0.5; omega 0.5; } }
cache { grad(U); }
''')
plist = ' '.join(walls)
# NOTE: Ubuntu's OpenFOAM v1912 package fails in every function object (forces, sampling, yPlus ...) with
# "error in IOstream sha1" (a digest bug in that build), so the case runs without any. Forces, coefficients and the
# flow pictures are computed afterwards from the written fields by aero/src/a4_forces.py, the same way OpenFOAM's
# forces / wallShearStress function objects do (pressure: sum p S_f; friction: wall-function shear stress).
write('system/controlDict', 'dictionary', 'controlDict', f'''
application     simpleFoam;
startFrom       latestTime;
startTime       0;
stopAt          endTime;
endTime         {NITER};
deltaT          1;
writeControl    timeStep;
writeInterval   {int(os.environ.get('WRITE_EVERY', 300))};
purgeWrite      0;
writeFormat     ascii;
writePrecision  8;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;
''')
write('constant/transportProperties', 'dictionary', 'transportProperties', f'\ntransportModel Newtonian;\nnu {NU};\n')
# safety net: cap the cell speed at 80 m/s (about 3 x the free stream). A healthy solution never reaches it; it only
# stops a local blow-up in a few poor cells (wedge-shaped slivers where the spoiler meets the car) from wrecking the run.
write('system/fvOptions', 'dictionary', 'fvOptions', '\nspeedCap\n{\n    type limitVelocity;\n    active yes;\n    selectionMode all;\n    max 80;\n}\n')
write('constant/turbulenceProperties', 'dictionary', 'turbulenceProperties', '\nsimulationType RAS;\nRAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }\n')
WR = '|'.join(w for w in walls if not w.startswith('wheel'))
def field(name, cls, dim, internal, inlet, outlet, wall, ground, wheel):
    return f'''
dimensions {dim};
internalField uniform {internal};
boundaryField
{{
    #includeEtc "caseDicts/setConstraintTypes"
    midplane {{ type symmetryPlane; }}
    inlet  {{ {inlet} }}
    outlet {{ {outlet} }}
    top    {{ type slip; }}
    side   {{ type slip; }}
    ground {{ {ground} }}
    "({WR})" {{ {wall} }}
    wheelF {{ {wheel.replace('ORIGIN', f"({G['x_front_axle_m']} 0 {R_W - 0.008})")} }}
    wheelR {{ {wheel.replace('ORIGIN', f"({G['x_rear_axle_m']} 0 {R_W - 0.008})")} }}
}}
'''
Uv = f'({U} 0 0)'
write('0.orig/U', 'volVectorField', 'U', field('U', 'volVectorField', '[0 1 -1 0 0 0 0]', Uv,
      f'type fixedValue; value uniform {Uv};', f'type inletOutlet; inletValue uniform (0 0 0); value uniform {Uv};',
      'type noSlip;', f'type fixedValue; value uniform {Uv};',
      f'type rotatingWallVelocity; origin ORIGIN; axis (0 -1 0); omega {OMEGA:.4f}; value uniform (0 0 0);'))
write('0.orig/p', 'volScalarField', 'p', field('p', 'volScalarField', '[0 2 -2 0 0 0 0]', '0',
      'type zeroGradient;', 'type fixedValue; value uniform 0;', 'type zeroGradient;', 'type zeroGradient;', 'type zeroGradient;'))
write('0.orig/k', 'volScalarField', 'k', field('k', 'volScalarField', '[0 2 -2 0 0 0 0]', f'{K_IN:.6g}',
      f'type fixedValue; value uniform {K_IN:.6g};', f'type inletOutlet; inletValue uniform {K_IN:.6g}; value uniform {K_IN:.6g};',
      f'type kqRWallFunction; value uniform {K_IN:.6g};', f'type kqRWallFunction; value uniform {K_IN:.6g};', f'type kqRWallFunction; value uniform {K_IN:.6g};'))
write('0.orig/omega', 'volScalarField', 'omega', field('omega', 'volScalarField', '[0 0 -1 0 0 0 0]', f'{OM_IN:.6g}',
      f'type fixedValue; value uniform {OM_IN:.6g};', f'type inletOutlet; inletValue uniform {OM_IN:.6g}; value uniform {OM_IN:.6g};',
      f'type omegaWallFunction; value uniform {OM_IN:.6g};', f'type omegaWallFunction; value uniform {OM_IN:.6g};', f'type omegaWallFunction; value uniform {OM_IN:.6g};'))
write('0.orig/nut', 'volScalarField', 'nut', field('nut', 'volScalarField', '[0 2 -1 0 0 0 0]', '0',
      'type calculated; value uniform 0;', 'type calculated; value uniform 0;', 'type nutkWallFunction; value uniform 0;',
      'type nutkWallFunction; value uniform 0;', 'type nutkWallFunction; value uniform 0;'))
json.dump(dict(variant=VAR, U=U, nu=NU, rho=RHO, omega_wheel=OMEGA, x_mid=XM, Aref_half=AREF, lRef=LREF, k_in=K_IN, omega_in=OM_IN,
               nproc=NPROC, niter=NITER, walls=walls), open(f'{CASE}/case_info.json', 'w'), indent=1)
print('wrote', CASE, 'walls', walls, f'U {U:.2f} m/s, wheel omega {OMEGA:.1f} rad/s, Aref(half) {AREF:.4f} m2')
