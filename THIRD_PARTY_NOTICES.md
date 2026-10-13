# Third-party notices

## Workbench contributions

This repository contains the English edition of the workbench's interface, player, initial-state editor, recording adapter, conservative scheduler, comparisons, exports, launch tools, and documentation. The English edition shares this implementation with the [Chinese edition](https://github.com/aa3277105147-create/atommovr-ui-zh).

Copyright for the workbench's new code is attributed to **aa3277105147-create** in [LICENSE](LICENSE). This attribution does not extend to upstream algorithms, physical models, or dependency code, and does not claim scientific novelty for standard matching or trajectory-checking methods.

## atommovr

- Project: [bernienlab/atommovr](https://github.com/bernienlab/atommovr)
- Authors: Nikhil K. Harle, Bo-Yu Chen, Bob Bao, and Hannes Bernien
- Upstream copyright: **Copyright (c) 2025 Nikhil K. Harle, Bo-Yu Chen, Bob Bao, and Hannes Bernien**
- License: [MIT](https://github.com/bernienlab/atommovr/blob/cca2553985bb9d81b19cae9b83074df4816502f9/LICENSE)
- Managed-download and reference revision: **cca2553985bb9d81b19cae9b83074df4816502f9**
- Research reference: [Quantum 10, 2177 (2026), DOI 10.22331/q-2026-07-29-2177](https://doi.org/10.22331/q-2026-07-29-2177)

The workbench calls the upstream rearrangement classes, AtomArray operations, stochastic loading, vacuum and tweezer error models, crossed-AOD command utilities, and timing logic. Its adapter records these outcomes, converts units, enforces capacity and conservative safety rules, and judges success from the actual final target occupancy. The adapter does not replace the upstream algorithms or implement a second loss model.

Upstream source is not committed or bundled in this repository. Setup obtains a separate complete checkout, or uses the source selected through ATOMMOVR_SOURCE. User-provided source may differ from the reference revision.

The upstream MIT license requires preservation of its copyright and permission notice when copies or substantial portions of its software are distributed. If an upstream copy is included in a release, preserve its full LICENSE and applicable component notices. The workbench's LICENSE does not replace them. The paper citation is scholarly attribution, separate from license-notice requirements.

## PPSU2023 and other dependencies

Upstream Parallel LBAP uses the PPSU2023 matching component from the complete atommovr source tree. Its matching routines are not workbench contributions. The original source is acknowledged by upstream as *Engineering fast algorithms for the bottleneck matching problem*, by Ioannis Panagiotas, Grégoire Pichon, Somesh Singh, and Bora Uçar. See the [upstream README](https://github.com/bernienlab/atommovr/blob/cca2553985bb9d81b19cae9b83074df4816502f9/README.md) and [PPSU2023 provenance](https://github.com/bernienlab/atommovr/blob/cca2553985bb9d81b19cae9b83074df4816502f9/PPSU2023/README.md), including relevant source-file notices.

This repository does not ship PPSU source, precompiled matching libraries, or generated artifacts. Installed packages, including Gradio, NumPy, SciPy, Matplotlib, xarray, and ImageIO, remain subject to their respective licenses. Their notices are retained with the installed distributions.
