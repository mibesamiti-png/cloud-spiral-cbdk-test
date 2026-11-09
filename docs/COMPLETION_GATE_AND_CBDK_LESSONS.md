# CBDK-EXP-CLOUD-001 — Completion gate and transferable lessons

## User-agreed stop rule (2026-11-09 JST)

**When the active roadmap reaches 100% accepted completion, a subsequent "続けてー" must be answered with "今回のロードマップは100%完了しているよー！"** Do not silently invent more tasks, versions, or extend that finished roadmap. A new version needs a **separate newly agreed roadmap**.

**Scope accounting:**
- Original v0.3 MVP: CLD-01..05, **4/5=80% formally complete**. CLD-04 is 98%, pending real Windows user UI / acceptance. Never round it to 100 just because CI is green.
- Post-MVP CLD-06 (v0.4 puffy): **90% review pending**, counted separately. Achieving CLD-06 100% does not rewrite the v0.3 MVP's denominator and vice versa.
- Long-term v3.0 design ambitions are also separate. Do not declare them complete because the short-term roadmap completed.

**At the 100% gate, before reporting final acceptance:**
1. Re-read roadmap and Notion task statuses; match each original acceptance criterion to verified evidence. Report unresolved items instead of blindly editing progress.
2. Record what was implemented, which CI jobs actually ran, user/Windows/manual GUI acceptance if required, final artifact links, code SHA, known limitations and what was explicitly NOT tested.
3. Write a retrospective with **hard parts, symptoms, root cause, attempts that failed, final fix, how to do it better next time, and reusable CBDK engineering guidance**.
4. Update both the experiment handoff and the CBDK Notion learnings page. **Do not modify CBDK's main/development branch, STATE, ABCD tasks or merge a PR as part of this learning note.**
5. Tell the user **100% complete**, link lessons, and stop until a **new request with explicit scope** arrives.

## Observed lessons, not hypothetical defects

| Hard problem | Evidence/what happened | Next-time playbook |
| --- | --- | --- |
| Winding/coherent topology | Original v0.2 showed 256 conflicting adjacent edges; CBDK static AST/audit did not itself diagnose geometry | Add mesh fixtures for winding, boundary/non-manifold, signed volume, degenerate faces, and exact legacy geometry regression |
| Blender object identity | Native test assumed `bpy.data.objects` follows creation order; false | Select generated objects by stable tags, selection, locations, and pointers, never iteration order |
| Blender cancel/error wrapper | Operator returning CANCELLED while reporting ERROR may cause Python `bpy.ops` to raise RuntimeError | In fault-injection tests, assert the known error, object and mesh cleanup, original selection/active restoration, then successful retry |
| CI infrastructure failures | Private-repo Actions jobs had runner_name absent and steps=0; source not executed | Classify runner/pre-start failures separately from Python/Blender tests; require source SHA, actual job logs and terminal run conclusion |
| GUI vs API registration | Successful class registration didn't prove the panel was visible or operable | Layer tests: static AST → native Blender 3 versions → graphical Xvfb GUI → Windows final user acceptance |
| Black screenshots | Blender screenshot operator generated all-black PNG under Xvfb | Use external X11 capture plus pixel-content validation and human visual inspection |
| Input intercepted by modal | Blender first-use Quick Setup obscured the GUI and keyboard Ctrl+Z | Dismiss/detect first-run overlays before sending UI shortcuts, then assert 1→0→1 generated-lobe counts |
| Artistic vs topology success | v0.4 is watertight and 2.83x taller, 2.48x more volume, but still a rounded carved mound | Keep numerical geometry quality and human aesthetic acceptance as separate gates; add style/shape review criteria |
| No human-time baseline | Original MVP estimated 60–120 min but full manual work time and time saved by CBDK weren't measured | Capture per-stage start/end, active work, wait, rerun and repair times; never invent a productivity percentage |
| Public/Private boundary | Repo changed from Private to Public to regain Actions functionality | Review source, uploaded assets, paths and artifacts before publicity. Never use private files for testing in a public repo |

## Proposed CBDK improvements — suggestions, NOT implemented in CBDK

- **QA-MESH**: reproducible Blender mesh tests for winding, degeneration, volume, legacy comparison.
- **QA-FAILURE**: reusable mid-build injected-exception and clean rollback fixtures.
- **QA-GUI**: optional Xvfb Blender + first-start modal handling + non-black screenshot + keyboard Undo/Redo + truthful Windows gap.
- **QA-DIAGNOSTICS**: categorize runner, test harness, addon, and environment failures with real CI logs.
- **OPS-DoD**: milestone-specific 100% gate, stop behavior, user acceptance, and mandatory retrospective/work-time capture.

**Important:** All changes to the main CBDK repository require its established ABCD ownership, QA and integration process; this file is not an authorized feature assignment.

## Sources / continuation

