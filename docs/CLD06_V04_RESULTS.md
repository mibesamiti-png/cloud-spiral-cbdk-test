# CLD-06 — Cloud Spiral v0.4 organic puff experiment

**Status:** v0.4 implemented, native Blender + Linux GUI CI passed. **Visual acceptance pending**, the result is rounded/puffy but still not a naturally connected cumulus cloud.  
**Branch:** `test/cloud-v03-blender-native`, draft PR #1, `main` unmerged.  
**Visibility:** PUBLIC (do not add private 3D models or personal information).

## What changed
- Added `addon/cloud_spiral_lobe_builder_v04.py`; the v0.3.1 source remains unchanged.
- New default `PUFFY` style: height expansion, mild lobular perimeter waves, six side loops to round the underside.
- Three controls: `puffiness=0.55`, `outline_strength=0.09`, `rim_roundness=0.22`.
- `CLASSIC` style preserves v0.3.1 meshes exactly, including every vertex coordinate and polygon.
- Existing spiral groove, Soft/Carved/Reset presets, triple-lobe layout, selection rollback, and object-mode restrictions remain functional.

## Verified native geometry data (Blender 4.4.3, radius=1)

| Property | v0.3.1 legacy | v0.4 PUFFY |
| --- | ---: | ---: |
| Max height | 0.300000 | 0.850001 |
| Signed volume | 0.697097 | 1.731700 |
| Max radial extent | 1.000000 | 1.099873 |
| Vertex count | 5,826 | 6,466 |
| Polygon count | 5,888 | 6,528 |
| Boundary/unpaired edges | 0 | 0 |
| Winding conflicts | 0 | 0 |

**Height ratio: 2.83x; volume ratio: 2.48x.** These are **generated mesh** metrics, not subjective fluffiness or user productivity estimates.

The `scripts/puffy_geometry_compare.py` Blender test proves:
1. `CLASSIC` equals the complete old v0.3.1 topology and geometry.
2. `PUFFY` is closed/oriented with stronger volume/height.
3. Puffiness, perimeter strength and rim roundness each affect the shape.
4. The same real Blender environment renders an old/new side-by-side image.

## GitHub CI proof

- [Push run #42539777746](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42539777746): **5/5 SUCCESS**, tested HEAD `acc5d81f73267944d66c5595df33b3227a7f3093`.
- [Draft PR run #42539782530](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42539782530): **5/5 SUCCESS**, same code revision.
- Blender 4.4.3 / 4.5.15 / 5.2.1: standard native generation, invalid-parameter and injected-failure rollback quality gates, plus new geometry comparison.
- Linux Blender 4.4.3 GUI in Xvfb/openbox: actual N-panel/screenshot, preset + generation, Ctrl+Z/Redo 1→0→1.
- CBDK scanner/audit succeeded.
- [Installer ZIP & static report](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42539777746/artifacts/13641066019)
- [Blender 4.4.3 geometry comparison PNG, QA JSON, .blend](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42539777746/artifacts/13640837847)
- [GUI screenshot & Undo report](https://github.com/mibesamiti-png/cloud-spiral-cbdk-test/actions/runs/42539777746/artifacts/13640946735)

## SHA-256 / packaging
- `addon/cloud_spiral_lobe_builder_v04.py`: `017ddda76dd09116c6aa43aab3c56fc4b55a420d05d18837eba2d4ebe0ac0afb`
- Installer `Cloud_Spiral_Lobe_Builder_v0.4.zip`: `8ae15b89dfcf2918ec4ab7f88cfca8b8ea2ac0feec6045f6b53b062bb2648ea0`
- Review bundle in conversation: `Cloud_Spiral_v0.4_Review_Package.zip` with installer, source, Japanese README, test/QA JSON, screenshots, comparison render, and synthetic Blender test scene (2,861,075 bytes).

## Limitations and next tasks
- Screenshot confirms this is a **rounded swirl mound**, not fluffy cloud realism; 3-lobe meshes remain independent, not smoothly fused.
- No verified guarantees of geometry self-intersection-free when meshes overlap; no 3D print wall thickness or slicer guarantee.
- **Windows interactive UI usage** and real-world artistic assessment are still untested (Linux GUI CI does not replace them).
- Keep `main` unchanged and PR draft until scope or acceptance decision. The earlier MVP was 4/5=80%; **CLD-06 is a separate post-MVP stage** and should not silently change that denominator.
- No tracked human effort or CBDK time-saving baseline; no empirical speedup percentage.
- Next geometry study: add local/cloudlet volume variations that preserve watertightness, then evaluate merging/bridging independently.

[Notion CLD-06 stage](https://app.notion.com/p/413948b749378104a06ac74679c8b9dd) · [Primary experiment tracker](https://app.notion.com/p/412948b7493781d092b2eb7dc2f1e048).
