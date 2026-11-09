"""Native Blender geometry regression: v0.3.1 legacy versus v0.4 CLASSIC/PUFFY.

This validates that v0.4 CLASSIC has identical vertices/faces to v0.3.1,
while PUFFY is measurably fuller, closed, correctly wound, and user-adjustable.
"""
from __future__ import annotations
import importlib.util
import json
import math
import sys
import traceback
from pathlib import Path
import bpy


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def create(module, name, style=None, **overrides):
    kwargs = dict(
        name=name,
        radius=1.0,
        thickness=0.16,
        angular_segments=128,
        radial_segments=32,
        inner_spiral_radius_ratio=0.24,
        center_patch_ratio=0.58,
        transition_rings=3,
        transition_twist_deg=18.0,
        turns=1.12,
        start_angle_deg=-80.0,
        direction_sign=1.0,
        spiral_power=1.0,
        spiral_enabled=True,
        groove_depth_ratio=0.095,
        groove_width_ratio=0.20,
        groove_edge_softness=0.45,
        inner_fade_end=0.12,
        outer_fade_start=0.58,
        outer_fade_power=1.60,
        dome_height_ratio=0.14,
        dome_power=1.75,
    )
    if style is not None:
        kwargs.update(shape_style=style, puffiness=0.55, outline_strength=0.09, rim_roundness=0.22)
    kwargs.update(overrides)
    mesh, count = module.create_lobe_mesh(**kwargs)
    assert count == 128
    return mesh


def inspect(mesh):
    edges = {}
    volume = 0.0
    for poly in mesh.polygons:
        ring = list(poly.vertices)
        assert len(ring) >= 3 and len(set(ring)) == len(ring)
        for a, b in zip(ring, ring[1:] + ring[:1]):
            edges.setdefault(tuple(sorted((a, b))), []).append((a, b))
        a = mesh.vertices[ring[0]].co
        for i in range(1, len(ring)-1):
            b = mesh.vertices[ring[i]].co
            c = mesh.vertices[ring[i+1]].co
            volume += a.dot(b.cross(c)) / 6.0
    boundaries = sum(len(e) != 2 for e in edges.values())
    winding = sum(len(e) == 2 and e[0] != e[1][::-1] for e in edges.values())
    max_z = max(v.co.z for v in mesh.vertices)
    min_z = min(v.co.z for v in mesh.vertices)
    contour_radius = max(math.hypot(v.co.x, v.co.y) for v in mesh.vertices)
    out = {
        "vertices": len(mesh.vertices), "faces": len(mesh.polygons),
        "unpaired_edges": boundaries, "winding_conflicts": winding,
        "signed_volume": round(volume, 6), "max_z": round(max_z, 6),
        "min_z": round(min_z, 6), "max_radial_extent": round(contour_radius, 6),
    }
    assert boundaries == 0 and winding == 0
    assert volume > 0 and min_z >= -1e-5
    return out


