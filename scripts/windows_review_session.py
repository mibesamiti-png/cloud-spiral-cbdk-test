"""One-click local Windows review session for Cloud Spiral v0.4.

Launch via run_windows_review.bat, or use --smoke under CI's real Blender.
The addon itself is NOT modified. A separate temporary scene is built with
--factory-startup. Human GUI acceptance remains explicitly manual.
"""
import hashlib
import os
import importlib.util
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import bpy
from bpy.props import EnumProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup


def args():
    if "--" not in sys.argv:
        raise ValueError("Missing -- ADDON OUTPUT [--smoke] arguments")
    parts = sys.argv[sys.argv.index("--") + 1:]
    if len(parts) not in (2, 3):
        raise ValueError("Expected ADDON OUTPUT [--smoke|--gui-smoke]")
    source = Path(parts[0]).resolve()
    output = Path(parts[1]).resolve()
    smoke = len(parts) == 3 and parts[2] == "--smoke"
    gui_smoke = len(parts) == 3 and parts[2] == "--gui-smoke"
    if len(parts) == 3 and not (smoke or gui_smoke):
        raise ValueError("Unknown argument: " + parts[2])
    if not source.is_file():
        raise FileNotFoundError("Cloud Spiral addon source not found: " + str(source))
    output.mkdir(parents=True, exist_ok=True)
    return source, output, smoke, gui_smoke


SOURCE, OUTPUT, SMOKE, GUI_SMOKE = args()
REGISTERED_ADDON = None
QA_CLASSES_REGISTERED = False

OPTIONS = (
    ("NOT_TESTED", "未確認", "まだ検証していない"),
    ("PASS", "合格", "Windows上で自分の目と操作で確認できた"),
    ("FAIL", "不具合", "確認して問題が起きた"),
)

QUESTIONS = (
    ("panel", "Nパネルの表示とクリック", "CLD-04"),
    ("generate", "単体と3ローブを操作して生成", "CLD-04"),
    ("presets", "ふんわり・くっきり・標準の切替", "CLD-04"),
    ("undo", "Ctrl+ZとCtrl+Shift+Z", "CLD-04"),
    ("appearance", "雲の見た目が希望に合うか", "CLD-06"),
    ("three_lobes", "3ローブの自然さ・重なり", "CLD-06"),
)


class CLOUDQA_ReviewState(PropertyGroup):
    panel: EnumProperty(name="Nパネルの表示・クリック", items=OPTIONS, default="NOT_TESTED")
    generate: EnumProperty(name="単体と3ローブの生成", items=OPTIONS, default="NOT_TESTED")
    presets: EnumProperty(name="溝スタイル切替", items=OPTIONS, default="NOT_TESTED")
    undo: EnumProperty(name="Undo / Redo", items=OPTIONS, default="NOT_TESTED")
    appearance: EnumProperty(name="ふっくら雲の見た目", items=OPTIONS, default="NOT_TESTED")
    three_lobes: EnumProperty(name="3ローブの造形", items=OPTIONS, default="NOT_TESTED")
    notes: StringProperty(name="気づいた問題・感想", description="任意のメモ", default="", maxlen=1024)


def statuses(scene):
    state = scene.cloud_qa_review
    return {name: getattr(state, name) for name, _, _ in QUESTIONS}


def build_report(scene, evidence_kind="MANUAL_WINDOWS_GUI"):
    values = statuses(scene)
    def section_status(prefix):
        picked = [values[name] for name, _, group in QUESTIONS if group == prefix]
        if any(s == "FAIL" for s in picked):
            return "REJECTED"
        if all(s == "PASS" for s in picked):
            return "ACCEPTED"
        return "INCOMPLETE"

    return {
        "schema": "cloud_spiral_windows_acceptance_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "kind": evidence_kind,
        "blender_version": bpy.app.version_string,
        "blender_background": bool(bpy.app.background),
        "addon_version": "0.4.0",
        "addon_source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "source_file_name": SOURCE.name,
        "answers": {
            name: {"question": text, "stage": group, "answer": values[name]}
            for name, text, group in QUESTIONS
        },
        "stage_CLD04": section_status("CLD-04"),
        "stage_CLD06": section_status("CLD-06"),
        "notes": scene.cloud_qa_review.notes[:1024],
        "print_suitability": "NOT_TESTED",
        "limitations": [
            "Acceptance answers are user-controlled and are never automatically set to PASS.",
            "The review scene uses generated temporary cloud samples, not the user's own project.",
            "CLD-04/06 acceptance is not a 3D-print or fused-solid certification.",
            "The independent geometry CI and this subjective Windows review are different evidence layers.",
        ],
    }


