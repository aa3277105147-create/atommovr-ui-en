# Feature Audit and Extension Priorities

This audit covers the upstream README, tutorial, algorithms, and core models, together with the workbench's interface, adapter, scheduler, comparison tools, and player. It distinguishes capabilities present upstream, capabilities exposed by the workbench, and capabilities that require additional development. Results in the original paper are not general performance guarantees for this application.

## Current coverage

| Capability | Upstream basis | Workbench support | Rationale |
|---|---|---|---|
| Six single-species algorithms | algorithms/single_species.py | All integrated; BC variants require a central target; LBAP uses experimental serial adaptation | Compare assignment and balancing strategies |
| Stochastic loading | core.py, AtomArray.load_tweezers | Independent loading random stream and manual editing | Model loading or reproduce a chosen scene |
| Four regular targets | AtomArray._generate_single_species_target | Central square, checkerboard, horizontal stripes, vertical stripes | Show density and shape effects |
| AOD intersections and collision events | move_utils.py, AtomArray.move_atoms | Upstream execution with additional capacity and conservative trajectory checks | Point-like lattice model, not full hardware safety |
| Vacuum and tweezer errors | ZeroNoise, UniformVacuumTweezerError | Lifetime, pickup/putdown success, and noise switch | Record upstream outcomes rather than create another loss model |
| Transfer and acceleration durations | ErrorModel, aod_timing.py | Four durations from 0 to 10000 µs, default zero | Apply with or without noise using adjacent-batch timing |
| Single-trial comparison | Upstream Benchmarking; independent comparison adapter here | Shared initial state, target, and physical conditions | A single execution is not a statistical ranking |
| Repeated trials | Upstream repeated-shot concept | Independent adapter, 1–20 trials, default five | Preserve safety, capacity, and failure states |
| Numerical export | Upstream Benchmarking can save NetCDF | Full trajectory JSON and CSV with per-trial configurations | Support inspection and analysis, not video or control waveforms |
| Images, GIFs, and appearance settings | animation.py, customize.py | Independent Canvas player; upstream GIF export is not called | Step, seek, and slow playback support explanation |

