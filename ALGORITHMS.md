# Rearrangement Algorithms and Comparison Methodology

The workbench calls six upstream single-species algorithms from atommovr to show assignment, transport, parallel scheduling, and loss. Success is determined from the actual final occupancy of every target site; excess atoms outside the target are retained.

## Available algorithms

| Algorithm | Upstream class | Main strategy | Targets in this workbench | Tweezer limit |
|---|---|---|---|---|
| Parallel Hungarian | ParallelHungarian | Distance-cost assignment, path planning, and grouping into parallel batches | All four patterns | 1–24 |
| Hungarian, sequential | Hungarian | Distance-cost assignment followed by sequential transport | All four patterns | Fixed at 1 |
| Parallel LBAP, bottleneck assignment | ParallelLBAP | Reduce the longest assignment distance, then plan paths; experimental implementation | All four patterns | Conservative serial execution, fixed at 1 |
| Generalized Balance | GeneralizedBalance | Recursively alternate row and column balancing; some batches can be parallel | All four patterns | 1–24 |
| BCv2, optimized balance and compact | BCv2 | Balance regional atom supply and compact into the central target | Central square | 1–24 |
| BC, traditional balance and compact | BalanceAndCompact | Earlier row and column balancing and compaction implementation | Central square | 1–24 |

The four patterns are a central square, checkerboard, horizontal stripes, and vertical stripes. Compare these entries with the [upstream single-species source](https://github.com/bernienlab/atommovr/blob/main/atommovr/algorithms/single_species.py). Pattern support does not guarantee success for every initial state.

Hungarian assignment minimizes total cost in the chosen cost matrix, while LBAP minimizes the longest assignment distance. Neither objective is equivalent to globally minimizing the complete rearrangement time. Paths, resources, transfer overheads, and loss also affect the outcome; see the [atommovr paper](https://arxiv.org/html/2508.02670v2). Some native LBAP parallel plans cannot complete without loss. This adapter retains its assignment strategy, uses conservative serial execution, and marks it experimental.

## Parallel scheduling

The default capacity is four. It counts the Cartesian product of active AOD rows and columns, including empty and stationary intersections. Two rows and two columns create four moving traps even if only two atoms are intended to move. Row and column RF-tone counts and total moving-trap capacity are distinct resources; see [HiPARS, Section III-A](https://arxiv.org/html/2509.12083v1).

The workbench's independently implemented adapter retains a native batch if it passes checks and fits within capacity. Other batches are split according to occupied-site and vacancy dependencies. Checks include AOD command compatibility, synchronous straight trajectories of the complete intersection grid, conflicts with stationary occupied sites, and upstream noiseless execution to verify atom count and the intended state.

The scheduler does not add transfers of occupied atoms outside the original batch's intent. If no safe split exists, it reports a **Safety stop** and retains completed steps.

When pickup error is enabled, the scheduler does not rely on another atom in the same batch definitely leaving its source. Occupancy is rechecked before each executed batch. If earlier errors make the remaining plan unsafe, execution stops without automatic replanning. A larger capacity can change batches, physical time, and loss; it does not always reduce time.

The checks cover lattice sites, synchronous straight paths, and point-like traps. They do not cover finite trap sizes, tone separation, optical power, or complete hardware waveforms. Scheduled batches may differ from unrestricted upstream replay in the original paper, so comparisons should report the adapter's capacity and scheduling conditions.

## Reading the comparisons

**Algorithm comparison · Single trial** compares one fixed scene. A successful transport command requires an occupied source, a nonzero displacement, and a successful outcome. Repeated moves of one atom count repeatedly. Successful distance is the sum of those commands' Euclidean path lengths, excluding failed and empty-site commands. Under noise, a shorter distance can result from failure; inspect filling as well.

**Algorithm comparison · Repeated trials** describes empirical performance for the selected conditions. Random mode reloads the array per trial; manual mode preserves occupancy and changes the error seed. Manual trials without noise produce the same result.

Within each trial, algorithms share the initial state and seed. Full-target proportion is based on final target occupancy, and its denominator includes all executed trials, including insufficient loading, incomplete results, and safety stops. Mean filling includes those outcomes. Mean successful physical time includes a sample count. Algorithms perform different operations and consume random numbers differently, so a shared seed does not align individual loss events.

After about two minutes, the workbench stops starting new algorithm executions and retains completed records. Unequal sample counts should not be interpreted as a direct ranking. Small samples illustrate trends and do not identify a universally best algorithm.

Computer computation time, simulated physical time, and animation duration are different measurements. Upstream timing determines pickup, putdown, acceleration, and deceleration from neighboring batches, then adds the current batch's longest moving-trap travel time. These operation durations are batch overheads, not costs multiplied by the atom count. Presentation speed is excluded from simulation.

## Complexity and related methods

In the interface, N is the array side length and the number of sites is N². For comparisons, distinguish side length L, site count S=L², initial atoms A, target sites T, and initial target defects D. Papers may use N for target atoms or defects, so their expressions cannot be substituted directly.

The upstream assignment step calls SciPy linear_sum_assignment, implemented using a modified Jonker–Volgenant method with rectangular cost-matrix support; see [SciPy documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html). A single assignment step's complexity is not the complexity of the complete rearrangement, which also includes paths, grouping, scheduling, and possibly repeated assignment. A fitted scaling law for physical time is not CPU complexity.

| Related method | Entry point in this upstream version | Interpretation |
|---|---|---|
| Greedy | No separate algorithm class with this name | A family of strategies; specify selection, paths, and collision handling |
| Tetris | Not integrated | Row/column transport and control pipelining; move counts and physical-time scaling do not directly establish CPU O(N). [Original paper](https://arxiv.org/abs/2210.10364) |
| HiPARS | Not integrated | Heuristic search and composite parallel transport; computation depends on candidate row/column combinations and other settings. [Original paper](https://arxiv.org/html/2509.12083v1) |
| HCA | Not integrated | Heuristic Cluster Algorithm; near-defect-count transport does not imply linear computation time or global optimality. [Original paper](https://arxiv.org/abs/2011.10390) |
| RL/ML | No trained model or inference entry point | Requires a particular model, environment, reward, and evaluation. Upstream discusses learning as future work. [Discussion](https://arxiv.org/html/2508.02670v2#S7) |

These methods are not aliases for the six available classes. See [FEATURE_SCOPE.md](FEATURE_SCOPE.md) for unexposed capabilities and extension priorities.
