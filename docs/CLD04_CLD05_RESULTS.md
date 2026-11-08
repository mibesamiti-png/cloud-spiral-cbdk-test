# CBDK-EXP-CLOUD-001 — CLD-04 / CLD-05 handoff

**Date:** 2026-11-09 (JST)  
**Status:** Cloud Spiral Lobe Builder v0.3.1 Release Candidate. This repository is PUBLIC by owner choice. No private assets should be uploaded. Keep PR #1 draft and main unchanged.

## Implemented
- Single closed spiral mesh with quad center, spiral groove, and dome
- Three independent lobes with adjustable spread and side scale
- N-panel presets (Soft / Carved / Reset) and foldable advanced controls
- Registration/unregistration, Edit Mode poll guard and failure cleanup
- An independent v0.3.1 Python file alongside the old v0.3 baseline

## Verified in actual Blender
- [Run 42503919900](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42503919900): SUCCESS, all 4 jobs.
- [PR run 42503923375](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42503923375): SUCCESS, all 4 jobs.
- Source-tested HEAD: 8bfdb18558879cc23c44804f43738c0b27228474.
- Blender 4.4.3, 4.5.15 and 5.2.1: **12 basic checks + 9 quality-report checks per version**. The quality-report check for Undo merely declares Undo NOT_RUN without an interactive VIEW_3D, NOT an actual Undo pass.
- Quality gates: RNA min/max, invalid numeric clamp/reject, Edit Mode operator poll, injected second-lobe failure, complete rollback of meshes/objects, selection and active restoration, successful generation after failure.
- CBDK static scanner/audit succeeded. This does not prove mesh appearance or Windows GUI behavior.
- Blender 4.4.3 default mesh evidence: 5,826 verts, 5,888 faces, boundary/nonmanifold/winding-conflict counts all zero.
- EGL_BAD_MATCH warnings occurred while rendering, but PNG and blend saves succeeded.

## Artifacts and reproducibility
- [Installer and CBDK static audit](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42503919900/artifacts/13626612800)
- [Blender 4.4.3 evidence](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42503919900/artifacts/13626177827)
- [Blender 4.5.15 evidence](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42503919900/artifacts/13626323882)
- [Blender 5.2.1 evidence](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42503919900/artifacts/13625898663)
- Installer ZIP SHA-256: 66afdb8e43f9e6d262c706e035a929d8b7f857d6d99e1cbdfe7846039a737dfd.
- Python source SHA-256: 991e0fb429de4e3bb1cf9db26099bf83e54f55eece531d5e1fbc15f8174f5b5d.
- The ChatGPT conversation also has a release candidate bundle including the ZIP, source, Japanese README, preview PNG, QA JSON and Blender test scene.
- Artifacts are kept only about 30 days, until 2026-12-08 UTC.

## Findings and honest limitations
- Earlier failed quality checks were caused by the test expecting a CANCELLED return, while the Blender bpy.ops wrapper raised RuntimeError for an ERROR report on cancellation. The corrected native tests verified rollback and restoration.
- The original v0.2 winding conflicts were found by a separate geometry test, not by CBDK's static auditor. Mesh geometry fixtures are a worthwhile future CBDK feature.
- The preview shows **shallow carved spiral lobes**, not seamless fluffy clouds; the three lobes remain independent.
- Interactive Windows Blender N-panel, clicks, Ctrl+Z/Redo, artistic assessment, self-intersection checks and printing suitability are **NOT VERIFIED**.
- Overall development time and productivity improvement were **not measured**; do not fabricate a speedup percentage.

## Next acceptance gate
1. Install version 0.3.1 in Blender 4.4.3 on Windows and confirm N-panel labels and interactivity.
2. Generate single and three-lobe samples; use the three style presets and custom spread/scale.
3. Verify interactive Undo and Redo; check mesh look and scene safety.
4. Evaluate artistry and, if needed, slicer/print constraints separately.
5. Do not merge draft PR #1 into main without final acceptance or an explicit scope decision.

## Status
CLD-01 PASS; CLD-02 PASS; CLD-03 PASS; **CLD-04 95% (GUI pending)**; CLD-05 PASS (release candidate package and retrospective). **4/5 milestones complete = 80%**.

- [Notion project overview](https://app.notion.com/p/412948b7493781d092b2eb7dc2f1e048)
- [CLD04 full quality report](https://app.notion.com/p/412948b74937818183e1e6250d7e76e0)
- [CLD05 packaging retrospective](https://app.notion.com/p/412948b7493781d99f6cfa1dc042f8c5)


## Latest GUI / Undo automation result (2026-11-09 JST)

**Verified code HEAD:** `4abb4f9c6b981311911eecb8e9d5b7577470df8f`  
**[CI run 42506059041](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42506059041): 5/5 SUCCESS** (3 headless Blender versions, CBDK static scan, 1 Linux virtual GUI test).  
**[PR CI run 42506061850](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42506061850): 5/5 SUCCESS**.

The new `scripts/gui_smoke.py` runs Blender 4.4.3 **without `--background`** inside Xvfb + openbox. It verifies:
- A real GUI Window/VIEW_3D/N sidebar exists and the Cloud Spiral panel is registered.
- Factory-startup first-use modal is dismissed with X11 mouse/keyboard events.
- The addon Soft preset and a single lobe generation work with a true VIEW_3D context.
- An actual window screenshot is **non-black** and shows the Cloud Spiral N-panel and the generated mesh (the test-only startup Cube is hidden).
- `xdotool` Ctrl+Z changes generated-lobe count **1 -> 0**, and Ctrl+Shift+Z changes **0 -> 1**. This measures real X11 shortcut input, not just a mock `bpy.ops.ed.undo()` call.
- JSON checks and the PNG screenshot are saved as [GitHub Actions GUI artifact](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42506059041/artifacts/13627138845).

The first GUI trials failed for important reasons: the native Blender screenshot operator produced a **completely black PNG**, direct `bpy.ops.ed.undo()` failed its `poll()` in a Python timer context, and the startup Quick Setup overlay intercepted X11 keyboard events. Adding openbox, external scrot capture with pixel checks, and dismissal of the startup modal yielded a fully passing native GUI test.

**Visual assessment:** The screenshot shows a shallow, carved, circular spiral lobe, **not a fluffy volumetric cloud**. Do not claim artistic quality was validated. Manual Windows Blender 4.4.3 verification, Windows font/layout, direct mouse click feel, self-intersections and 3D print suitability remain unverified. The reported 5/5 CI success does **not** imply those conditions are satisfied.

**MVP accounting:** CLD-04 `検証待ち` / estimated **98%** due to pending Windows acceptance; CLD-01, 02, 03, 05 complete; **4/5=80%** fully completed stages. Existing Release Candidate remains v0.3.1, without source geometry edits in this GUI testing pass.

[Notion detailed GUI evidence and handoff](https://app.notion.com/p/412948b74937810586ecea123543c4fc).