def render_comparison(old, puffy, output):
    # Only a synthetic demo scene. Does not alter the user's existing .blend.
    # The source meshes already exist in bpy.data: do NOT reset to factory
    # here, because read_factory_settings() would invalidate their datablocks.
    for obj in tuple(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    objects = []
    for mesh, label, xpos in [(old, "Legacy v0.3.1", -1.25), (puffy, "Puffy v0.4", 1.25)]:
        obj = bpy.data.objects.new(label, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.location.x = xpos
        objects.append(obj)
    from mathutils import Vector
    camera_data = bpy.data.cameras.new("CloudComparisonCamera")
    camera = bpy.data.objects.new("CloudComparisonCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (4.0, -7.0, 4.5)
    camera.rotation_euler = (Vector((0.0, 0.0, 0.0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 5.7
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 650
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    assert output.is_file() and output.stat().st_size > 5000
    return {"image": output.name, "bytes": output.stat().st_size}


def main():
    if "--" not in sys.argv or len(sys.argv) - sys.argv.index("--") != 4:
        raise SystemExit("usage: blender -b --python scripts/puffy_geometry_compare.py -- V031 V04 OUT")
    oldpath, newpath, outpath = sys.argv[sys.argv.index("--")+1:]
    oldpath, newpath, out = Path(oldpath).resolve(), Path(newpath).resolve(), Path(outpath).resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = {"status": "RUNNING", "blender": bpy.app.version_string, "checks": [], "warnings": []}
    meshes = []
    try:
        old = load_module(oldpath, "cloud_old_for_comparison")
        new = load_module(newpath, "cloud_v04_for_comparison")
        legacy = create(old, "Legacy")
        classic = create(new, "NewClassic", style="CLASSIC")
        puffy = create(new, "Puffy", style="PUFFY")
        meshes.extend([legacy, classic, puffy])

        assert len(legacy.vertices) == len(classic.vertices)
        assert len(legacy.polygons) == len(classic.polygons)
        assert all(tuple(a.co) == tuple(b.co)
                   for a, b in zip(legacy.vertices, classic.vertices))
        assert all(tuple(a.vertices) == tuple(b.vertices)
                   for a, b in zip(legacy.polygons, classic.polygons))
        report["checks"].append({"name":"classic_bitwise_equivalent_topology", "status":"PASS"})
        print("CLOUD_PUFF_PASS: classic_bitwise_equivalent_topology", flush=True)

        old_stats = inspect(legacy)
        new_stats = inspect(puffy)
        assert new_stats["max_z"] > old_stats["max_z"] + 0.30, (old_stats, new_stats)
        assert new_stats["signed_volume"] > 1.5 * old_stats["signed_volume"], (old_stats, new_stats)
        assert new_stats["vertices"] >= old_stats["vertices"] + 500
        report["legacy"] = old_stats
        report["puffy"] = new_stats
        report["checks"].append({"name":"closed_oriented_puffier_than_legacy", "status":"PASS"})
        print("CLOUD_PUFF_PASS: closed_oriented_puffier_than_legacy", flush=True)

        low = create(new, "LowPuff", style="PUFFY", puffiness=0.0)
        high = create(new, "HighPuff", style="PUFFY", puffiness=0.95)
        meshes.extend([low, high])
        a, b = inspect(low), inspect(high)
        assert b["max_z"] > a["max_z"] + 0.50
        report["checks"].append({"name":"puffiness_control_changes_height", "status":"PASS", "low":a["max_z"],"high":b["max_z"]})
        print("CLOUD_PUFF_PASS: puffiness_control_changes_height", flush=True)

        smooth = create(new, "NoOutline", style="PUFFY", outline_strength=0.0)
        uneven = create(new, "UnevenOutline", style="PUFFY", outline_strength=0.15)
        meshes.extend([smooth, uneven])
        # No-outline must not contain the extra angular modulation.
        a, b = inspect(smooth), inspect(uneven)
        assert abs(a["max_radial_extent"] - b["max_radial_extent"]) > 0.02
        report["checks"].append({"name":"outline_control_changes_silhouette", "status":"PASS"})
        print("CLOUD_PUFF_PASS: outline_control_changes_silhouette", flush=True)

        full_round = create(new, "Rounded", style="PUFFY", rim_roundness=0.30)
        no_round = create(new, "FlatRim", style="PUFFY", rim_roundness=0.0)
        meshes.extend([full_round, no_round])
        a, b = inspect(full_round), inspect(no_round)
        assert abs(a["signed_volume"] - b["signed_volume"]) > 0.03
        report["checks"].append({"name":"roundness_control_changes_volume", "status":"PASS"})
        print("CLOUD_PUFF_PASS: roundness_control_changes_volume", flush=True)

        try:
            report["preview"] = render_comparison(legacy, puffy, out / "cloud_v04_comparison.png")
        except Exception as exc:
            report["warnings"].append("Preview failure; numeric geometry still tested: " + repr(exc))
        report["status"] = "PASS"
        print("CLOUD_PUFF_NATIVE: PASS", flush=True)
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = repr(exc)
        report["traceback"] = traceback.format_exc()
        print("CLOUD_PUFF_NATIVE: FAIL", flush=True)
        raise
    finally:
        (out/"puffy_geometry_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
