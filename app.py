"""Local controls for the atommovr simulator."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import time
import urllib.request
import webbrowser

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
os.environ.setdefault("MPLBACKEND", "Agg")

import gradio as gr

from simulator import (DEFAULT_CONFIG, ALGORITHM_NAMES, ALGORITHM_PATTERNS,
                       MULTI_TWEEZER_ALGORITHMS, MAX_TWEEZERS, preview, simulate)
from comparison import TABLE_HEADERS, compare_algorithms
from benchmark import HEADERS as BENCHMARK_HEADERS, MAX_TRIALS, benchmark_algorithms, export_csv
from version import __version__

HERE = Path(__file__).resolve().parent
STATE_DIR = Path(os.environ.get("ATOMMOVR_UI_STATE_DIR", HERE / ".runtime")).expanduser()
KEYS = ["n", "target_size", "loading_prob", "seed", "algorithm", "pattern",
        "speed", "spacing_um", "noise", "lifetime", "pickup_success", "putdown_success", "initial_mode", "tweezer_count",
        "pickup_time_us", "putdown_time_us", "accel_time_us", "decel_time_us"]
PATTERNS = [("Centered square", "center"), ("Checkerboard", "checkerboard"),
            ("Horizontal stripes", "horizontal"), ("Vertical stripes", "vertical")]
ALGORITHMS = [(name, key) for key, name in ALGORITHM_NAMES.items()]
ALGORITHM_INFO = {
    "parallel": "Distance-cost matching followed by parallel scheduling. Supports all four target patterns; matching cost and actual transport time measure different things.",
    "hungarian": "Distance-cost matching followed by sequential transport. Supports all four target patterns; obstacle avoidance and intermediate moves can increase the traveled distance.",
    "lbap": "Experimental implementation that prioritizes reducing the longest matching distance. The native parallel plan has known collision issues, so this interface executes it conservatively with one tweezer. Judge it by the actual target fill.",
    "generalized": "Recursively alternates row and column occupancy balancing. Supports all four target patterns; useful for comparing transport batches with matching-based algorithms.",
    "bcv2": "Optimized balancing and central compaction with batched transport. Supports centered square targets only.",
    "bc": "Original balancing and central compaction. Supports centered square targets only; included for comparison with the optimized version.",
}

CSS = """
body { background:#eceef0 !important; }
.gradio-container { width:100% !important; max-width:1440px !important; margin:auto !important;
    font-family:Arial,-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif !important; }
#hero { padding:12px 2px 8px; border-bottom:1px solid #bdc4cc; margin-bottom:10px; }
#hero h1 { font-size:23px; font-weight:600; color:#222b34; margin:0 0 6px; }
#hero p { color:#56616d; font-size:13px; line-height:1.6; margin:0; }
#controls { background:#f7f8fa; padding:16px; border:1px solid #bcc4cc;
    border-radius:3px; gap:10px; box-shadow:none; }
