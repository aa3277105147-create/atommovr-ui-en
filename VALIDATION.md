# Validation Records

These records describe checks of the shared workbench implementation and earlier revisions. They are retained for traceability; they do not imply that every English control or every operating system was tested in each historical run. English-edition release checks should be recorded separately.

## 2026-10-13: English-edition release checks

- All 62 Python behavior tests passed after translation and after changing the default seed to 1. The translated Gradio application built 71 components and 36 events, and its Python, HTML, JavaScript, and Markdown user-facing text contained no Chinese characters.
- `start.sh --check` and `Launch.command --check` completed against an existing upstream source and Python environment on macOS. Shell and Python syntax checks passed, and the Bash launcher also passed a temporary path test containing spaces and non-ASCII characters.
- `start.bat` received static checks for command labels, parentheses, `py -3.11`/`py -3` discovery, quoting, and argument forwarding. Windows and native Linux were not available for an actual launch test, so those platforms remain documented installation paths rather than claimed runtime validation.
- Browser checks covered the default simulation, single-step playback, the High-loss demo, complete playback, and a 390×844 layout without page-level horizontal overflow.

## 2026-10-11: public-interface review and feature additions

- Before release, the default random seed changed to 1. With the default 10×10 array, central 4×4 target, 60% loading, Parallel Hungarian, and no noise, the initial state contains 64 atoms and fills 11/16 target sites; four batches fill 16/16 with zero loss in 241.421356 µs of simulated physical time. All 62 tests passed again in both language editions.
- All 62 Python behavior tests passed: 42 simulation/scheduling, eight single-trial comparison, seven repeated-trial statistics, and five interface-state tests. Coverage includes real subprocesses, upstream timing agreement, reproducible noise, collision rejection, extreme initial states, statistical denominators, exported configurations, and delayed-preview protection.
- An additional 972 algorithm/pattern/size/seed/capacity/noise combinations and 216 manually specified extreme states were checked for per-frame capacity, trajectory continuity, binary occupancy, and loss accounting. Insufficient loading and safety stops were reported from the actual state.
- The adapter addressed insufficient native LBAP planning rounds for small targets using upstream `round_lim=max(15,target_count)`. Single distant atoms moved to a central single-site target with N=7, 10, and 24 all produced actual filling 1/1.
- Pickup, putdown, acceleration, and deceleration durations were added. Two adjacent continuous moves were timed as 84+98=182 µs: pickup/acceleration only at the beginning, deceleration/putdown only at the end. Both noiseless and noisy modes retain these durations; vacuum loss uses the complete batch time.
- Twelve actual subprocess runs covered six algorithms at K=1 and 24, N=24, a central 12×12 target, pickup/putdown 100 µs, and acceleration/deceleration 10 µs. All achieved 144/144 with zero loss; the longest run was about 1.99 seconds. BCv2 changed from 474 to 67 batches and 127.98 to 17.96 ms. These measurements apply only to those configurations.
- Browser edits of the four durations to 10/20/3/4 µs followed by simulation produced three batches, 281.7 µs, and 16/16 with default Parallel Hungarian, with noise disabled. A fast-input preview overwrite was fixed: previews follow actual input and a delayed refresh matching an already completed result does not rebuild the player.
- Presets that changed physics while preserving initial occupancy correctly marked single-trial and repeated-trial snapshots stale. Manual-edit events received all 18 control values.
- Browser execution of five ideal-mode seeds, 42–46, gave five runs per algorithm, all fully filled. CSV contained 30 records with each seed and complete config_json. Two seeds of the high-loss preset yielded 12 records; BCv2 reported two safety stops. With zero successful samples, mean successful time was “—”; short failed executions were not counted as a speed advantage.
- The final browser scene used BCv2, a tweezer limit of six, and default ideal physical parameters: 16/16, three batches, peak five, and 150 µs. Comparisons and repeated trials left the player's trajectory unchanged.
- Player JavaScript syntax and DOM/Canvas behavior checks covered playback, pause, stepping, seeking, speed accounting, stationary commands, empty tweezers, vacuum loss, and edit rollback. Invalid previews retained the real error message.
- Parsed JSON export matched the authoritative result, included additional physical parameters, and excluded playback state. Preview export was disabled. Clicking export displayed a file-generation confirmation. The in-app browser automation did not return a download-completion event, so that event was not used as proof of a saved download. Server-side CSV content was read and checked.
- At a 390×844 viewport, the page width remained 390 with no full-page horizontal overflow. Both tables scrolled inside their panels, headers stayed on one line, and player statistics wrapped. Public wording focused on models and comparison methodology rather than personal conversation or rankings from historical examples.

Safety remains a synchronous straight-path lattice model. Nonzero acceleration/deceleration durations are fixed overheads, not simulated velocity curves, finite beams, or device waveforms. Repeated trials run through the independent safety adapter and do not directly use upstream Benchmarking's sufficient-atom resampling.

## Earlier capacity and safety-scheduling checks