- [Cloud experiment master roadmap](https://app.notion.com/p/412948b7493781d092b2eb7dc2f1e048)
- [CBDK Notion learning and completion-gate page](https://app.notion.com/p/413948b7493781f68756d61534df149b)
- [CLD-06 v0.4 evidence](https://app.notion.com/p/413948b749378104a06ac74679c8b9dd)
- [Successful 5-job native/GUI CI](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42540369098)
- [Experiment draft PR #1](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/pull/1)

**Status snapshot:** original MVP 80% formal completion (CLD-04 at 98%); optional subsequent CLD-06 is 90%. A future final retrospective must replace these as-of values with verified milestone acceptance evidence, not assumptions.


## 2026-11-09 — Windows native Blender QA (new accepted evidence)

**Goal:** Reduce CLD-04's Windows verification gap without opening the user's own Windows PC. No new roadmap feature is created here, and **completion remains below 100% until actual Windows interactive GUI acceptance**.

- [Push CI #42542713024](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42542713024), [draft-PR CI #42542720133](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42542720133), tested SHA `1a24f90206bf49db41863e41f231ae1be3175c39`: **six of six jobs SUCCESS** in each workflow.
- Added `windows-blender-native` on GitHub-hosted **Windows Server 2022** using an **official Blender 4.4.3 Windows x64 portable ZIP**. Official checksum manifest is downloaded and SHA-256 checked before extraction.
- Windows real Blender logs confirm `CLOUD_REAL_BLENDER: PASS`, `CLOUD_REAL_BLENDER_QUALITY: PASS`, `CLOUD_PUFF_NATIVE: PASS`, and the aggregate `CLOUD_WINDOWS_REAL_BLENDER_ALL_GATES: PASS`.
- Windows native smoke: **12 PASS** (registration, operator/panel classes, presets, single/three-lobe generation, modified parameters, topology and cleanup). Windows robustness: **9 recorded PASS**, including a check explicitly declaring interactive Undo **NOT_RUN**; not a Windows keyboard Undo success. Windows old/new comparison: **5 PASS** for exact CLASSIC compatibility, PUFFY height/volume, outline controls and rim roundness.
- The Windows job independently validates all three JSON reports and uploads generated test scenes plus logs. [Windows real-Blender evidence artifact](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42542713024/artifacts/13641948143).
- Linux Blender 4.4.3/4.5.15/5.2.1 real native jobs, Linux Xvfb GUI screenshot and keyboard Undo/Redo, and CBDK AST/audit also passed in the same CI run.
- **Important failure and lesson:** The first Windows runs crashed after all single/three-lobe geometry smoke tests, when a Workbench preview called OpenGL. The Windows GitHub runner had no OpenGL vendor (`No OpenGL vendor detected` and `EXCEPTION_ACCESS_VIOLATION`). This is a **runner graphics limitation** observed at rendering time, not evidence that generated meshes were invalid.
- **Fix:** `CLOUD_SKIP_RENDER=1` is set only on the Windows CI job; `native_smoke.py` and `puffy_geometry_compare.py` record the omitted GPU preview explicitly while preserving all geometry, rollback and exact legacy compatibility assertions. Linux preview and real graphical GUI jobs still test rendering and screenshots; they are not skipped.
- **CBDK reusable practice:** GPU-dependent preview must be separated from native geometry tests. Report `SKIPPED_NO_GPU` honestly and treat OS/runtime crashes independently from addon failures. Include Windows/CPU-only native validation alongside Linux GUI rendering rather than asking the user to troubleshoot a headless graphics runner.

**Current acceptance:** CLD-04 remains `検証待ち` at its previously estimated 98%, pending Windows user-interactive N-panel and mouse/Undo feedback. CLD-06 remains 90% review pending (aesthetic result and shape/print suitability). The original MVP remains **4/5 = 80%** formally finished; neither milestone has reached 100%. Do not silently start another roadmap on a generic "続けてー" after completion.


## 2026-11-09 — Local human-acceptance evidence: reliable Blender QA kit

**Validated in real CI before final user signoff:**
- [Run #42545843598](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42545843598): **6/6 jobs SUCCESS**, test source SHA `b1d88dc1f968fe0c8a77a7dd139c31b2987fc2ea`. Validates both Windows Blender 4.4.3 in background and actual Linux Xvfb graphical Blender 4.4.3.
- Added a portable [Windows one-click review kit ZIP](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42545843598/artifacts/13643057294): `run_windows_review.bat`, v0.4 source, `windows_review_session.py`, Japanese README.
- The kit opens an isolated `--factory-startup` Blender session and constructs a 1+3 cloud review scene. No existing user .blend files are overwritten. The Cloud QA panel contains four CLD04 acceptance choices and two CLD06 artistic choices with `NOT_TESTED` initial state, plus an optional note and a local JSON export button.
- Real Windows Blender CI checks the generated 4 objects, review-panel registration, JSON export operator, all unanswered stages `INCOMPLETE`, a `FAIL` -> `REJECTED` transition, and all manual `PASS` -> `ACCEPTED` **only when every required check is explicitly marked**. The synthetic report created in the CI test is deleted instead of distributing fabricated human acceptance.
- Linux Xvfb GUI CI checks a live GUI window exists, the Cloud QA panel is registered, review samples are created, and default states are `INCOMPLETE`. This **does not** simulate the user's Windows mouse clicks.

**Hardest part / actual failure:**
The first GUI run failed with `typing.get_type_hints failed with: CLOUDQA_ReviewState` / `NameError: EnumProperty is not defined`. The review script used `from __future__ import annotations`, which caused Blender's RNA registration to evaluate deferred property annotations in a GUI timer/module scope. It passed in the earlier headless run yet failed after graphical startup, showing that test-mode differences matter.

**Actual fix:** Remove deferred annotations for the Blender `PropertyGroup` module so `EnumProperty` is evaluated directly while defining the registered class. Also terminate explicit GUI-smoke failure promptly rather than leaving Blender waiting at a startup modal until the CI timeout; exit cleanly and leave ordinary/manual GUI sessions open for the user. Following the fix, both Windows and Linux GUI CI passed.

**Suggested CBDK practices (not yet implemented in main CBDK):**
1. Generate **reproducible user-acceptance kits** for tasks requiring real UX/aesthetic judgment, with minimal launch steps, safe disposable demo scenes and exportable evidence.
2. Include **strict manual states `NOT_TESTED`, `FAIL`, `PASS`** and distinguish automation smoke logs from signed-off user acceptance. A successful CI must NEVER silently mark human-gated 100%.
3. For Blender addons, test `PropertyGroup` registration in graphical startup and avoid untested deferred annotations in dynamically registered UI classes. Use both background and GUI runs.
4. On failure, output root cause to a log and exit CI nonzero quickly; retain JSON and screenshots without bundling simulated acceptance as if it were user input.
5. Preserve data boundaries: the ZIP and source can be public, but generated user notes and locally recorded GUI evidence must not be auto-uploaded.

**Acceptance still pending:** The original MVP is 4/5=80% (CLD04 98% user Windows interaction pending), plus separate CLD06 at 90% (aesthetic review pending). This kit bridges the final evidence gap but does not itself satisfy it; stop at 100% only after the real outstanding acceptance criteria are met.

[Japanese user instructions](../WINDOWS_REVIEW_README.md) · [Notion local review kit report](https://app.notion.com/p/413948b74937817d9bb6c6b2026ade60)

## 2026-11-09 — Validate the artifact people actually download (one-unzip kit)

**Verified CI:** [GitHub Actions #42547536657](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42547536657) succeeded **6/6 jobs** on SHA `1278c1acdb576f0d66f39694a97da863489f630a`. [One-unzip Windows acceptance kit](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42547536657/artifacts/13643679074).

**The avoidable friction:** `actions/upload-artifact` delivers its own ZIP. Uploading our pre-zipped `Cloud_Spiral_Windows_Review_Kit.zip` created a **ZIP-inside-ZIP** experience, requiring the user to unpack twice.

**Fix:** Keep the inner installer ZIP for CI/debug use, but upload the staging **review-kit folder** as the Actions artifact. The downloaded Actions ZIP now has the BAT, Python addon, review script, and Japanese README directly at its root. The final ZIP was inspected to contain exactly those four paths, with archive CRC integrity verified.

**Production-style test:** After packaging, **unpack the actual staged ZIP on Windows Server 2022**, compare SHA-256 for all four files against staging, then launch the **extracted Python file and bundled addon** in real Blender 4.4.3. The packaged release's startup and local report export passed, generated four test objects, and remained `INCOMPLETE` for both human-gated stages. `CLOUD_PACKAGED_WINDOWS_KIT_SMOKE: PASS` in the Windows job proves the check ran (it is not a human GUI acceptance).

**Data-safety defect fixed:** Earlier JSON filenames had second-level time resolution, risking accidental overwrites on consecutive clicks. Filenames now include microseconds and a collision suffix. Windows Blender tested *two back-to-back exports*, confirmed two different JSON files and no changes to the first, then deleted the synthetic test reports instead of shipping them.

**Reusable CBDK recommendations (not incorporated into CBDK itself):**
- Test final **deliverable bytes after extraction**, not merely source code in the repository.
- Avoid double packaging when the distribution service already wraps files in a ZIP.
- For local feedback/evidence, use collision-safe output filenames and retention; never overwrite user reports by default.
- Distinguish Windows headless packaged smoke, Linux virtual GUI smoke, and unperformed **human Windows acceptance** in progress scoring.

**Still pending:** CLD-04 user Windows N-panel mouse/Undo acceptance (98%) and separate CLD-06 aesthetic review (90%). Original MVP remains 4/5=80%, not 100%. 