#controls h2 { font-size:15px; color:#222b34; margin:0; border-bottom:1px solid #c8ced5; padding-bottom:8px; }
#controls .gradio-slider, #controls .gradio-number, #controls .gradio-dropdown,
#controls .gradio-checkbox { box-shadow:none; }
#controls input { accent-color:#0072bd; }
#controls button.primary { background:#0072bd !important; border-color:#005d9b !important; }
#controls button { min-height:35px; border-radius:3px; font-size:13px; }
#controls input, #controls .wrap, #controls .form { border-radius:3px !important; }
#parameter-status p { font-size:12px; line-height:1.6; margin:0; }
#control-note p { font-size:12px; color:#74858e; line-height:1.6; }
#initial-note p { font-size:12px; color:#526171; line-height:1.5; }
#algorithm-note p, #tweezer-note p { font-size:12px; color:#526171; line-height:1.5; margin:0; }
#comparison-panel, #reference-panel, #benchmark-panel { border:1px solid #bcc4cc; border-radius:3px; background:#f7f8fa; }
#comparison-status p { font-size:12px; line-height:1.6; }
#comparison-table, #benchmark-table { min-width:0; max-width:100%; }
#comparison-table th, #benchmark-table th { white-space:nowrap !important; word-break:normal !important; }
#algorithm-reference { overflow-x:auto; font-size:12px; }
#presets { gap:8px; }
#page-note p { color:#63717e; font-size:11px; text-align:center; line-height:1.6; }
@media (max-width:720px) {
  .gradio-container { padding:12px !important; }
  #hero { padding:8px 2px 4px; }
  #hero h1 { font-size:20px; }
  #controls { padding:12px; }
}
"""


def as_config(values, layout=None):
    config = dict(zip(KEYS, values))
    for key in ("n", "target_size", "seed", "tweezer_count"):
        value = config[key]
        if isinstance(value, (int, float)) and float(value).is_integer():
            config[key] = int(value)
    if isinstance(config.get("n"), int) and isinstance(config.get("target_size"), int):
        config["target_size"] = min(config["n"], config["target_size"])
    allowed = ALGORITHM_PATTERNS.get(config.get("algorithm"), ())
    if allowed and config.get("pattern") not in allowed:
        config["pattern"] = allowed[0]
    if config.get("algorithm") not in MULTI_TWEEZER_ALGORITHMS:
        config["tweezer_count"] = 1
    config["initial_matrix"] = None
    if config.get("initial_mode") == "manual":
        matrix = (layout or {}).get("matrix", [])
        n = config.get("n", 10)
        if isinstance(n, int) and 4 <= n <= 24:
            config["initial_matrix"] = [[matrix[r][c] if r < len(matrix) and c < len(matrix[r]) else 0
                                         for c in range(n)] for r in range(n)]
    return config


def show_preview(*args):
    config = as_config(args[:-1], args[-1])
    result = preview(config)
    layout = ({"n": result["n"], "matrix": result["initial"]}
              if result["initial"] else args[-1])
    prefix = "**Initial preview / Parameters changed**" if result['summary']['status'] == 'preview' else "**Invalid parameters or preview error**"
    return result, layout, prefix + " · " + result["summary"]["message"]


def capture_request(*args):
    return as_config(args[:-1], args[-1])


def refresh_preview(*args):
    """A delayed input refresh must not overwrite a completed matching run."""
    values, layout, result = args[:-2], args[-2], args[-1]
    if result and as_config(values, layout) == result.get("config"):
        status = result.get('summary', {}).get('status')
        note = "**Simulation ready** · Click Play or step through the transport batches." if status in ('success', 'incomplete') else "**Please adjust the parameters** · " + result.get('summary', {}).get('message', '')
        return gr.skip(), gr.skip(), note
    return show_preview(*values, layout)


def run_simulation(config):
    try:
        result = simulate(config)
    except Exception:
        result = {
            "config": config, "n": config.get("n", 10), "initial": [], "target": [],
            "frames": [], "summary": {"status": "algorithm_error",
                "message": "The simulation could not finish. Check the parameters and try again.", "initial_count": 0,
                "target_count": 0, "remaining": 0, "filled": 0,
                "total_batches": 0, "executed_batches": 0, "total_moves": 0,
                "simulated_time": 0, "planned_success": False},
        }
    return result


def begin_run():
    return gr.Button(interactive=False), "**Computing** · Preparing the atom transport trajectory…"


def publish_result(*args):
    values, layout, result = args[:-2], args[-2], args[-1]
    config = as_config(values, layout)
    if config != result.get("config"):
        shown, layout, status = show_preview(*values, layout)
        status = "**Parameters changed during computation** · The latest initial preview is shown. Run the simulation again."
    else:
        shown = result
        layout = {"n": result["n"], "matrix": result["initial"]}
        failed = result["summary"]["status"] in {"invalid", "algorithm_error", "insufficient", "blocked"}
        status = ("**Please adjust the parameters** · " + result["summary"]["message"] if failed
                  else "**Simulation ready** · Click Play or step through the transport batches.")
    return shown, layout, status, gr.Button(interactive=True)


def edit_initial(n, target_size, loading_prob, seed, algorithm, pattern, speed,
                 spacing_um, noise, lifetime, pickup_success, putdown_success,
                 initial_mode, tweezer_count, pickup_time_us, putdown_time_us,
                 accel_time_us, decel_time_us, layout, evt: gr.EventData):
    # Gradio injects EventData into positional parameters, not keyword-only args.
    values = [n, target_size, loading_prob, seed, algorithm, pattern, speed,
              spacing_um, noise, lifetime, pickup_success, putdown_success, initial_mode, tweezer_count,
              pickup_time_us, putdown_time_us, accel_time_us, decel_time_us]
    config = as_config(values, layout)
    matrix = evt._data.get("matrix") if isinstance(evt._data, dict) else None
    if config["initial_mode"] == "manual" and isinstance(matrix, list) and len(matrix) == config["n"]:
        edited = dict(config, initial_matrix=matrix)
        checked = preview(edited)
        if checked["summary"]["status"] == "preview":
            return checked, {"n": checked["n"], "matrix": checked["initial"]}, "**Manual initial state updated** · Click grid sites to add or remove atoms, then click Run simulation to compute the trajectory."
    return show_preview(*values, layout)


def clear_initial(*args):
    values = args[:-1]
    n = int(values[0])
    return show_preview(*values, {"n": n, "matrix": [[0] * n for _ in range(n)]})


def preset(kind):
    config = dict(DEFAULT_CONFIG)
    if kind == "loss":
        config.update(noise=True, speed=0.001, lifetime=0.01,
                      pickup_success=90, putdown_success=90)
    return [config[k] for k in KEYS]


def resize_target(n, target_size):
    return gr.Slider(maximum=int(n), value=min(int(n), int(target_size)))


def constrain_pattern(algorithm, pattern):
    choices = [p for p in PATTERNS if p[1] in ALGORITHM_PATTERNS.get(algorithm, ())]
    value = pattern if any(p[1] == pattern for p in choices) else choices[0][1]
    return gr.Dropdown(choices=choices, value=value)


def algorithm_note(algorithm):
    return ALGORITHM_INFO.get(algorithm, "Select an algorithm.")


def tweezer_note(algorithm):
    if algorithm in MULTI_TWEEZER_ALGORITHMS:
        return "Supports multiple tweezers up to the selected limit. AOD trajectory conflicts and occupancy are checked; conflicting moves and moves exceeding the limit are split into batches. Empty intersections also count as tweezers."
    return "This interface executes this algorithm with one tweezer. Paths are still checked; execution stops with an explanation if a safe move is unavailable."


def constrain_tweezers(algorithm, count):
    enabled = algorithm in MULTI_TWEEZER_ALGORITHMS
    value = max(1, min(MAX_TWEEZERS, int(count or 1))) if enabled else 1
    return gr.Slider(value=value, interactive=enabled), tweezer_note(algorithm)


def begin_comparison():
    return gr.Button(interactive=False), "**Comparing** · Running each algorithm from the same initial state. You can still adjust parameters and view the animation."


def comparison_note(*args):
    values, layout, result = args[:-2], args[-2], args[-1]
    if not result:
        return "No comparison yet. Freeze the current initial state and run each algorithm that supports the selected target pattern."
    config = result.get("config", {})
    unchanged = as_config(values, layout) == config
    prefix = "**Comparison complete**" if unchanged else "**Parameters changed; compare again** · The table retains the previous comparison snapshot"
    pattern = dict((value, label) for label, value in PATTERNS).get(config.get("pattern"), "")
    if config.get("pattern") == "center":
        pattern += f" {config.get('target_size')}×{config.get('target_size')}"
    atoms = sum(sum(row) for row in result.get("initial_matrix", []))
    context = f"{config.get('n')}×{config.get('n')} array, {pattern}, {atoms} initial atoms, seed {config.get('seed')}, tweezer limit {config.get('tweezer_count', 1)}, " + ("errors enabled" if config.get("noise") else "ideal mode")
    if result.get("status") == "invalid":
        return "**Invalid comparison parameters** · " + result.get("message", "Please adjust the parameters.")
    return prefix + " · " + context + ".\n\n" + result.get("footnote", "")


def publish_comparison(*args):
    result = args[-1] or {}
    return result.get("table_rows", []), comparison_note(*args), gr.Button(interactive=True)


def benchmark_note(*args):
    values, layout, trials, result = args[:-3], args[-3], args[-2], args[-1]
    if not result:
        return "No trial statistics yet. In each trial, algorithms share the same initial state. Insufficient-atom runs and safety stops are included in the trial count."
    unchanged = as_config(values, layout) == result.get("config") and trials == result.get("trials")
    prefix = "" if unchanged else "**Settings changed; the previous statistics snapshot is shown below.** "
    config = result.get("config", {})
    mode = "new random loading in each trial" if config.get("initial_mode") == "random" else "fixed manual initial state, varying only the error seed"
    return prefix + result.get("message", "") + f" Starting seed {config.get('seed')}; {mode}."


def capture_benchmark(*args):
    return {"config": as_config(args[:-2], args[-2]), "trials": args[-1]}


def run_benchmark(request, progress=gr.Progress()):
    return benchmark_algorithms(request["config"], request["trials"], on_progress=progress)


def publish_benchmark(*args):
    result = args[-1] or {}
    path = export_csv(result, STATE_DIR / "exports")
    return result.get("rows", []), benchmark_note(*args), gr.Button(interactive=True), gr.DownloadButton(value=path, interactive=bool(path))


def refresh_notes(*args):
    inputs, trials, compared, benchmarked = args[:-3], args[-3], args[-2], args[-1]
    return comparison_note(*inputs, compared), benchmark_note(*inputs, trials, benchmarked)


def build_app():
    initial_preview = preview(DEFAULT_CONFIG)
    with gr.Blocks(title="atommovr · Atom Rearrangement Demo", analytics_enabled=False, fill_width=True) as demo:
        gr.Markdown(f"# atommovr · Atom Rearrangement Lab v{__version__}\nPreview the initial state and target → Run simulation → Play the transport trajectory | Single-species tweezer arrays", elem_id="hero")
        layout_state = gr.State({"n": 10, "matrix": initial_preview["initial"]})
        request_state = gr.State(dict(DEFAULT_CONFIG))
        result_state = gr.State(None)
        comparison_request = gr.State(None)
        comparison_result = gr.State(None)
        benchmark_request = gr.State(None)
        benchmark_result = gr.State(None)
        with gr.Row(equal_height=False):
            with gr.Column(scale=1, min_width=310, elem_id="controls"):
                gr.Markdown("## Parameters")
                with gr.Row(elem_id="presets"):
                    ideal = gr.Button("Ideal rearrangement", size="sm", min_width=100)
                    lossy = gr.Button("High-loss demo", size="sm", min_width=100)
                algorithm = gr.Dropdown(ALGORITHMS, value="parallel", label="Rearrangement algorithm", filterable=False)
                algorithm_info = gr.Markdown(algorithm_note("parallel"), elem_id="algorithm-note")
                tweezer_count = gr.Slider(1, MAX_TWEEZERS, value=DEFAULT_CONFIG["tweezer_count"], step=1,
                                         label="Moving tweezer limit", info="Maximum simultaneously active tweezers, including empty intersections")
                tweezer_info = gr.Markdown(tweezer_note("parallel"), elem_id="tweezer-note")
                pattern = gr.Dropdown(PATTERNS, value="center", label="Target pattern", filterable=False)
                n = gr.Slider(4, 24, value=10, step=1, label="Array side length", info="N × N tweezer sites")
                target_size = gr.Slider(1, 10, value=4, step=1, label="Centered target side length", info="Used for centered square targets only")
                loading_prob = gr.Slider(0, 1, value=.6, step=.01, label="Atom loading probability")
                seed = gr.Number(value=DEFAULT_CONFIG["seed"], precision=0, minimum=0, maximum=2**32-1, label="Random seed", info="The same parameters and seed reproduce the same result")
                initial_mode = gr.Dropdown([("Random loading", "random"), ("Manual placement", "manual")],
                                           value="random", label="Initial atom distribution", filterable=False)
                gr.Markdown("The plot updates as parameters change. In manual mode, click grid sites to add or remove atoms. Resizing the array preserves sites that remain within its bounds.", elem_id="initial-note")
                with gr.Row(visible=False) as edit_tools:
                    edit_view = gr.Button("Edit initial state", size="sm", min_width=80)
                    clear = gr.Button("Clear placement", size="sm", min_width=80)
                with gr.Accordion("Physics and errors", open=False):
                    speed = gr.Slider(.001, 1, value=.1, step=.001, label="Tweezer speed (µm/µs)")
                    spacing_um = gr.Slider(1, 20, value=5, step=.1, label="Array spacing (µm)")
                    with gr.Accordion("Operation durations (advanced)", open=False):
                        pickup_time_us = gr.Number(value=0, minimum=0, maximum=10000, label="Pickup time (µs)")
                        putdown_time_us = gr.Number(value=0, minimum=0, maximum=10000, label="Putdown time (µs)")
                        accel_time_us = gr.Number(value=0, minimum=0, maximum=10000, label="Acceleration overhead (µs)")
                        decel_time_us = gr.Number(value=0, minimum=0, maximum=10000, label="Deceleration overhead (µs)")
                        gr.Markdown("Operation durations follow the library rules for consecutive moves. They also apply when errors are disabled. Acceleration and deceleration add time overhead; they do not model a velocity profile.")
                    noise = gr.Checkbox(value=False, label="Enable errors and atom loss")
                    lifetime = gr.Number(value=30, minimum=.001, maximum=3600, label="Atom lifetime (s)", interactive=False)
                    pickup_success = gr.Slider(0, 100, value=99, step=.1, label="Pickup success (%)", interactive=False)
                    putdown_success = gr.Slider(0, 100, value=99, step=.1, label="Putdown success (%)", interactive=False)
                    gr.Markdown("The High-loss demo deliberately exaggerates losses for teaching. Slower playback and pausing do not increase simulated loss.", elem_id="control-note")
                run = gr.Button("Run simulation", variant="primary", interactive=False)
                new_seed = gr.Button("New random distribution")
                parameter_status = gr.Markdown("⏳ Preparing the default demo…", elem_id="parameter-status")
            with gr.Column(scale=2, min_width=320):
                player = gr.HTML(
                    value=initial_preview,
                    html_template=(HERE / "player.html").read_text(),
                    css_template=(HERE / "player.css").read_text(),
                    js_on_load=(HERE / "player.js").read_text(),
                    apply_default_css=False,
                    elem_id="atom-player", padding=False,
                )
        with gr.Accordion("Algorithm comparison · Single trial", open=False, elem_id="comparison-panel"):
            gr.Markdown("Compare how algorithms handle the same atom array under identical initial, target, and physical conditions. This table describes one scenario; use the repeated trials below to explore variation.")
            compare = gr.Button("Compare all available algorithms", size="sm")
            comparison_status = gr.Markdown("No comparison yet. Freeze the current initial state and run each algorithm that supports the selected target pattern.", elem_id="comparison-status")
            comparison_table = gr.Dataframe(value=[], headers=TABLE_HEADERS,
                                           datatype=["str", "str", "str"] + ["number"] * (len(TABLE_HEADERS) - 3),
                                           interactive=False, wrap=False, column_widths=[240, 130, 150, 100, 120, 100, 130, 190, 200],
                                           elem_id="comparison-table", max_height=420, show_row_numbers=False, show_label=False, type="array", buttons=["copy", "fullscreen"])
        with gr.Accordion("Algorithm comparison · Repeated trials", open=False, elem_id="benchmark-panel"):
            gr.Markdown("Repeat trials with consecutive seeds to observe target fill, atom loss, and the duration of successful runs. Random mode reloads each trial; manual mode preserves the same placement. Manual trials are identical when errors are disabled.")
            trials = gr.Slider(1, MAX_TRIALS, value=5, step=1, label="Trials per algorithm")
            with gr.Row():
                benchmark_run = gr.Button("Run repeated trials", size="sm")
                benchmark_download = gr.DownloadButton("Download trial results CSV", interactive=False, size="sm")
            benchmark_status = gr.Markdown(benchmark_note(*[DEFAULT_CONFIG[k] for k in KEYS], None, 5, None))
            benchmark_table = gr.Dataframe(value=[], headers=BENCHMARK_HEADERS, datatype="str", interactive=False,
                                          wrap=False, column_widths=[240, 110, 170, 150, 160, 200, 140, 220],
                                          elem_id="benchmark-table", max_height=420, show_row_numbers=False, show_label=False, type="array", buttons=["copy", "fullscreen"])
            gr.Markdown("Full-target fraction = trials with every target site occupied at the end / executed trials. Mean fill includes insufficient-atom, stopped, and incomplete runs. Mean successful time uses only full-target runs, with its sample count shown. Short failed runs do not imply a speed advantage. Algorithms consume noise samples in different orders; these are descriptive statistics from a finite sample. After about two minutes, no new executions start and completed records are retained.")
        with gr.Accordion("Algorithms and references", open=False, elem_id="reference-panel"):
            reference = HERE / "ALGORITHMS.md"
            gr.Markdown(reference.read_text() if reference.exists() else "Algorithm notes are being prepared.", elem_id="algorithm-reference")
        gr.Markdown("Single-species demo · Core algorithms and simulation model from [atommovr](https://github.com/bernienlab/atommovr) · Atoms outside the target are retained · Error mode executes the original plan once", elem_id="page-note")

        controls = [n, target_size, loading_prob, seed, algorithm, pattern, speed,
                    spacing_um, noise, lifetime, pickup_success, putdown_success, initial_mode, tweezer_count,
                    pickup_time_us, putdown_time_us, accel_time_us, decel_time_us]
        preview_inputs = controls + [layout_state]
        preview_outputs = [player, layout_state, parameter_status]
        gr.on(triggers=[c.input for c in controls], fn=refresh_preview,
              inputs=preview_inputs+[result_state], outputs=preview_outputs,
              trigger_mode="always_last", concurrency_limit=1, concurrency_id="configuration",
              show_progress="hidden", api_visibility="private")
        n.change(resize_target, inputs=[n, target_size], outputs=target_size, queue=False, api_visibility="private")
        algorithm.change(constrain_pattern, inputs=[algorithm, pattern], outputs=pattern, queue=False, api_visibility="private")
        algorithm.change(algorithm_note, algorithm, algorithm_info, queue=False, api_visibility="private")
        algorithm.change(constrain_tweezers, [algorithm, tweezer_count], [tweezer_count, tweezer_info],
                         queue=False, api_visibility="private")
        pattern.change(lambda p: gr.Slider(interactive=p == "center"), pattern, target_size,
                       queue=False, api_visibility="private")
        noise.change(lambda enabled: [gr.Number(interactive=enabled), gr.Slider(interactive=enabled), gr.Slider(interactive=enabled)],
                     inputs=noise, outputs=[lifetime, pickup_success, putdown_success], queue=False, api_visibility="private")
        ideal_event = ideal.click(lambda: preset("ideal"), outputs=controls, queue=False, api_visibility="private").then(
            show_preview, inputs=preview_inputs, outputs=preview_outputs,
            concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        lossy_event = lossy.click(lambda: preset("loss"), outputs=controls, queue=False, api_visibility="private").then(
            show_preview, inputs=preview_inputs, outputs=preview_outputs,
            concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        initial_mode.change(lambda mode: [gr.Slider(interactive=mode == "random"),
                                         gr.Button(interactive=mode == "random"), gr.Row(visible=mode == "manual")],
                            initial_mode, [loading_prob, new_seed, edit_tools], queue=False, api_visibility="private")
        player.edit(edit_initial, inputs=preview_inputs, outputs=preview_outputs,
                    concurrency_limit=1, concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        edit_view.click(show_preview, inputs=preview_inputs, outputs=preview_outputs,
                        concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        clear.click(clear_initial, inputs=preview_inputs, outputs=preview_outputs,
                    concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        seed_event = new_seed.click(lambda: secrets.randbelow(2**32), outputs=seed, queue=False, api_visibility="private").then(
            show_preview, inputs=preview_inputs, outputs=preview_outputs,
            concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        for event in (ideal_event, lossy_event, seed_event):
            event.then(refresh_notes, inputs=preview_inputs+[trials, comparison_result, benchmark_result],
                       outputs=[comparison_status, benchmark_status], concurrency_id="configuration",
                       show_progress="hidden", api_visibility="private")

        compute = run.click(begin_run, outputs=[run, parameter_status], queue=False, api_visibility="private")
        compute = compute.then(capture_request, inputs=preview_inputs, outputs=request_state,
                               concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        compute = compute.then(run_simulation, inputs=request_state, outputs=result_state,
                               api_name="simulate", concurrency_limit=1, concurrency_id="simulation", show_progress="minimal")
        compute.then(publish_result, inputs=preview_inputs+[result_state], outputs=preview_outputs+[run],
                     concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        loaded = demo.load(run_simulation, inputs=request_state, outputs=result_state,
                           concurrency_limit=1, concurrency_id="simulation", show_progress="minimal", api_visibility="private")
        loaded.then(publish_result, inputs=preview_inputs+[result_state], outputs=preview_outputs+[run],
                    concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        gr.on(triggers=[c.input for c in controls]+[layout_state.change], fn=comparison_note,
              inputs=preview_inputs+[comparison_result], outputs=comparison_status, trigger_mode="always_last",
              concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        comparing = compare.click(begin_comparison, outputs=[compare, comparison_status], queue=False, api_visibility="private")
        comparing = comparing.then(capture_request, inputs=preview_inputs, outputs=comparison_request,
                                  concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        comparing = comparing.then(compare_algorithms, inputs=comparison_request, outputs=comparison_result,
                                  concurrency_id="simulation", concurrency_limit=1, show_progress="minimal", api_visibility="private")
        comparing.then(publish_comparison, inputs=preview_inputs+[comparison_result],
                       outputs=[comparison_table, comparison_status, compare],
                       concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        gr.on(triggers=[c.input for c in controls]+[layout_state.change, trials.input], fn=benchmark_note,
              inputs=preview_inputs+[trials, benchmark_result], outputs=benchmark_status, trigger_mode="always_last",
              concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        benchmarking = benchmark_run.click(lambda: [gr.Button(interactive=False), "**Running trials** · Comparing algorithms under the same conditions in each trial."],
                                          outputs=[benchmark_run, benchmark_status], queue=False, api_visibility="private")
        benchmarking = benchmarking.then(capture_benchmark, inputs=preview_inputs+[trials], outputs=benchmark_request,
                                         concurrency_id="configuration", show_progress="hidden", api_visibility="private")
        benchmarking = benchmarking.then(run_benchmark, inputs=benchmark_request, outputs=benchmark_result,
                                         concurrency_id="simulation", concurrency_limit=1, show_progress="minimal", api_visibility="private")
        benchmarking.then(publish_benchmark, inputs=preview_inputs+[trials, benchmark_result],
                          outputs=[benchmark_table, benchmark_status, benchmark_run, benchmark_download],
                          concurrency_id="configuration", show_progress="hidden", api_visibility="private")
    return demo


def existing_url():
    try:
        info = json.loads((STATE_DIR / "server.json").read_text())
        url = info["url"]
        if not url.startswith("http://127.0.0.1:"):
            return None
        with urllib.request.urlopen(url + "atommovr-health", timeout=1) as response:
            health = json.load(response)
            if (health.get("application") == "atommovr-ui" and
                    health.get("version") == __version__):
                return url
    except (OSError, ValueError, KeyError):
        pass
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    url = existing_url()
    if url:
        print("Demo already running: " + url, flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        return
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("GRADIO_TEMP_DIR", str(STATE_DIR / "cache"))
    demo = build_app().queue(default_concurrency_limit=1, max_size=32)
    theme = gr.themes.Base(primary_hue="blue", secondary_hue="gray", neutral_hue="gray", radius_size="sm", text_size="sm", spacing_size="sm")
    server, url, _ = demo.launch(server_name="127.0.0.1", share=False,
                               inbrowser=False, prevent_thread_lock=True,
                               theme=theme, css=CSS, footer_links=[], show_error=False,
                               ssr_mode=False)

    @server.get("/atommovr-health")
    def health():
        return {"application": "atommovr-ui", "version": __version__}

    (STATE_DIR / "server.json").write_text(json.dumps({"url": url, "pid": os.getpid()}))
    print("Atom rearrangement demo started: " + url, flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        demo.close()


if __name__ == "__main__":
    main()