See [USER_GUIDE.md](USER_GUIDE.md) and [VALIDATION.md](VALIDATION.md) for operation and recorded checks. Source references are available in the [upstream repository](https://github.com/bernienlab/atommovr) and [single-species entry points](https://github.com/bernienlab/atommovr/blob/main/atommovr/algorithms/single_species.py).

## Available upstream but not exposed

| Capability | Upstream entry point | Value and required adaptation | Priority |
|---|---|---|---|
| Left-fill target | Configurations.Left_Sweep | Offset targets; specify width, algorithm scope, and boundary validation | Small future extension |
| Random targets and target density | Configurations.RANDOM, target_occup_prob | Irregular targets; add an independent target random stream and freeze both states | Add for a specific research need |
| Custom target matrix | AtomArray.target; explicit Benchmarking target arrays | Edit or import targets; validate nonempty targets, algorithm scope, and snapshots | Prefer to many additional presets |
| Dual-species rearrangement | InsideOut, NaiveParHung, two-channel AtomArray | Species-specific counts, targets, display, paths, scheduling, and validation | Separate second phase |
| Multiple feedback rounds | Benchmarking.rounds_list | Replan after loss; accumulate round time, imaging overhead, and round boundaries | Keep single execution here; add an explicit mode |
| Remove excess atoms | do_ejection, source/ejection.py | Count intentional ejection separately and handle out-of-bounds destinations | Defer to avoid confusing removal with error loss |
| Larger parameter sweeps | Benchmarking size, target, error, and parameter lists | Loading/lifetime/capacity curves; computation grows with combinations and trials | Begin with a one-dimensional sweep |
| Bottleneck-assignment time lower bound | source/scaling_lower_bound.py | Compare an ideal lower bound with execution; disclose omitted paths, capacity, and transfers | Optional advanced analysis |
| Acceleration/deceleration failure rates | ErrorModel.accel_fail_rate, decel_fail_rate | Extend event statistics and legends, separately from putdown loss | Expose when calibrated values are available |
| Custom error models | ErrorModel subclass interface | Position-dependent errors; state assumptions and validate reproducibility | Research extension |
| GIF/static-image export | make_single_species_gif and related functions | Render recorded frames rather than rerun and resample noise | Follow numerical export |
| New algorithm plugins | Algorithm_class.Algorithm | Implement adapters and common evaluation, rather than add names | Integrate after implementation, license review, and validation |

Dual-species algorithms exist upstream, but supporting them requires more than displaying two colors. One species can obstruct the other, and success must be checked separately for each species. See [atommovr, Section 6](https://arxiv.org/html/2508.02670v2#S6).

## Capabilities not implemented by the current framework

ArrayGeometry contains rectangular, triangular, and Bravais enum values, but marks geometries other than the square lattice as unsupported. AtomArray.geom having a RECTANGULAR default does not generate a physical rectangular-lattice model. A matrix's row and column dimensions are not general lattice support. See [core.py](https://github.com/bernienlab/atommovr/blob/main/atommovr/utils/core.py) and [CONTRIBUTING.md](https://github.com/bernienlab/atommovr/blob/main/CONTRIBUTING.md).

BenchmarkingFigure describes itself as a nonoperational placeholder, and the contribution guide lists automatic plotting as future development. Existing plotting methods do not establish a complete supported plotting system.

Continuous AOD waveforms, finite-trap and detailed heating models, alternative SLM/holographic transport, and RL/ML models are not implemented by this workbench. The paper identifies these as research directions; interpolated animation or enum values do not replace physical models. See [atommovr, Section 7](https://arxiv.org/html/2508.02670v2#S7).

## Audit findings and interpretation

1. **Optimal assignment is not optimal rearrangement.** Hungarian minimizes total assignment cost, and LBAP minimizes the longest assignment distance. Paths, resources, transfers, and loss require separate evaluation. Neither is described as universally fastest or optimal.
2. **Pattern support is not a success guarantee.** Upstream planning flags can disagree with actual final filling. The adapter uses final occupancy. Some native LBAP parallel batches collide; this workbench marks it experimental and uses conservative serial execution. Small targets use upstream round_lim to extend the planning limit without changing the native algorithm.
3. **Capacity is not an atom count.** Active rows and columns form a complete Cartesian product, including empty and stationary intersections. Upstream move_atoms completes intersections, so scheduling must count the closure before execution.
4. **Endpoint checks are insufficient.** Synchronous whole-path minimum-distance and static-occupancy checks prevent intermediate collisions and unintended transfers of atoms outside the native batch's intent. Actual occupancy is rechecked after errors. Serializing moves is not a universal solution.
5. **Enough atoms can still produce a safety stop.** A stop follows this adapter's conservative policy and is reported separately. It does not prove that the native algorithm or a real device could never complete the scene.
6. **Upstream sampling needs an explicit interpretation.** Benchmarking.check_sufficient_atoms=True resamples insufficient initial states. That suits conditional evaluation but can overstate success directly after loading. This workbench retains insufficient cases and reports their counts.
7. **Feedback-round time must be accumulated.** Upstream _run_benchmark_round overwrites t_total with each evaluate_moves call and can retain only the final round's time. This does not affect the current single-round adapter. A future feedback mode should not reuse that aggregate unchanged.
8. **Execution helpers differ.** AtomArray.evaluate_moves supplies preceding and following batches; the simplified benchmarking.evaluate_moves helper does not. Nonzero transfer overheads require the former semantics. This adapter times adjacent scheduled batches.
9. **Shared seeds do not replace statistics.** Algorithms consume random numbers differently; the same seed does not assign identical loss events to individual atoms. One trajectory cannot support a scientific ranking.
10. **Time and complexity are distinct.** Interface N is side length, while paper N may mean target atoms or defects. Assignment complexity, physical-time scaling, computer runtime, and playback duration must be distinguished.

These observations concern the reviewed upstream source and adapter. Concrete regression cases and test coverage are recorded in [VALIDATION.md](VALIDATION.md); passing a finite set of cases does not guarantee every configuration.

## Extension order

The current release prioritizes operation durations, repeated trials, and numerical export to make comparisons inspectable. Next consider custom targets/initial-state import and one-dimensional parameter sweeps, followed by visual export from recorded frames.

Dual-species support, feedback rounds, ejection, arbitrary lattices, and hardware waveforms need separate development with appropriate success conditions, timing, errors, and validation. Manually entered occupancy can represent an observed state but does not itself simulate imaging. See the [experimental stochastic-loading workflow](https://arxiv.org/abs/1607.03042).
