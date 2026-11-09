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
