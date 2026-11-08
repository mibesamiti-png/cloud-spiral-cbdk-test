"""Native (not mocked) Blender smoke suite for Cloud Spiral v0.3.1.

Only synthetic meshes are generated. Blender --background --factory-startup
--python-exit-code 1 --python scripts/native_smoke.py -- SOURCE OUT
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path

import bpy


def inspect_mesh(mesh):
    edges = defaultdict(list)
    volume = 0.0
    degenerate = 0
    quad_count = 0
    for poly in mesh.polygons:
        ring = tuple(poly.vertices)
        if len(ring) == 4:
            quad_count += 1
        if len(ring) < 3 or len(set(ring)) != len(ring):
            degenerate += 1
            continue
        for a, b in zip(ring, ring[1:] + ring[:1]):
            edges[tuple(sorted((a, b)))].append((a, b))
        anchor = mesh.vertices[ring[0]].co
        for i in range(1, len(ring)-1):
            b = mesh.vertices[ring[i]].co
            c = mesh.vertices[ring[i+1]].co
            volume += anchor.dot(b.cross(c)) / 6.0
    boundary = sum(len(v)==1 for v in edges.values())
    nonmanifold = sum(len(v)!=2 for v in edges.values())
    winding = sum(len(v)==2 and v[0] != v[1][::-1] for v in edges.values())
    min_z = min(v.co.z for v in mesh.vertices)
    max_z = max(v.co.z for v in mesh.vertices)
    stats = {
        'vertices': len(mesh.vertices), 'faces': len(mesh.polygons),
        'quads': quad_count, 'boundary_edges': boundary,
        'nonmanifold_edges': nonmanifold, 'winding_conflicts': winding,
        'degenerate_faces': degenerate, 'signed_volume': round(volume, 7),
        'min_z': round(min_z, 7), 'max_z': round(max_z, 7),
    }
    assert stats['vertices'] > 100 and quad_count > 100, stats
    assert not boundary and not nonmanifold and not winding and not degenerate, stats
    assert volume > 0 and min_z >= -0.00001 and max_z > 0, stats
    return stats


def lobes():
    return [o for o in bpy.data.objects if o.type == 'MESH' and o.get('cloud_spiral_lobe')]


def run(source, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    spec = importlib.util.spec_from_file_location('cloud_spiral_lobe_builder_v031', source)
    assert spec is not None and spec.loader is not None
    addon = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = addon
    spec.loader.exec_module(addon)
    assert tuple(addon.bl_info['version']) == (0, 3, 1)

    evidence = {
        'status': 'RUNNING', 'blender': bpy.app.version_string,
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'checks': [], 'meshes': [],
        'limitations': [
            'Background Blender is not proof of Windows GUI/Undo interaction.',
            'Closed oriented geometry does not prove no self-intersection or 3D print quality.'
        ],
    }
    registered = False

    def check(name, test):
        start = time.perf_counter()
        result = test()
        evidence['checks'].append({
            'name': name, 'status': 'PASS',
            'duration_ms': round((time.perf_counter()-start)*1000, 2),
            'result': result,
        })
        print('CLOUD_NATIVE_PASS: ' + name, flush=True)
        return result

    try:
        check('register', addon.register)
        registered = True
        assert hasattr(bpy.types.Scene, 'cloud_spiral_settings')
        settings = bpy.context.scene.cloud_spiral_settings
        assert hasattr(settings, 'mode')
        assert addon.VIEW3D_PT_cloud_spiral_builder.bl_category == 'Cloud Spiral'
        check('panel_and_properties_registered', lambda: {
            'panel': addon.VIEW3D_PT_cloud_spiral_builder.bl_idname,
            'operator': addon.MESH_OT_cloud_spiral_generate.bl_idname
        })

        def ui_presets():
            assert settings.ui_show_advanced is False
            assert abs(settings.three_spread - 1) < 0.0001
            assert abs(settings.three_side_scale - 1) < 0.0001
            original_radius = settings.radius
            original_angular = settings.angular_segments
            for preset, depth in [('SOFT', 0.055), ('CARVED', 0.14), ('RESET', 0.095)]:
                assert bpy.ops.mesh.cloud_spiral_preset(preset=preset) == {'FINISHED'}
                assert abs(settings.groove_depth_ratio - depth) < 0.00001
                assert settings.radius == original_radius
                assert settings.angular_segments == original_angular
            settings.ui_show_advanced = True
            assert settings.ui_show_advanced is True
            settings.ui_show_advanced = False
            return {'presets': 3, 'advanced_toggle': 'PASS', 'unchanged_radius': original_radius}
        check('ui_presets_and_advanced_toggle', ui_presets)

        def single():
            settings.mode = 'SINGLE'
            settings.spiral_enabled = True
            result = bpy.ops.mesh.cloud_spiral_generate()
            assert result == {'FINISHED'}, result
            objs = lobes()
            assert len(objs) == 1, len(objs)
            assert bpy.context.view_layer.objects.active == objs[0]
            stats = inspect_mesh(objs[0].data)
            evidence['meshes'].append(stats)
            return stats
        check('single_lobe_closed_oriented', single)

        def spiral_switch():
            baseline = lobes()[-1].data
            settings.spiral_enabled = False
            assert bpy.ops.mesh.cloud_spiral_generate() == {'FINISHED'}
            other = bpy.context.view_layer.objects.active.data
            assert len(baseline.vertices) == len(other.vertices)
            difference = sum(abs(x.co.z-y.co.z) for x,y in zip(baseline.vertices,other.vertices))
            assert difference > 0.01, difference
            return {'z_delta_sum': round(difference,5), 'mesh': inspect_mesh(other)}
        check('spiral_enabled_affects_mesh', spiral_switch)

        def three():
            settings.mode = 'REFERENCE_3'
            settings.spiral_enabled = True
            settings.direction = 'ALTERNATE'
            assert bpy.ops.mesh.cloud_spiral_generate() == {'FINISHED'}
            objs = lobes()
            assert len(objs) == 5, len(objs)
            selected = [o for o in objs if o.select_get()]
            assert len(selected) == 3, len(selected)
            for obj in selected:
                evidence['meshes'].append(inspect_mesh(obj.data))
            return {'total_lobes': len(objs), 'selected':len(selected)}
        check('three_lobe_layout_and_selection', three)

        def custom_three():
            before = len(lobes())
            baseline = lobes()[3].data
            old_max_x = max(v.co.x for v in baseline.vertices)
            settings.three_spread = 1.5
            settings.three_side_scale = 0.7
            assert bpy.ops.mesh.cloud_spiral_generate() == {'FINISHED'}
            added = lobes()[before:]
            assert len(added) == 3, len(added)
            assert abs(added[1].location.x - (-0.7 * 1.5 * settings.radius)) < 0.0001
            assert abs(added[1].location.y - (0.72 * 1.5 * settings.radius)) < 0.0001
            assert abs(added[2].location.x - (-0.76 * 1.5 * settings.radius)) < 0.0001
            new_max_x = max(v.co.x for v in added[1].data.vertices)
            assert abs((new_max_x / old_max_x) - 0.7) < 0.01, (new_max_x, old_max_x)
            for obj in added:
                inspect_mesh(obj.data)
            settings.three_spread = 1.0
            settings.three_side_scale = 1.0
            return {'generated': len(added), 'side_scale_ratio': round(new_max_x / old_max_x, 4)}
        check('three_lobe_custom_layout', custom_three)

        def extreme():
            settings.mode = 'SINGLE'
            settings.radial_segments = 8
            settings.angular_segments = 33
            settings.transition_rings = 0
            settings.thickness = 0.02
            settings.groove_depth_ratio = 0.35
            assert bpy.ops.mesh.cloud_spiral_generate() == {'FINISHED'}
            obj = bpy.context.view_layer.objects.active
            assert obj['cloud_spiral_segments'] % 4 == 0
            return inspect_mesh(obj.data)
        check('extreme_valid_parameters', extreme)

        def repeat():
            settings.mode = 'SINGLE'
            settings.spiral_enabled = True
            stats = []
            for _ in range(3):
                assert bpy.ops.mesh.cloud_spiral_generate() == {'FINISHED'}
                stats.append(inspect_mesh(bpy.context.view_layer.objects.active.data))
            return {'runs':len(stats), 'first_vertices': stats[0]['vertices']}
        check('repeat_generation', repeat)

        try:
            image = out/'cloud_preview.png'
            cam_data=bpy.data.cameras.new('TestCamera')
            cam=bpy.data.objects.new('TestCamera',cam_data)
            bpy.context.scene.collection.objects.link(cam)
            cam.location=(2.5,-4.5,3.4)
            from mathutils import Vector
            cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
            cam_data.type='ORTHO'
            cam_data.ortho_scale=6.5
            bpy.context.scene.camera=cam
            scene=bpy.context.scene
            scene.render.engine='BLENDER_WORKBENCH'
            scene.render.resolution_x=800
            scene.render.resolution_y=600
            scene.render.resolution_percentage=100
            scene.render.filepath=str(image)
            bpy.ops.render.render(write_still=True)
            evidence['preview_image']=str(image.name)
        except Exception as exc:
            evidence['preview_warning']=repr(exc)
            print('CLOUD_RENDER_WARNING: '+repr(exc), flush=True)

        bpy.ops.wm.save_as_mainfile(filepath=str(out/'cloud_test.blend'))
        check('unregister', addon.unregister)
        registered = False
        assert not hasattr(bpy.types.Scene, 'cloud_spiral_settings')
        check('re_register', addon.register)
        registered = True
        assert hasattr(bpy.types.Scene, 'cloud_spiral_settings')
        check('re_unregister', addon.unregister)
        registered = False
        assert not hasattr(bpy.types.Scene, 'cloud_spiral_settings')
        evidence['status'] = 'PASS'
        return evidence
    finally:
        if registered:
            addon.unregister()


def main():
    if '--' not in sys.argv or len(sys.argv) - sys.argv.index('--') < 3:
        raise SystemExit('usage: blender -b --python scripts/native_smoke.py -- SOURCE OUT')
    args=sys.argv[sys.argv.index('--')+1:]
    src=Path(args[0]).resolve()
    out=Path(args[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    start=time.perf_counter()
    try:
        report=run(src,out)
        report['wall_seconds']=round(time.perf_counter()-start,3)
        (out/'native_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('CLOUD_REAL_BLENDER: PASS',flush=True)
    except Exception as exc:
        report={
            'status':'FAIL', 'error':repr(exc), 'traceback':traceback.format_exc(),
            'blender':bpy.app.version_string,
            'wall_seconds':round(time.perf_counter()-start,3),
        }
        (out/'native_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('CLOUD_REAL_BLENDER: FAIL',flush=True)
        raise

if __name__ == '__main__':
    main()