- All 42 behavior tests passed: 36 simulation/scheduling and six algorithm-comparison tests. Cases included complete AOD-intersection capacity, encounters during synchronized motion, static obstacles, reverse ordering of vacancy chains, blocked exchange cycles, preservation of unintended occupied ghost intersections, invalid long or out-of-bounds moves, safety stops after error residue, and expanded-intersection resource bounds.
- Parallel Hungarian, Generalized Balance, BCv2, and traditional BC allowed 1–24 tweezers, default four. Sequential Hungarian and conservative LBAP execution forced one. Parameter normalization and control states were checked for all six algorithms.
- BCv2 with N=10, central 4×4, loading 0.6, seed 42, and no noise executed 9/4/3/3 batches at K=1/4/8/24. Physical times were 450/200/150/150 µs, actual peaks 1/4/8/8, filling always 16/16, all 62 atoms retained, and zero collision loss.
- Browser changes from one to four BCv2 tweezers changed nine batches at 450 µs to four batches at 200 µs. The first batch displayed T1–T4, four active tweezers, and 50 µs. Changing paused presentation speed from 1× to 4× left physical time, atom count, batch, and tweezer IDs unchanged.
- N=24, central 8×8, loading 0.6, seed 42, no noise: both K=4 and 24 achieved 64/64 in 34 batches, peak four, and zero loss. The subprocess completed in about 0.53 seconds.
- Default Parallel Hungarian used three single-tweezer batches at K=1/4/8/24, achieved 16/16, and lost no atoms. The full AOD combination in this initial state would affect occupied intersections outside the original batch's intent, illustrating why more capacity does not guarantee more parallelism.
- Every frame recorded complete intersection count and current batch IDs. Planned checked-batch counts were separate from the current batch's checked flag. Unsafe splitting or an obstacle left by errors stopped execution and retained completed frames, without forced transport or automatic replanning.
- Browser comparisons completed all six algorithms at 16/16. Sequential Hungarian and LBAP had effective limit and peak one. Conservative LBAP used three batches at 191.421356 µs, unlike the historical unrestricted parallel replay at 14/16.
- Comparisons left player data unchanged. The table included tweezer limit and peak active tweezers. At 390×844, the figure, IDs, capacity statistics, and playback controls remained visible with no full-page horizontal overflow.

These checks cover unit lattice steps, synchronized straight trajectories, and native AOD rules, not finite optical spots or beat-frequency thresholds. The results below concern earlier unrestricted native-batch replay and do not substitute for current capacity-limited scheduling.

## Earlier unrestricted-replay records

- All 30 behavior tests passed: 25 simulation-adapter and five comparison tests. Coverage included available algorithms/patterns, reproducibility, edge cases, physical timing, loss causes, partial execution errors, process timeout, preview/run initial-state agreement, manual-matrix validation, frozen comparison states, unsupported-pattern skipping, successful-command metrics, and per-algorithm error isolation.
- Defaults: 62 initial atoms, 16/16 central targets filled, two batches, 120.710678 µs physical time, no atom loss.
- High-loss preset: the same 62 initial atoms, 17 remaining, target filling 2/16, 45 vacuum losses, and 12.071068 ms.
- N=24 with central 8×8: 64/64 in 26 batches.
- Browser checks covered parameter-change prompts, presets, noise controls, algorithm-pattern restrictions, target-size bounds, playback/pause, immediate speed changes, seek, step, and result updates.
- Layouts were checked at 1280×960 and 390×844. The narrow layout had no horizontal overflow and retained an operable animation and controls.
- Repeated launches reused the running service; interface dependencies had no reported conflicts.
- Live preview at N=12, loading 35%, central 6×6 showed 59 initial atoms and initial filling 12/36 without running. The previous trajectory stopped and the player indicated that simulation was pending.
- Manual mode preserved random occupancy on entry. After clearing, adding one atom, and immediately running, the latest initial state was used and the target reached 1/1. Event injection, edit confirmation, resizing, cropping, and empty padding were checked.
- While paused during batch three, changing 0.25× to 4× kept physical time at 186.092827 µs with unchanged count and progress. Seeking to the end showed 282.842712 µs and target filling 1/1.
- Display checks verified blue stationary atoms, orange moving atoms and paths, green target markers, yellow pickup-failure triangles, red transport-loss crosses, and purple vacuum-loss diamonds.
- Changing a central target to a checkerboard updated the target immediately; at N=11 the initial filling was 42/60. The high-loss preset retained 17 atoms, filled 2/16, and recorded 45 losses. At 390×844, controls and player stacked without horizontal overflow.
- Outdated result protection compared results with the latest controls and manual matrix before publishing. A previous random result could not overwrite a newer manually placed single-atom state.
- Browser menus contained six native entries, including LBAP, Generalized Balance, and traditional BC. Switching from checkerboard to traditional BC restored the central target.
- Default comparisons used the same 62-atom state generated by seed 42. The following are historical unrestricted-replay results; time is in µs and distance in µm.

| Algorithm | Actual filling | Batches | Successful transport commands | Successful distance | Physical time |
|---|---:|---:|---:|---:|---:|
| Parallel Hungarian | 16/16 | 2 | 3 | 17.071068 | 120.710678 |
| Hungarian, sequential | 16/16 | 3 | 3 | 17.071068 | 170.710678 |
| Parallel LBAP | 14/16 | 2 | 1 | 7.071068 | 141.421356 |
| Generalized Balance | 16/16 | 5 | 5 | 27.071068 | 270.710678 |
| BCv2 | 16/16 | 3 | 9 | 45 | 150 |
| Traditional BC | 16/16 | 7 | 9 | 45 | 350 |

- In that native LBAP replay, two atoms were lost even without stochastic noise. Running and seeking to the end showed 14/16, 60 remaining, and 141.4 µs. The interface used actual occupancy rather than the ideal planning flag. Traditional BC did the same; of 184 additional boundary configurations, 164 succeeded and 20 had insufficient initial atoms, with no execution exceptions.
- Comparison metrics matched the adapter, and the player was unchanged. A checkerboard change marked the old table stale. On recomparison, both BC variants displayed unsupported-pattern status and “—” metrics; the other four returned actual outcomes.
- At 390×844, the comparison table scrolled within its panel and the page had no horizontal overflow.

Each noisy outcome applies only to its stated seed and configuration; it does not estimate a statistical success probability.
