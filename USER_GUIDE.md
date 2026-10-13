# Atom Rearrangement Workbench: User Guide

On Windows, open **start.bat**; on Linux, run `chmod +x start.sh && ./start.sh`; on macOS, open **Launch.command** or run **./start.sh**. Keep the terminal open while the local web application is running. Press **Control-C** to stop it. Setup details are in [README.md](README.md).

## Demonstration workflow

1. Choose **Ideal rearrangement**, select **Run simulation**, and play the computed trajectory.
2. Pause, step backward or forward, drag the progress slider, or replay to inspect individual batches. Space toggles playback; the arrow keys step through batches when the animation area has focus.
3. Adjust presentation speed from 0.25× to 4×. The default is about 0.6 seconds per batch, and changes apply immediately during playback.
4. Choose **High-loss demo** and run again to observe pickup failures and atom loss. This preset deliberately exaggerates losses for teaching.
5. Parameter changes update the initial-state and target preview. Run the simulation to compute a new trajectory; replay uses the result already computed.

Defaults are a 10×10 array, a central 4×4 target, 60% loading, seed 1, Parallel Hungarian, a tweezer limit of 4, and noise disabled. Array size ranges from 4 to 24, and the central target side length from 1 to N. Checkerboard and stripe targets use the entire array. BCv2 and traditional BC support central-square targets only.

## Initial occupancy and the display

Random loading samples occupancy using the loading probability at each site. The same configuration and seed reproduce the same initial state. Random loading followed by occupancy measurement and rearrangement reflects the experimental workflow described by [Barredo et al.](https://arxiv.org/abs/1607.03042). Manual placement is useful for a chosen teaching example or known measured occupancy; it does not simulate the imaging process itself.

Switching to **Manual placement** preserves the current initial state. Click lattice sites to add or remove atoms, or use **Clear placement** to start with an empty array. After running, select **Edit initial state** to return to editing. Increasing the array size adds empty sites; decreasing it removes sites outside the new boundary. Loading probability and **New random distribution** are disabled in manual mode, but the seed still controls error sampling.

Changing parameters stops the old animation and refreshes the initial-state preview. Edits made during computation also remain in the latest preview, with a prompt to run again. Preview mode displays simulated physical time as “—”.

Blue circles represent stationary atoms; orange atoms and paths identify the current moves. Green squares mark targets, and gray outlines mark empty sites. Yellow triangles indicate pickup failures, red crosses indicate transport losses, and purple diamonds indicate vacuum losses. Moving tweezers and empty AOD intersections are displayed separately from atoms.

## Physical time and errors

| Parameter | Unit | Default and range |
|---|---|---|
| Tweezer speed | µm/µs | 0.1; 0.001–1 |
| Lattice spacing | µm | 5; 1–20 |
| Atom lifetime | seconds | 30; 0.001–3600 |
| Pickup and putdown success | % | 99 each; 0–100 |
| Additional pickup, putdown, acceleration, and deceleration duration | µs | 0 each; 0–10000 |

All four additional durations apply even with noise disabled. The adapter converts them to seconds for the upstream model. The upstream timing logic uses AOD continuity across adjacent batches to determine transfers, acceleration, and deceleration, rather than assuming every atom is picked up again in every batch. Acceleration and deceleration failure rates remain zero. These durations are fixed overheads, not simulated velocity profiles.

The adapter records upstream events and does not implement a separate loss probability model. Pickup failure usually leaves an atom at its source, whereas putdown failure loses it. Empty-site commands are not counted as lost atoms.

With noise enabled, the workbench executes the ideal plan once, without automatic repair or replanning. Insufficient initial atoms preserve the initial state and produce an explanation. An already filled target needs no moves. Excess atoms outside the target are retained.

**Tweezer speed affects simulated time and loss. Presentation speed, pause, and replay affect only the display.** Repeating the same configuration and seed reproduces the simulation. The High-loss demo preset uses speed 0.001 µm/µs, lifetime 0.01 seconds, and 90% pickup and putdown success.

## Parallel tweezers and safety stops

Parallel Hungarian, Generalized Balance, BCv2, and traditional BC allow a tweezer limit of 1–24. Sequential Hungarian uses one. Upstream LBAP produces a parallel plan, but this workbench executes it conservatively with one tweezer and labels it experimental.

The limit counts the complete crossed-AOD grid, including empty and stationary intersections: two active rows and two active columns form four traps. It is neither the number of moving atoms nor a separate limit on row or column RF tones. See [HiPARS, Section III-A](https://arxiv.org/html/2509.12083v1).

The adapter checks capacity, AOD compatibility, and entire synchronous straight trajectories, then verifies the intended result with upstream noiseless execution. Batches that exceed capacity or fail checks are split using occupancy and vacancy dependencies, without moving occupied atoms outside the original batch's intent. Before every executed batch, the current occupancy is checked again. Cyclic dependencies or obstacles left by errors can produce a **Safety stop**; completed frames are preserved.

These checks use lattice sites and point-like traps. They do not validate finite optical spots, tone separation, or complete device waveforms. Changing the tweezer limit requires a new simulation and may change batches, physical time, and losses.

## Comparison, repeated trials, and export

Open **Algorithm comparison · Single trial** and select **Compare all available algorithms**. All applicable algorithms use the same initial occupancy, target, and physical parameters. Unsupported patterns are skipped. The table reports actual filling, effective tweezer limit, peak usage, batches, successful transport commands, successful transport distance, and physical time. Comparisons do not replace the player's current trajectory. Changes mark the old table as a previous snapshot.

Successful command counts and distances include only successful moves with an occupied source and nonzero displacement. Moving the same atom repeatedly contributes multiple commands. Under noise, a short distance can result from failures; one scene does not estimate a statistical success probability.

Open **Algorithm comparison · Repeated trials** and select **Run repeated trials**. The default is five trials per algorithm, with a maximum of 20, using consecutive seeds starting from the selected seed. Random mode creates a new initial state per trial; manual mode keeps the same occupancy and changes only the error seed. With noise disabled, repeated manual trials give identical results.

Algorithms share each trial's initial state and seed. The full-target proportion uses all executed trials, including insufficient loading and safety stops. Mean filling also includes those outcomes. Mean successful physical time is accompanied by its sample count. After about two minutes, no new algorithm execution is started, and completed records remain available; algorithms may have different sample counts. Small samples illustrate trends. Select **Download trial results CSV** to inspect individual outcomes and configurations.

**Export result JSON** saves the computed configuration, initial state, target, full batch trajectory, and final statistics without resampling. Exporting during playback or while paused still saves the entire result. Completed, incomplete, and safety-stopped results can be exported; previews, insufficient-loading results, and errors cannot. JSON contains numerical trajectories, not video or hardware control waveforms. The CSV includes trial status, seed, and configuration.

Read [ALGORITHMS.md](ALGORITHMS.md) for strategy and comparison details, and [FEATURE_SCOPE.md](FEATURE_SCOPE.md) for upstream capabilities that are not exposed here.

## Files and runtime

The interface does not modify the upstream algorithm implementations. The shared launcher prepares or reuses an environment and a separate upstream checkout. Managed downloads use the reference revision documented in [README.md](README.md); user-selected source may differ. Environments, dependencies, runtime state, and generated exports are excluded from Git.

The repository contains the controls, simulation adapter, conservative scheduler, comparison and trial tools, and player. The service listens only on 127.0.0.1 and normally starts looking for a free port at 7860. Opening the player HTML alone cannot run a simulation.
