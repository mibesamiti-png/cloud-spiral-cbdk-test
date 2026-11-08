"""Extra native robustness gate for Cloud Spiral v0.3.1.

Tests RNA range handling, OBJECT/Edit Mode poll, rollback on injected mid-build
failure, preservation of existing objects, and honest headless Undo evidence.
This script runs in Blender itself, not a fake bpy environment.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
import time
import traceback
from pathlib import Path

import bpy


def main():
    if "--" not in sys.argv:
        raise SystemExit("blender --background --python-exit-code 1 --python scripts/blender_quality_gate.py -- ADDON OUTPUT")
    params = sys.argv[sys.argv.index("--") + 1:]
    if len(params) != 2:
        raise SystemExit("Expected addon path and output directory")
    src = Path(params[0]).resolve()
    out = Path(params[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)

    report = {
        "test": "cloud_spiral_robustness_v1",
        "blender": bpy.app.version_string,
        "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "status": "RUNNING",
        "checks": [],
        "limitations": [
            "A headless Blender run is not interactive N-panel or Windows GUI validation.",
            "Undo is recorded as NOT_RUN when an actual VIEW_3D window context is unavailable.",
            "A rollback test checks object/mesh cleanup and selection restoration, not every possible external failure.",
        ],
    }

    def check(name, func):
        started = time.perf_counter()
        try:
            detail = func()
            report["checks"].append({
                "name": name, "status": "PASS",
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "details": detail,
            })
            print(f"CLOUD_QUALITY_PASS: {name}", flush=True)
            return detail
        except Exception as exc:
            report["checks"].append({
                "name": name, "status": "FAIL",
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            })
            print(f"CLOUD_QUALITY_FAIL: {name} -> {exc!r}", flush=True)
            raise

    registered = False
    addon = None
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        spec = importlib.util.spec_from_file_location("cloud_spiral_quality_v031", src)
        if spec is None or spec.loader is None:
            raise AssertionError("Cannot import addon source")
        addon = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = addon
        spec.loader.exec_module(addon)
        check("register", addon.register)
        registered = True
        settings = bpy.context.scene.cloud_spiral_settings

        def rna_bounds():
            requirements = {
                "radius": (0.05, None),
                "thickness": (0.02, None),
                "angular_segments": (32, 512),
                "radial_segments": (8, 160),
                "turns": (0.35, 2.5),
                "three_spread": (0.4, 2.0),
                "three_side_scale": (0.5, 1.25),
                "groove_depth_ratio": (0.0, 0.35),
            }
            observed = {}
            for prop_name, (low, high) in requirements.items():
                prop = settings.bl_rna.properties[prop_name]
                assert abs(prop.hard_min - low) < 1e-6, (prop_name, prop.hard_min)
                if high is not None:
                    assert abs(prop.hard_max - high) < 1e-6, (prop_name, prop.hard_max)
                observed[prop_name] = {"min": low, "max": high}
            return observed
        check("rna_property_min_max", rna_bounds)

        def invalid_values():
            cases = [
                ("radius", -1.0, "min", 0.05),
                ("thickness", -2.0, "min", 0.02),
                ("angular_segments", 1, "min", 32),
                ("radial_segments", 1, "min", 8),
                ("turns", 900.0, "max", 2.5),
                ("three_spread", 999.0, "max", 2.0),
                ("groove_depth_ratio", 99.0, "max", 0.35),
            ]
            outcomes = {}
            for name, attempted, rule, bound in cases:
                original = getattr(settings, name)
                try:
                    try:
                        setattr(settings, name, attempted)
                    except (ValueError, TypeError, OverflowError) as exc:
                        outcomes[name] = "rejected:" + type(exc).__name__
                        continue
                    got = getattr(settings, name)
                    if rule == "min":
                        assert got >= bound - 1e-6, (name, got, bound)
                    else:
                        assert got <= bound + 1e-6, (name, got, bound)
                    assert math.isfinite(float(got)), (name, got)
                    outcomes[name] = got
                finally:
                    setattr(settings, name, original)
            return outcomes
        check("invalid_numeric_values_clamped_or_rejected", invalid_values)

        def initial():
            settings.mode = "SINGLE"
            assert bpy.ops.mesh.cloud_spiral_generate.poll()
            assert bpy.ops.mesh.cloud_spiral_generate() == {"FINISHED"}
            obj = bpy.context.view_layer.objects.active
            assert obj is not None and obj.type == "MESH"
            assert obj.get("cloud_spiral_lobe")
            return {"object": obj.name, "mesh": obj.data.name}
        check("baseline_generate", initial)

        def edit_mode():
            baseline_object_count = len(bpy.data.objects)
            obj = bpy.context.view_layer.objects.active
            assert obj is not None and obj.type == "MESH"
            try:
                bpy.ops.object.mode_set(mode="EDIT")
                assert bpy.context.mode == "EDIT_MESH", bpy.context.mode
                assert not bpy.ops.mesh.cloud_spiral_generate.poll()
                assert len(bpy.data.objects) == baseline_object_count
                return {"mode": bpy.context.mode, "generate_operator_poll": False}
            finally:
                if bpy.context.mode == "EDIT_MESH":
                    bpy.ops.object.mode_set(mode="OBJECT")
        check("edit_mode_generation_blocked", edit_mode)

        def mid_build_rollback():
            settings.mode = "REFERENCE_3"
            # Select the already-generated lobe, so a failed operation must restore it.
            preserved = bpy.context.view_layer.objects.active
            assert preserved is not None
            for obj in bpy.context.selected_objects:
                obj.select_set(False)
            preserved.select_set(True)
            bpy.context.view_layer.objects.active = preserved
            original_obj_pointers = {o.as_pointer() for o in bpy.data.objects}
            original_mesh_pointers = {m.as_pointer() for m in bpy.data.meshes}
            original_selected = {o.as_pointer() for o in bpy.context.selected_objects}
            original_active_ptr = preserved.as_pointer()

            original_creator = addon.create_lobe_mesh
            call_count = [0]

            def fail_during_second_lobe(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 2:
                    raise RuntimeError("injected-failure-after-first-mesh")
                return original_creator(*args, **kwargs)

            addon.create_lobe_mesh = fail_during_second_lobe
            try:
                result = bpy.ops.mesh.cloud_spiral_generate()
            finally:
                addon.create_lobe_mesh = original_creator

            assert result == {"CANCELLED"}, result
            assert call_count == [2], call_count
            assert original_obj_pointers == {o.as_pointer() for o in bpy.data.objects}, "leaked or deleted object(s)"
            assert original_mesh_pointers == {m.as_pointer() for m in bpy.data.meshes}, "leaked or deleted mesh(es)"
            assert original_selected == {o.as_pointer() for o in bpy.context.selected_objects}, "selection not restored"
            assert original_active_ptr == bpy.context.view_layer.objects.active.as_pointer(), "active object not restored"
            assert bpy.context.view_layer.objects.active == preserved
            return {
                "operator_result": list(result),
                "injected_after_mesh": 1,
                "objects_preserved": len(original_obj_pointers),
                "meshes_preserved": len(original_mesh_pointers),
                "selection_restored": True,
                "active_restored": True,
            }
        check("mid_build_rollback_preserves_scene", mid_build_rollback)

        def after_recovery():
            settings.mode = "SINGLE"
            assert bpy.ops.mesh.cloud_spiral_generate() == {"FINISHED"}
            return {"generated_after_failure": bpy.context.view_layer.objects.active.name}
        check("generation_recovers_after_rollback", after_recovery)

        def headless_undo_status():
            # Do not report a GUI Undo pass when running --background.
            has_3d_context = (not bpy.app.background and bpy.context.window is not None
                              and bpy.context.area is not None
                              and bpy.context.area.type == "VIEW_3D")
            if not has_3d_context:
                return {"status": "NOT_RUN", "reason": "No interactive VIEW_3D area in headless Actions runner"}
            return {"status": "NOT_RUN", "reason": "This suite intentionally does not simulate a user's interactive Undo/Redo"}
        check("undo_gui_scope_declared", headless_undo_status)

        def unregister():
            nonlocal registered
            addon.unregister()
            registered = False
            assert not hasattr(bpy.types.Scene, "cloud_spiral_settings")
            return {"scene_property_removed": True}
        check("unregister_after_robustness", unregister)
        report["status"] = "PASS"
        print("CLOUD_REAL_BLENDER_QUALITY: PASS", flush=True)
    except Exception:
        report["status"] = "FAIL"
        report["error_traceback"] = traceback.format_exc()
        print("CLOUD_REAL_BLENDER_QUALITY: FAIL", flush=True)
        raise
    finally:
        if registered:
            addon.unregister()
        (out / "quality_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
