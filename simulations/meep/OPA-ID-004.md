# OPA-ID-004 — Inverse designed waveguide crossing

A four-port crossing allows two optical paths to intersect in the same plane.
A straight-through signal should continue to the opposite port, with little
power scattered into the perpendicular guides. This study uses generic 2D Ez
Meep, index 1.8 in air, 0.6 µm guides and a 2.4 × 2.4 µm design region
with 25 × 25 material weights. It follows the adjoint verification and
splitter in OPA-ID-001/002.

Compare a plain binary plus-shaped crossing, a grayscale seed, optimized
continuous material, and a 0.5-thresholded diagnostic. Optimize at 1550 nm
and 30 px/µm under fourfold rotational and mirror symmetry. The objective
is incident-normalized through power minus the sum of both perpendicular
outgoing guided-mode powers. Projected ascent with backtracking is limited
to ten iterations. Finite differences in two symmetric directions and
two step sizes verify gradients at 30 and 60 px/µm; use the ID-001
minimum runtime of 200 Meep units.

Independent forward simulations at both resolutions measure all four
outgoing powers with straight-guide normalization and incident subtraction
at the launch port. Positive east/north and negative west/south coefficients
are outgoing. Repeat vertical excitation at fine resolution and validate
1530 and 1570 nm without optimizing on those wavelengths. The symmetry
restriction is not a substitute for these independent runs.

Mandatory checks cover completeness, gradient agreement, reference,
finite values, independent objective agreement, symmetry, passivity
tolerance and monotonic accepted steps. Scientific goals are separate:
improve both seed and plain crossing, >95% through transmission, summed
crosstalk <1%, reflection <1%, coarse/fine and orthogonal transmission
differences <3 percentage points. Failure to reach a research goal
does not invalidate otherwise sound measurements.

Outputs: result.json, measurements.csv, gradient_checks.csv,
optimization_history.csv, optimized_density.csv, environment lock and
package inventory. Run through the existing selective CI workflow.
This first bounded experiment runs serially; the current parallel
workflows are specific to ID-003 and MOD-007. No shared CI changes.
No claim of fabrication tolerance, minimum feature size, foundry
readiness, physical verification, full complex scattering matrix or novelty.
The binary threshold is not fabrication optimization. A later study can
add robust geometry perturbations, multiple wavelengths, feature constraints
and 3D validation.