class CLOUDQA_OT_export(Operator):
    bl_idname = "cloud_qa.export_review"
    bl_label = "検証レポートを書き出す"
    bl_description = "合否をJSONに書き出す。未確認は未確認として残します"
    bl_options = {"REGISTER"}

    def execute(self, context):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        destination = OUTPUT / ("cloud_review_" + timestamp + ".json")
        # Preserve each user observation, even after repeated clicks.
        if destination.exists():
            for suffix in range(1, 1001):
                candidate = OUTPUT / ("cloud_review_" + timestamp + "_" + str(suffix) + ".json")
                if not candidate.exists():
                    destination = candidate
                    break
            else:
                self.report({"ERROR"}, "レポート保存名が重複しています")
                return {"CANCELLED"}
        report = build_report(context.scene)
        try:
            destination.write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:
            self.report({"ERROR"}, "結果を書き込めません: " + str(exc))
            return {"CANCELLED"}
        self.report(
            {"INFO"}, "結果を保存しました: " + destination.name
        )
        print("CLOUD_WINDOWS_REVIEW_REPORT: " + str(destination), flush=True)
        return {"FINISHED"}


class VIEW3D_PT_cloud_review(Panel):
    bl_label = "Cloud Spiral | Windows 最終確認"
    bl_idname = "VIEW3D_PT_cloud_review"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cloud QA"

    def draw(self, context):
        layout = self.layout
        state = context.scene.cloud_qa_review
        layout.label(text="1. Cloud Spiralタブで実際に操作")
        layout.label(text="2. 結果をそれぞれ選択してください")
        box = layout.box()
        box.label(text="CLD-04 | 操作の最終確認")
        for name in ("panel", "generate", "presets", "undo"):
            box.prop(state, name)
        box = layout.box()
        box.label(text="CLD-06 | 造形の最終確認")
        for name in ("appearance", "three_lobes"):
            box.prop(state, name)
        layout.prop(state, "notes")
        layout.operator(CLOUDQA_OT_export.bl_idname, icon="FILE_TICK")
        layout.label(text="未確認は合格扱いしません", icon="INFO")
        layout.label(text="3D印刷適性は別の検査です", icon="INFO")


QA_CLASSES = (CLOUDQA_ReviewState, CLOUDQA_OT_export, VIEW3D_PT_cloud_review)


