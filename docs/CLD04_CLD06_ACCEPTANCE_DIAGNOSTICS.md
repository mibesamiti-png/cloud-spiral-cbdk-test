# CLD-04 / CLD-06 — Windows panel and v0.4 BVH acceptance diagnostics

**Purpose:** Finish the remaining checks from the already-agreed roadmap, not expand the roadmap or declare 100% without evidence.  
**Owner's stop rule:** Once an explicitly scoped roadmap is fully accepted (100%), a subsequent「続けてー」should report completion instead of automatically inventing a next version.

## Real-Blender CI evidence

- [GitHub Actions 42543692198](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42543692198): **all six jobs SUCCESS**, tested HEAD `52c450938d6a9596dc2e78a38caff8f26a20df03`.
- [Same code, PR validation 42543697240](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42543697240): **six of six jobs SUCCESS**.
- New `scripts/acceptance_diagnostics.py` runs in actual Blender on Windows Server 2022 / Blender 4.4.3 and Linux Blender 4.4.3, 4.5.15, 5.2.1.
- The existing Linux graphical GUI test separately verifies visual N-panel, a real window screenshot, keyboard Ctrl+Z / Ctrl+Shift+Z, and generation.
- Windows native Blender test uses a Python UI recorder to execute the addon Panel.draw code against **real registered Blender RNA properties**. It checks controls and the generator's enabled state; this is **not equivalent to real mouse clicks or rendered Windows N-panel**.

## N-panel logic: 6 checks in actual Windows Blender

| Control state | Required behavior | Result |
| --- | --- | --- |
| PUFFY + SINGLE, advanced off | Puffiness/outline/rim controls visible, side-scale and advanced hidden | PASS |
| CLASSIC + SINGLE | New PUFFY-only controls hidden | PASS |
| PUFFY + REFERENCE_3 | Side spread and side scale shown | PASS |
| PUFFY + REFERENCE_3 + advanced on | Mesh segments and topology controls appear | PASS |
| Spiral disabled | Compatible UI items remain usable and registered | PASS |
| Edit Mode | Generate operator's UI disabled; explanation shown | PASS |

Three groove-preset operator buttons and one generate button are validated in each UI layout pass. The recorder verifies that referenced Blender properties exist at runtime.

## Actual mesh geometry: BVH intersection diagnostics

Observed on Windows 4.4.3; the same mode tests also succeeded on Linux 4.5.15/5.2.1:

| Geometry scenario | BVH-detected non-adjacent self-intersections |
| --- | ---: |
| Default v0.4 PUFFY single lobe | **0** |
| Max puffiness 1.00, outline 0.15, roundness 0.30 | **0** |
| Flat, outline 0, roundness 0 | **0** |
| Max outline 0.15 with 0 roundness | **0** |

The BVH test excludes pairs of polygons sharing vertices by construction. The result supports no **non-neighboring face collisions** in the tested configurations, but is **not proof** of no adjacent face folding, adequate wall thickness, printer tolerances, or every possible setting.

**The three-lobe output is NOT a fused mesh.** Individual world-space BVHs showed intersections between lobe pairs:
- Lobe pair A–B: **371** overlapping face pairs.
- Lobe pair A–C: **332** overlapping face pairs.
- Lobe pair B–C: **175** overlapping face pairs.

Those numbers count candidate intersecting face pairs, **not** volume, severity, or a printable union. The three separate objects may need an explicit union/voxel remesh workflow before relying on them for 3D printing. This remains a **design limitation and next acceptance consideration**, not a completed feature.

## Remaining user acceptance (intentionally NOT claimed)

The remaining CLD-04 gate requires a real Windows Blender desktop session:
1. Install the v0.4 Python addon in Blender 4.4.3, enable it, press N, and confirm Cloud Spiral controls are readable and clickable.
2. Run PUFFY SINGLE and REFERENCE_3 from the real UI. Test preset buttons, expanded settings and side spacing controls.
3. Press Ctrl+Z and Ctrl+Shift+Z, and observe whether the actual scene objects disappear and return properly.
4. Decide whether the cloud looks acceptable aesthetically (currently a rounded grooved mound, not fully natural fluffy cumulus).
5. If 3D printing is intended, test the chosen mesh union, slicer inspection, and wall thickness; do not infer print safety from BVH alone.

If these are not confirmed, **do not mark CLD-04 at 100%**. The extra CLD-06 design review likewise remains separate.

## CBDK learnings / better next time

1. Run a **UI property-branch matrix** with registered real Blender RNA, even when the Windows host cannot initialize OpenGL.
2. Keep **rendered GUI tests** separate from **headless code-path tests**; a UI recorder tests generation of controls but not their visual appearance or human-click behavior.
3. Test both **per-object self-intersections** and **cross-object overlap**. A watertight individual mesh does not imply that multiple objects form a watertight fused result.
4. Establish objective geometric quality checks (BVH self-intersection) **and** subjective user acceptance as independent gates; they answer different questions.
5. Track evidence across Blender versions and platform runs, with precise SHA, status and logs. Never translate these results into invented human productivity time savings.

## Cross references

- [CLD-04/05 existing handoff](CLD04_CLD05_RESULTS.md)
- [CLD-06 v0.4 notes](CLD06_V04_RESULTS.md)
- [Completion stop rule and CBDK lessons](COMPLETION_GATE_AND_CBDK_LESSONS.md)
- [Notion original roadmap](https://app.notion.com/p/412948b7493781d092b2eb7dc2f1e048)
- [Notion CLD-06 stage](https://app.notion.com/p/413948b749378104a06ac74679c8b9dd)

**Current status:** original MVP 4/5 milestones=80% (CLD-04 98% acceptance pending), CLD-06 separately 90% (artistic acceptance pending), no automatic move to a new release roadmap.
