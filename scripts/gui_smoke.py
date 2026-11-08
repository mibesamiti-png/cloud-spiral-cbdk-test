"""Linux virtual-display GUI smoke for Cloud Spiral v0.3.1.

Blender must be launched WITHOUT --background under xvfb-run.
The test uses timers so that the actual window, screen and VIEW_3D region exist.
It does not assert mouse click accuracy or replace Windows user testing.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import traceback
from pathlib import Path
import bpy


def arguments():
    if "--" not in sys.argv:
        raise SystemExit("usage: blender --python scripts/gui_smoke.py -- ADDON OUT")
    extra = sys.argv[sys.argv.index("--") + 1:]
    if len(extra) != 2:
        raise SystemExit("Expected ADDON and OUT")
    return Path(extra[0]).resolve(), Path(extra[1]).resolve()


SOURCE, OUT = arguments()
OUT.mkdir(parents=True, exist_ok=True)
REPORT_PATH = OUT / "gui_report.json"
STATE = {"phase": 0, "registered": False, "addon": None,
         "window": None, "area": None, "region": None,
         "original_count": None, "created_count": None,
         "checks": [], "warnings": [], "ticks": 0}
REPORT = {"blender": bpy.app.version_string, "background": bpy.app.background,
          "status": "RUNNING", "checks": STATE["checks"], "warnings": STATE["warnings"],
          "platform": "Linux Xvfb (virtual screen)",
          "limitations": [
              "N-panel registration and visibility are verified; manual button clicks are not simulated.",
              "This test does not prove Windows-specific layout, fonts, and mouse behavior.",
              "Undo/Redo requires a real UI context and is reported independently from ordinary headless checks.",
          ]}


def record(name, detail):
    STATE["checks"].append({"name": name, "status": "PASS", "details": detail})
    print("CLOUD_GUI_PASS: " + name, flush=True)


def save_report(status):
    REPORT["status"] = status
    REPORT_PATH.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")


def finish(status, error=None):
    if error:
        REPORT["error"] = repr(error)
        REPORT["traceback"] = traceback.format_exc()
    if STATE["registered"]:
        try:
            STATE["addon"].unregister()
            STATE["registered"] = False
        except Exception as exc:
            STATE["warnings"].append("unregister: " + repr(exc))
    save_report(status)
    print("CLOUD_GUI_REAL_BLENDER: " + status, flush=True)
    # Quitting via Blender makes screenshot and JSON writes visible to the CI artifact.
    bpy.ops.wm.quit_blender()
    return None


def current_context():
    windows = list(bpy.context.window_manager.windows)
    for window in windows:
        if window.screen is None:
            continue
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                region = next((r for r in area.regions if r.type == "WINDOW"), None)
                if region is not None:
                    return window, area, region
    return None


def lobe_count():
    return sum(1 for obj in bpy.data.objects
               if obj.type == "MESH" and obj.get("cloud_spiral_lobe"))


def tick():
    STATE["ticks"] += 1
    try:
        if STATE["ticks"] > 80:
            raise RuntimeError("GUI context initialization timed out")

        if STATE["phase"] == 0:
            if bpy.app.background:
                raise RuntimeError("GUI test must not use --background")
            context = current_context()
            if context is None:
                return 0.3
            window, area, region = context
            STATE["window"], STATE["area"], STATE["region"] = context
            spec = importlib.util.spec_from_file_location("cloud_spiral_gui_v031", SOURCE)
            if spec is None or spec.loader is None:
                raise RuntimeError("No addon module")
            addon = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = addon
            spec.loader.exec_module(addon)
            addon.register()
            STATE["addon"] = addon
            assert hasattr(bpy.types.Scene, "cloud_spiral_settings")
            assert hasattr(bpy.types, "VIEW3D_PT_cloud_spiral_builder")
            assert addon.VIEW3D_PT_cloud_spiral_builder.bl_category == "Cloud Spiral"
            area.spaces.active.show_region_ui = True
            assert area.spaces.active.show_region_ui
            record("real_gui_window_and_N_sidebar", {
                "window": True, "area": area.type,
                "N_sidebar_visible": True, "panel_registered": True,
                "panel_category": addon.VIEW3D_PT_cloud_spiral_builder.bl_category,
                "screen": window.screen.name,
            })
            STATE["registered"] = True
            STATE["phase"] = 1
            return 0.5

        window, area, region = STATE["window"], STATE["area"], STATE["region"]
        with bpy.context.temp_override(window=window, screen=window.screen,
                                       area=area, region=region):
            if STATE["phase"] == 1:
                settings = bpy.context.scene.cloud_spiral_settings
                settings.mode = "SINGLE"
                before = lobe_count()
                STATE["original_count"] = before
                assert bpy.ops.mesh.cloud_spiral_preset(preset="SOFT") == {"FINISHED"}
                assert abs(settings.groove_depth_ratio - 0.055) < 1e-5
                assert bpy.ops.mesh.cloud_spiral_generate.poll()
                result = bpy.ops.mesh.cloud_spiral_generate()
                assert result == {"FINISHED"}, result
                after = lobe_count()
                assert after == before + 1, (before, after)
                STATE["created_count"] = after
                record("gui_context_preset_and_generate", {
                    "preset": "SOFT", "before": before, "after": after,
                    "operator_invoked_in_VIEW_3D": True,
                })
                STATE["phase"] = 2
                return 0.8

            if STATE["phase"] == 2:
                image = OUT / "blender_window.png"
                # Capture the actual Blender GUI, not a Workbench render.
                assert bpy.ops.screen.screenshot.poll()
                result = bpy.ops.screen.screenshot(filepath=str(image), check_existing=False)
                assert result == {"FINISHED"}, result
                assert image.is_file() and image.stat().st_size > 4096
                record("real_gui_screenshot", {
                    "name": image.name, "size_bytes": image.stat().st_size,
                })
                STATE["phase"] = 3
                return 0.5

            if STATE["phase"] == 3:
                # Native Blender UI Undo. This is not a mocked bpy module.
                result = bpy.ops.ed.undo()
                assert result == {"FINISHED"}, result
                after_undo = lobe_count()
                assert after_undo == STATE["original_count"], (
                    "Undo failed to remove generated lobe",
                    STATE["original_count"], after_undo,
                )
                record("real_gui_undo", {
                    "result": list(result), "remaining_lobes": after_undo,
                })
                STATE["phase"] = 4
                return 0.5

            if STATE["phase"] == 4:
                result = bpy.ops.ed.redo()
                assert result == {"FINISHED"}, result
                after_redo = lobe_count()
                assert after_redo == STATE["created_count"], (
                    "Redo did not restore generated lobe",
                    STATE["created_count"], after_redo,
                )
                record("real_gui_redo", {
                    "result": list(result), "remaining_lobes": after_redo,
                })
                STATE["phase"] = 5
                return 0.1

        if STATE["phase"] == 5:
            return finish("PASS")
        raise RuntimeError("unexpected phase " + str(STATE["phase"]))
    except Exception as exc:
        print("CLOUD_GUI_EXCEPTION: " + traceback.format_exc(), flush=True)
        return finish("FAIL", error=exc)


# python execution can precede actual initialization of the graphical screen.
# Timer callback is evaluated after the Blender GUI event loop starts.
bpy.app.timers.register(tick, first_interval=1.5)
print("CLOUD_GUI_SCHEDULED", flush=True)
