"""Cloud Spiral v0.4 acceptance diagnostics using REAL Blender bpy.

Covers the code path generating the N-panel in actual Blender RNA contexts,
plus BVH checks for potential geometric self-intersections and pair overlaps.

Important: This is NOT an interactive human Windows UX test, and a BVH
intersection count alone is not a certified watertight 3D printable union.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import time
import traceback
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree


def load_source(path):
    spec = importlib.util.spec_from_file_location("cloud_panel_native_qa", str(path))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class UILayoutRecorder:
    """Observe Python UI generation; uses actual registered Blender RNA data."""

    def __init__(self, events, ancestry="layout"):
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "ancestry", ancestry)
        object.__setattr__(self, "enabled", True)
        object.__setattr__(self, "scale_y", 1.0)

    def __setattr__(self, name, value):
        if name in {"enabled", "scale_y"}:
            self.events.append({"type": "attribute", "name": name,
                                "value": value, "path": self.ancestry})
        object.__setattr__(self, name, value)

    def box(self):
        return UILayoutRecorder(self.events, self.ancestry + ".box")

    def row(self, **kwargs):
        return UILayoutRecorder(self.events, self.ancestry + ".row")

    def column(self, **kwargs):
        return UILayoutRecorder(self.events, self.ancestry + ".column")

    def separator(self, **kwargs):
        self.events.append({"type": "separator"})

    def label(self, **kwargs):
        self.events.append({"type": "label", "text": kwargs.get("text", "")})

    def prop(self, obj, name, **kwargs):
        assert name in obj.bl_rna.properties, f"Unknown registered RNA property: {name}"
        getattr(obj, name)  # prove property has a readable runtime value
        self.events.append({"type": "prop", "name": name, "path": self.ancestry})

    def operator(self, identifier, **kwargs):
        self.events.append({"type": "operator", "id": identifier,
                            "text": kwargs.get("text", "")})
        class DummyResult:
            pass
        return DummyResult()


class PanelProxy:
    def __init__(self, layout):
        self.layout = layout


def extract_panel_events(addon, context):
    events = []
    addon.VIEW3D_PT_cloud_spiral_builder.draw(
        PanelProxy(UILayoutRecorder(events)), context
    )
    return events


def assert_display(events, required=(), forbidden=(), mode="OBJECT"):
    props = {event["name"] for event in events if event["type"] == "prop"}
    for key in required:
        assert key in props, ("missing expected control", key, sorted(props))
    for key in forbidden:
        assert key not in props, ("unexpected hidden control", key, sorted(props))
    generate = [e for e in events if e["type"] == "operator"
                and e["id"] == "mesh.cloud_spiral_generate"]
    presets = [e for e in events if e["type"] == "operator"
               and e["id"] == "mesh.cloud_spiral_preset"]
    assert len(generate) == 1 and len(presets) == 3
    # Each draw is a single deterministic layout pass. The last enabled
    # assignment is on the dedicated Generate operator's parent column.
    columns = [e for e in events if e["type"] == "attribute"
               and e["name"] == "enabled" and e["path"] == "layout.column"]
    assert columns and columns[-1]["value"] == (mode == "OBJECT"), columns
    return {"properties": sorted(props), "presets": len(presets),
            "generator_enabled": columns[-1]["value"],
            "labels": [e["text"] for e in events if e["type"] == "label"]}


def vertices_polygons(mesh):
    return ([v.co.copy() for v in mesh.vertices],
            [tuple(p.vertices) for p in mesh.polygons])


def bvh_for_mesh(mesh):
    coords, faces = vertices_polygons(mesh)
    return BVHTree.FromPolygons(coords, faces, all_triangles=False, epsilon=0.0000001)


def count_self_intersections(mesh):
    """Exclude face pairs sharing any vertex, which are adjacent by design."""
    start = time.perf_counter()
    tree = bvh_for_mesh(mesh)
    shared = [set(p.vertices) for p in mesh.polygons]
    unique = set()
    for a, b in tree.overlap(tree):
        if a == b:
            continue
        lo, hi = sorted((a, b))
        if lo == hi or (lo, hi) in unique:
            continue
        if shared[lo].intersection(shared[hi]):
            continue
        unique.add((lo, hi))
    return {"non_adjacent_intersection_pairs": len(unique),
            "examples": [list(x) for x in sorted(unique)[:12]],
            "elapsed_ms": round((time.perf_counter()-start)*1000, 1),
            "interpretation": "Potential intersecting non-neighboring faces; visual and slicer verification still needed."}


def make_lobes():
    settings = bpy.context.scene.cloud_spiral_settings
    settings.shape_style = "PUFFY"
    settings.mode = "SINGLE"
    result = bpy.ops.mesh.cloud_spiral_generate()
    assert result == {"FINISHED"}, result
    single = bpy.context.view_layer.objects.active
    assert single and single.type == "MESH"
    assert single.get("cloud_spiral_lobe")
    stats = count_self_intersections(single.data)
    assert stats["non_adjacent_intersection_pairs"] == 0, (
        "Default PUFFY lobe has BVH-detected self-intersections", stats
    )

    # Exercise the high-end permitted silhouette inputs before print acceptance.
    # These are diagnostics only until each combination has independent evidence.
    extremes = []
    for name, puff, outline, rim in [
        ("full_puff_and_outline", 1.0, 0.15, 0.30),
        ("flat_no_outline", 0.0, 0.0, 0.0),
        ("max_outline_min_rim", 0.55, 0.15, 0.0),
    ]:
        settings.puffiness = puff
        settings.outline_strength = outline
        settings.rim_roundness = rim
        assert bpy.ops.mesh.cloud_spiral_generate() == {"FINISHED"}
        candidate = bpy.context.view_layer.objects.active
        check = count_self_intersections(candidate.data)
        extremes.append({"name": name, "parameters": [puff, outline, rim], **check})
    settings.puffiness = 0.55
    settings.outline_strength = 0.09
    settings.rim_roundness = 0.22

    settings.mode = "REFERENCE_3"
    result = bpy.ops.mesh.cloud_spiral_generate()
    assert result == {"FINISHED"}, result
    lobes = [o for o in bpy.context.selected_objects
             if o.type == "MESH" and o.get("cloud_spiral_lobe")]
    assert len(lobes) == 3, [o.name for o in lobes]
    # Native 3-piece output intentionally contains independent meshes.
    # Whether neighboring lobes overlap is a design diagnostic, NOT a pass gate.
    trees = [bvh_for_mesh(o.data) for o in lobes]
    overlaps = []
    from mathutils import Matrix
    for i in range(3):
        for j in range(i+1, 3):
            # BVH built in local coordinates; map into world space first.
            def world_tree(obj):
                coords, faces = vertices_polygons(obj.data)
                return BVHTree.FromPolygons(
                    [obj.matrix_world @ v for v in coords],
                    faces, all_triangles=False, epsilon=0.0000001)
            a, b = world_tree(lobes[i]), world_tree(lobes[j])
            # Report overlap tests as diagnostics, not a solid union guarantee.
            hits = a.overlap(b)
            overlaps.append({"objects": [lobes[i].name, lobes[j].name],
                             "triangle_or_face_overlaps": len(hits)})
    return {"single_lobe": stats, "parameter_extremes": extremes,
            "independent_lobes": len(lobes), "three_lobe_pairs": overlaps,
            "union_mesh_created": False}


def main():
    if "--" not in sys.argv:
        raise SystemExit("blender -b --python scripts/acceptance_diagnostics.py -- ADDON OUTPUT")
    parts = sys.argv[sys.argv.index("--")+1:]
    assert len(parts) == 2, parts
    source, out = Path(parts[0]).resolve(), Path(parts[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = {"status": "RUNNING", "blender": bpy.app.version_string,
              "os": sys.platform, "panel_checks": [], "geometry": {},
              "limitations": [
                  "Panel.draw is executed in a real Blender RNA context but controls are observed through a recorder, NOT clicked in Windows.",
                  "The BVH result is a potential mesh-intersection diagnostic, not an independent 3D-print certification.",
                  "Three lobes are separate meshes, not an automatically watertight fused cloud.",
              ]}
    addon = None
    registered = False
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        addon = load_source(source)
        addon.register()
        registered = True
        s = bpy.context.scene.cloud_spiral_settings

        cases = [
            ("puffy_single", "PUFFY", "SINGLE", False, False,
             {"puffiness","outline_strength","rim_roundness"},
             {"three_spread","three_side_scale","angular_segments"}),
            ("classic_single", "CLASSIC", "SINGLE", False, False,
             {"shape_style","radius","thickness"},
             {"puffiness","outline_strength","rim_roundness","three_spread"}),
            ("puffy_three", "PUFFY", "REFERENCE_3", False, False,
             {"three_spread","three_side_scale","puffiness"},
             {"angular_segments"}),
            ("puffy_three_advanced", "PUFFY", "REFERENCE_3", True, False,
             {"three_spread","three_side_scale","angular_segments","radial_segments",
              "center_patch_ratio","groove_width_ratio"},
             set()),
            ("spiral_disabled", "PUFFY", "SINGLE", False, True,
             {"spiral_enabled","puffiness","direction"}, {"angular_segments"}),
        ]
        for name, style, mode, advanced, disabled, required, forbidden in cases:
            s.shape_style = style
            s.mode = mode
            s.ui_show_advanced = advanced
            s.spiral_enabled = not disabled
            events = extract_panel_events(addon, bpy.context)
            detail = assert_display(events, required, forbidden)
            report["panel_checks"].append({"name": name, "status": "PASS",
                                           "details": detail})
            print(f"CLOUD_PANEL_PASS: {name}", flush=True)

        # Real Edit Mode (instead of fake context) should disable Generate.
        s.mode = "SINGLE"
        bpy.ops.mesh.primitive_cube_add(size=1)
        try:
            bpy.ops.object.mode_set(mode="EDIT")
            assert bpy.context.mode == "EDIT_MESH"
            events = extract_panel_events(addon, bpy.context)
            detail = assert_display(events, {"shape_style"}, set(), mode="EDIT_MESH")
            assert any(e.get("text") == "オブジェクトモードで生成できます"
                       for e in events if e["type"] == "label")
            report["panel_checks"].append({"name":"edit_mode_disables_generator",
                                           "status":"PASS", "details":detail})
            print("CLOUD_PANEL_PASS: edit_mode_disables_generator",flush=True)
        finally:
            if bpy.context.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")

        report["geometry"] = make_lobes()
        print("CLOUD_BVH_DIAGNOSTICS: "
              + json.dumps(report["geometry"], ensure_ascii=False), flush=True)
        report["status"] = "PASS"
        print("CLOUD_ACCEPTANCE_DIAGNOSTICS: PASS", flush=True)
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = repr(exc)
        report["traceback"] = traceback.format_exc()
        print("CLOUD_ACCEPTANCE_DIAGNOSTICS: FAIL", flush=True)
        raise
    finally:
        if registered:
            addon.unregister()
        (out/"acceptance_diagnostics.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