def load_addon():
    global REGISTERED_ADDON, QA_CLASSES_REGISTERED
    spec = importlib.util.spec_from_file_location("cloud_spiral_local_review_v04", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Cloud Spiral Python module")
    addon = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = addon
    spec.loader.exec_module(addon)
    addon.register()
    REGISTERED_ADDON = addon
    completed = []
    try:
        for item in QA_CLASSES:
            bpy.utils.register_class(item)
            completed.append(item)
        bpy.types.Scene.cloud_qa_review = PointerProperty(type=CLOUDQA_ReviewState)
        QA_CLASSES_REGISTERED = True
    except Exception:
        if hasattr(bpy.types.Scene, "cloud_qa_review"):
            del bpy.types.Scene.cloud_qa_review
        for item in reversed(completed):
            bpy.utils.unregister_class(item)
        addon.unregister()
        REGISTERED_ADDON = None
        raise
    return addon


def prepare_samples():
    """Generate 1+3 real addon meshes without touching any user .blend file."""
    scene = bpy.context.scene
    source_addon = REGISTERED_ADDON
    assert source_addon is not None
    cube = bpy.data.objects.get("Cube")
    if cube is not None:
        cube.hide_set(True)
    settings = scene.cloud_spiral_settings
    settings.shape_style = "PUFFY"
    settings.mode = "SINGLE"
    assert bpy.ops.mesh.cloud_spiral_generate() == {"FINISHED"}
    a = [obj for obj in bpy.context.selected_objects if obj.get("cloud_spiral_lobe")]
    assert len(a) == 1, [obj.name for obj in a]
    a[0].location.x -= 3.0
    a[0]["qa_sample"] = "SINGLE"

    settings.mode = "REFERENCE_3"
    assert bpy.ops.mesh.cloud_spiral_generate() == {"FINISHED"}
    b = [obj for obj in bpy.context.selected_objects if obj.get("cloud_spiral_lobe")]
    assert len(b) == 3, [obj.name for obj in b]
    for obj in b:
        obj.location.x += 3.0
        obj["qa_sample"] = "THREE"
    settings.mode = "SINGLE"
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = None
    assert len([o for o in scene.objects if o.get("qa_sample")]) == 4
    return {"single": a[0].name, "triple": [x.name for x in b],
            "total_sample_objects": 4}


def configure_window():
    for window in bpy.context.window_manager.windows:
        if window.screen is None:
            continue
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            space.show_region_ui = True
            if space.region_3d:
                space.region_3d.view_location = (0.0, 0.0, 0.0)
                space.region_3d.view_distance = 10.0
            return True
    return False


def initialize():
    load_addon()
    generated = prepare_samples()
    if SMOKE:
        assert hasattr(bpy.types.Scene, "cloud_qa_review")
        assert hasattr(bpy.types, "VIEW3D_PT_cloud_review")
        assert len([o for o in bpy.data.objects if o.get("qa_sample")]) == 4
        first = build_report(bpy.context.scene, "AUTOMATED_SMOKE_NOT_ACCEPTANCE")
        assert first["stage_CLD04"] == "INCOMPLETE"
        assert first["stage_CLD06"] == "INCOMPLETE"
        assert all(v["answer"] == "NOT_TESTED" for v in first["answers"].values())

        # Exercise the actual Report Export operator without treating this
        # automated smoke as the user's real Windows GUI acceptance.
        before = set(OUTPUT.glob("cloud_review_*.json"))
        assert bpy.ops.cloud_qa.export_review() == {"FINISHED"}
        added = set(OUTPUT.glob("cloud_review_*.json")) - before
        assert len(added) == 1, ("Report export did not create one JSON", added)
        first_path = next(iter(added))
        test_report = json.loads(first_path.read_text(encoding="utf-8"))
        assert test_report["stage_CLD04"] == "INCOMPLETE"
        assert test_report["stage_CLD06"] == "INCOMPLETE"
        assert all(v["answer"] == "NOT_TESTED" for v in test_report["answers"].values())
        assert bpy.ops.cloud_qa.export_review() == {"FINISHED"}
        twice = set(OUTPUT.glob("cloud_review_*.json")) - before
        assert len(twice) == 2, "Rapid repeated export overwrote earlier report"
        assert first_path.read_text(encoding="utf-8") == json.dumps(
            test_report, indent=2, ensure_ascii=False
        )
        for report_file in twice:
            report_file.unlink()  # Never ship synthetic manual-acceptance JSON.

        # Confirm a FAIL cannot be mislabeled accepted, and all manual PASS
        # answers are necessary before a stage reports ACCEPTED.
        values = bpy.context.scene.cloud_qa_review
        values.panel = "FAIL"
        assert build_report(bpy.context.scene)["stage_CLD04"] == "REJECTED"
        values.panel = "PASS"
        assert build_report(bpy.context.scene)["stage_CLD04"] == "INCOMPLETE"
        for key in ("generate", "presets", "undo"):
            setattr(values, key, "PASS")
        assert build_report(bpy.context.scene)["stage_CLD04"] == "ACCEPTED"
        assert build_report(bpy.context.scene)["stage_CLD06"] == "INCOMPLETE"
        for key, _, _ in QUESTIONS:
            setattr(values, key, "NOT_TESTED")
        assert build_report(bpy.context.scene)["stage_CLD04"] == "INCOMPLETE"

        (OUTPUT / "windows_review_kit_smoke.json").write_text(
            json.dumps({"status": "PASS", "generated": generated, "review": first},
                       indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print("CLOUD_WINDOWS_REVIEW_KIT_SMOKE: PASS", flush=True)
    elif GUI_SMOKE:
        assert not bpy.app.background, "GUI smoke was run with --background"
        assert configure_window(), "No VIEW_3D graphical window was available"
        assert hasattr(bpy.types, "VIEW3D_PT_cloud_review")
        assert all(v == "NOT_TESTED" for v in statuses(bpy.context.scene).values())
        (OUTPUT / "windows_review_gui_smoke.json").write_text(
            json.dumps({
                "status": "PASS",
                "gui_window_available": True,
                "Cloud_QA_panel_registered": True,
                "generated": generated,
                "stage_CLD04": "INCOMPLETE",
                "stage_CLD06": "INCOMPLETE",
                "real_windows_mouse_clicks": "NOT_TESTED",
            }, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print("CLOUD_WINDOWS_REVIEW_GUI_SMOKE: PASS", flush=True)
        # The temporary CI Blender process may have a first-run modal. Once
        # JSON is written and stdout is flushed, exit without a UI save prompt.
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)
    else:
        configure_window()
        print("CLOUD_WINDOWS_REVIEW_KIT_READY: 4 cloud objects. Open N > Cloud QA.", flush=True)


if SMOKE:
    initialize()
else:
    _started = [False]

    def start_when_window_ready():
        if _started[0]:
            return None
        if not bpy.context.window_manager.windows:
            return 0.4
        _started[0] = True
        try:
            initialize()
        except Exception:
            details = traceback.format_exc()
            print("CLOUD_WINDOWS_REVIEW_KIT_ERROR:\n" + details, flush=True)
            (OUTPUT/"review_startup_error.txt").write_text(
                details, encoding="utf-8"
            )
            if GUI_SMOKE:
                # Fail fast in CI rather than letting Blender sit at its modal
                # first-run window until timeout kills the process.
                sys.stdout.flush()
                sys.stderr.flush()
                os._exit(1)
        return None

    bpy.app.timers.register(start_when_window_ready, first_interval=1.0)
