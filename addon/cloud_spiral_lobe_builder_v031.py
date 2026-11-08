bl_info = {
    "name": "Cloud Spiral Lobe Builder",
    "author": "OpenAI / Chappy",
    "version": (0, 3, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Cloud Spiral",
    "description": "Self-made cloud spiral lobes, quad patch, v0.3.1: workflow presets, layout controls, safe geometry (自作アドオン).",
    "category": "Add Mesh",
}

import bpy
import math
from mathutils import Vector
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
)

TAU = math.tau
EPS = 1.0e-9


# ============================================================
# Math helpers
# ============================================================

def clamp01(x):
    return max(0.0, min(1.0, x))


def smoothstep01(x):
    x = clamp01(x)
    return x * x * (3.0 - 2.0 * x)


def smootherstep01(x):
    x = clamp01(x)
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def lerp(a, b, t):
    return a + (b - a) * t


def wrap_angle(angle):
    """Return angle in [-pi, pi]."""
    return (angle + math.pi) % TAU - math.pi


def lerp_angle(a, b, t):
    return a + wrap_angle(b - a) * t


def normalized_angular_segments(value):
    """
    Center patch uses a square-grid-to-disk patch.
    Its boundary count is 4 * (grid_n - 1),
    so angular segments must be a multiple of 4.
    """
    value = max(32, int(value))
    return max(32, int(round(value / 4.0)) * 4)


# ============================================================
# Shape functions
# ============================================================

def spiral_center_angle(radius_value, full_radius, start_angle, turns, direction_sign, spiral_power):
    u = clamp01(radius_value / max(full_radius, EPS))
    return (
        start_angle
        + direction_sign
        * TAU
        * turns
        * (u ** max(0.10, spiral_power))
    )


def dome_z(u, thickness, dome_height, dome_power):
    """
    A low, flattened dome:
    center = thickness + dome_height
    outer edge = thickness
    """
    u = clamp01(u)
    return (
        thickness
        + dome_height
        * max(
            0.0,
            1.0 - (u ** max(0.10, dome_power)),
        )
    )


def inner_strength(u, fade_end):
    if fade_end <= EPS:
        return 1.0
    if u >= fade_end:
        return 1.0
    return smootherstep01(u / fade_end)


def outer_strength(u, fade_start, fade_power):
    if u <= fade_start:
        return 1.0

    t = (
        (u - fade_start)
        / max(1.0 - fade_start, EPS)
    )
    t = smootherstep01(t)

    return max(
        0.0,
        (1.0 - t) ** max(0.10, fade_power),
    )


def groove_mask_from_xy(
    x,
    y,
    full_radius,
    start_angle,
    turns,
    direction_sign,
    spiral_power,
    groove_width_ratio,
    groove_edge_softness,
):
    """
    Returns 0..1:
      1 = groove center / floor
      0 = untouched land

    The groove width is controlled as a fraction of the spiral pitch,
    so it stays visually much more consistent from center to outside.

    groove_width_ratio:
        0.20 = groove is about 20% of one spiral pitch wide.

    groove_edge_softness:
        0.0 = almost hard edge
        1.0 = very rounded edge
    """
    r = math.hypot(x, y)

    if r <= EPS:
        return 0.0

    theta = math.atan2(y, x)

    target = spiral_center_angle(
        r,
        full_radius,
        start_angle,
        turns,
        direction_sign,
        spiral_power,
    )

    # Approximate physical distance from the current vertex
    # to the spiral centerline along the local circular arc.
    angular_distance = abs(
        wrap_angle(theta - target)
    )
    distance = angular_distance * r

    # One radial spiral pitch.
    pitch = (
        full_radius
        / max(turns, 0.25)
    )

    full_width = max(
        pitch * groove_width_ratio,
        full_radius * 0.002,
    )

    half_width = full_width * 0.5

    # Soft transition is expressed as a fraction of the groove width.
    soft = max(
        full_width * 0.5 * groove_edge_softness,
        full_radius * 0.0005,
    )

    core_half = max(
        0.0,
        half_width - soft,
    )

    if distance <= core_half:
        return 1.0

    if distance >= half_width:
        return 0.0

    t = (
        (distance - core_half)
        / max(half_width - core_half, EPS)
    )

    return 1.0 - smootherstep01(t)


def top_height(
    x,
    y,
    radius,
    thickness,
    dome_height_ratio,
    dome_power,
    spiral_enabled,
    start_angle,
    turns,
    direction_sign,
    spiral_power,
    groove_depth_ratio,
    groove_width_ratio,
    groove_edge_softness,
    inner_fade_end,
    outer_fade_start,
    outer_fade_power,
):
    r = math.hypot(x, y)
    u = clamp01(r / max(radius, EPS))

    z = dome_z(
        u,
        thickness,
        radius * dome_height_ratio,
        dome_power,
    )

    if not spiral_enabled:
        return z

    mask = groove_mask_from_xy(
        x,
        y,
        radius,
        start_angle,
        turns,
        direction_sign,
        spiral_power,
        groove_width_ratio,
        groove_edge_softness,
    )

    amp = (
        inner_strength(u, inner_fade_end)
        * outer_strength(
            u,
            outer_fade_start,
            outer_fade_power,
        )
    )

    depth = (
        radius
        * groove_depth_ratio
        * mask
        * amp
    )

    # Keep the groove above the bottom. The old extreme settings could pierce the base.
    return max(thickness * 0.10, z - depth)


# ============================================================
# Center quad patch
# ============================================================

def square_to_disk(sx, sy):
    """
    Squircular mapping.
    The square boundary maps exactly to a circle.
    """
    dx = sx * math.sqrt(
        max(0.0, 1.0 - 0.5 * sy * sy)
    )
    dy = sy * math.sqrt(
        max(0.0, 1.0 - 0.5 * sx * sx)
    )
    return dx, dy


def create_center_patch(
    verts,
    faces,
    angular_segments,
    patch_radius,
    patch_rotation,
    height_func,
):
    """
    Create an all-quad square grid mapped onto a disk.

    Returns:
        boundary vertex indices in CCW order
    """
    n = angular_segments // 4 + 1

    grid = [
        [None for _ in range(n)]
        for _ in range(n)
    ]

    c = math.cos(patch_rotation)
    s = math.sin(patch_rotation)

    for j in range(n):
        sy = -1.0 + 2.0 * j / (n - 1)

        for i in range(n):
            sx = -1.0 + 2.0 * i / (n - 1)

            dx, dy = square_to_disk(
                sx,
                sy,
            )

            x0 = dx * patch_radius
            y0 = dy * patch_radius

            x = c * x0 - s * y0
            y = s * x0 + c * y0

            z = height_func(x, y)

            idx = len(verts)
            verts.append((x, y, z))
            grid[j][i] = idx

    # All-quads interior.
    for j in range(n - 1):
        for i in range(n - 1):
            a = grid[j][i]
            b = grid[j][i + 1]
            cidx = grid[j + 1][i + 1]
            d = grid[j + 1][i]

            faces.append(
                (a, b, cidx, d)
            )

    # CCW perimeter:
    # bottom L->R
    # right B->T
    # top R->L
    # left T->B
    boundary = []

    for i in range(n):
        boundary.append(
            grid[0][i]
        )

    for j in range(1, n):
        boundary.append(
            grid[j][n - 1]
        )

    for i in range(n - 2, -1, -1):
        boundary.append(
            grid[n - 1][i]
        )

    for j in range(n - 2, 0, -1):
        boundary.append(
            grid[j][0]
        )

    assert len(boundary) == angular_segments

    return boundary


# ============================================================
# Lobe mesh
# ============================================================

def create_lobe_mesh(
    name,
    radius,
    thickness,
    angular_segments,
    radial_segments,
    inner_spiral_radius_ratio,
    center_patch_ratio,
    transition_rings,
    transition_twist_deg,
    turns,
    start_angle_deg,
    direction_sign,
    spiral_power,
    spiral_enabled,
    groove_depth_ratio,
    groove_width_ratio,
    groove_edge_softness,
    inner_fade_end,
    outer_fade_start,
    outer_fade_power,
    dome_height_ratio,
    dome_power,
):
    radius = max(0.001, radius)

    angular_segments = normalized_angular_segments(
        angular_segments
    )

    radial_segments = max(
        4,
        int(radial_segments),
    )

    transition_rings = max(
        0,
        int(transition_rings),
    )

    inner_radius = (
        radius
        * clamp01(inner_spiral_radius_ratio)
    )

    patch_radius = (
        inner_radius
        * clamp01(center_patch_ratio)
    )

    patch_radius = min(
        patch_radius,
        inner_radius * 0.95,
    )

    start_angle = math.radians(
        start_angle_deg
    )

    # Height callback shared by patch / transition / spiral region.
    def height_func(x, y):
        return top_height(
            x=x,
            y=y,
            radius=radius,
            thickness=thickness,
            dome_height_ratio=dome_height_ratio,
            dome_power=dome_power,
            spiral_enabled=spiral_enabled,
            start_angle=start_angle,
            turns=turns,
            direction_sign=direction_sign,
            spiral_power=spiral_power,
            groove_depth_ratio=groove_depth_ratio,
            groove_width_ratio=groove_width_ratio,
            groove_edge_softness=groove_edge_softness,
            inner_fade_end=inner_fade_end,
            outer_fade_start=outer_fade_start,
            outer_fade_power=outer_fade_power,
        )

    verts = []
    faces = []
    top_face_count = 0

    # --------------------------------------------------------
    # 1) Quad center patch
    # --------------------------------------------------------

    # Boundary index 0 of the mapped square starts at -135 deg.
    # Rotate it so that it points along the inner spiral direction.
    patch_target_angle = spiral_center_angle(
        patch_radius,
        radius,
        start_angle,
        turns,
        direction_sign,
        spiral_power,
    )

    patch_rotation = (
        patch_target_angle
        + math.radians(135.0)
    )

    boundary = create_center_patch(
        verts=verts,
        faces=faces,
        angular_segments=angular_segments,
        patch_radius=patch_radius,
        patch_rotation=patch_rotation,
        height_func=height_func,
    )

    top_face_count = len(faces)

    # Actual angles of center patch boundary.
    boundary_angles = []

    for vid in boundary:
        x, y, _z = verts[vid]
        boundary_angles.append(
            math.atan2(y, x)
        )

    # --------------------------------------------------------
    # 2) Transition rings
    # --------------------------------------------------------

    previous_ring = boundary

    transition_twist = math.radians(
        transition_twist_deg
    ) * direction_sign

    for tr in range(1, transition_rings + 1):
        t = tr / (transition_rings + 1)
        tt = smootherstep01(t)

        r = lerp(
            patch_radius,
            inner_radius,
            t,
        )

        spiral_angle = spiral_center_angle(
            r,
            radius,
            start_angle,
            turns,
            direction_sign,
            spiral_power,
        )

        # The first column follows the groove center.
        target_start = (
            spiral_angle
            + transition_twist * (1.0 - t)
        )

        ring = []

        for j in range(angular_segments):
            target_angle = (
                target_start
                + TAU * j / angular_segments
            )

            angle = lerp_angle(
                boundary_angles[j],
                target_angle,
                tt,
            )

            x = math.cos(angle) * r
            y = math.sin(angle) * r
            z = height_func(x, y)

            ring.append(len(verts))
            verts.append((x, y, z))

        for j in range(angular_segments):
            jn = (j + 1) % angular_segments

            # CCW top winding (outward +Z); matches the center quad patch.
            faces.append((
                previous_ring[j],
                ring[j],
                ring[jn],
                previous_ring[jn],
            ))

        previous_ring = ring

    # --------------------------------------------------------
    # 3) Spiral-aligned rings
    # --------------------------------------------------------

    spiral_rings = []

    radial_power = 1.10

    for ri in range(radial_segments + 1):
        t = ri / radial_segments
        tr = t ** radial_power

        r = lerp(
            inner_radius,
            radius,
            tr,
        )

        center_angle = spiral_center_angle(
            r,
            radius,
            start_angle,
            turns,
            direction_sign,
            spiral_power,
        )

        ring = []

        for j in range(angular_segments):
            angle = (
                center_angle
                + TAU * j / angular_segments
            )

            x = math.cos(angle) * r
            y = math.sin(angle) * r
            z = height_func(x, y)

            ring.append(len(verts))
            verts.append((x, y, z))

        spiral_rings.append(ring)

    # Connect last transition / patch directly to first spiral ring.
    first_spiral = spiral_rings[0]

    for j in range(angular_segments):
        jn = (j + 1) % angular_segments

        faces.append((
            previous_ring[j],
            first_spiral[j],
            first_spiral[jn],
            previous_ring[jn],
        ))

    # Spiral ring quads.
    for ri in range(len(spiral_rings) - 1):
        r0 = spiral_rings[ri]
        r1 = spiral_rings[ri + 1]

        for j in range(angular_segments):
            jn = (j + 1) % angular_segments

            faces.append((
                r0[j],
                r1[j],
                r1[jn],
                r0[jn],
            ))

    top_face_count = len(faces)

    # --------------------------------------------------------
    # 4) Bottom and side
    # --------------------------------------------------------

    outer_ring = spiral_rings[-1]

    bottom_ring = []

    for top_idx in outer_ring:
        x, y, _z = verts[top_idx]
        bottom_ring.append(
            len(verts)
        )
        verts.append((x, y, 0.0))

    bottom_center = len(verts)
    verts.append((0.0, 0.0, 0.0))

    # Side quads.
    for j in range(angular_segments):
        jn = (j + 1) % angular_segments

        # Side points radially out, coherent with the CCW top and -Z bottom.
        faces.append((
            outer_ring[j],
            bottom_ring[j],
            bottom_ring[jn],
            outer_ring[jn],
        ))

    # Bottom fan (bottom topology is irrelevant for sculpting).
    for j in range(angular_segments):
        jn = (j + 1) % angular_segments

        faces.append((
            bottom_center,
            bottom_ring[jn],
            bottom_ring[j],
        ))

    # --------------------------------------------------------
    # Mesh
    # --------------------------------------------------------

    mesh = bpy.data.meshes.new(name + "_Mesh")
    try:
        mesh.from_pydata(verts, [], faces)
        mesh.validate(clean_customdata=False)
        mesh.update()

        # Top smooth, sides/bottom flat.
        for i, poly in enumerate(mesh.polygons):
            poly.use_smooth = i < top_face_count
        return mesh, angular_segments
    except Exception:
        # Avoid leaking an orphan Mesh if Blender rejects the new geometry.
        bpy.data.meshes.remove(mesh, do_unlink=True)
        raise


# ============================================================
# Reference layouts
# ============================================================

def reference_three_layout():
    return [
        # (x factor, y factor, scale, angle offset, z factor)
        (0.30, 0.10, 1.00,   0.0, 0.000),
        (-0.70, 0.72, 0.74,  28.0, 0.020),
        (-0.76, -0.60, 0.78, -22.0, 0.010),
    ]


# ============================================================
# Settings
# ============================================================

class CLOUDSPIRAL_Settings(PropertyGroup):

    ui_show_advanced: BoolProperty(
        name="詳細設定を表示",
        description="中央トポロジーや溝の細かい設定を表示します",
        default=False,
    )

    mode: EnumProperty(
        name="生成モード",
        items=[
            ('SINGLE', "単体", "渦ローブを1個生成"),
            ('REFERENCE_3', "参考画像風3個", "3ローブを別オブジェクトで配置"),
        ],
        default='SINGLE',
    )

    three_spread: FloatProperty(
        name="3ローブの広がり",
        description="中央から左右のローブまでの距離。1.0で旧バージョンと同じ配置",
        default=1.0,
        min=0.4,
        max=2.0,
    )

    three_side_scale: FloatProperty(
        name="左右ローブの大きさ",
        description="中央ローブは変更せず、左右2個の大きさだけを調整",
        default=1.0,
        min=0.5,
        max=1.25,
    )

    spiral_enabled: BoolProperty(
        name="渦あり",
        default=True,
    )

    radius: FloatProperty(
        name="半径",
        default=1.0,
        min=0.05,
        soft_max=10.0,
    )

    thickness: FloatProperty(
        name="本体厚み",
        default=0.16,
        min=0.02,
        soft_max=2.0,
    )

    turns: FloatProperty(
        name="巻き数",
        default=1.12,
        min=0.35,
        max=2.50,
    )

    start_angle: FloatProperty(
        name="渦の向き",
        default=-80.0,
        min=-360.0,
        max=360.0,
    )

    direction: EnumProperty(
        name="巻き方向",
        items=[
            ('CCW', "反時計", ""),
            ('CW', "時計", ""),
            ('ALTERNATE', "交互", "複数生成時のみ"),
        ],
        default='CCW',
    )

    spiral_power: FloatProperty(
        name="渦の詰まり",
        description="1=ほぼアルキメデス型。大きいほど中心側が緩く外側で回る",
        default=1.0,
        min=0.35,
        max=2.50,
    )

    angular_segments: IntProperty(
        name="円周分割",
        default=128,
        min=32,
        max=512,
    )

    radial_segments: IntProperty(
        name="半径方向分割",
        default=32,
        min=8,
        max=160,
    )

    inner_spiral_radius_ratio: FloatProperty(
        name="螺旋開始半径",
        default=0.24,
        min=0.08,
        max=0.45,
        subtype='FACTOR',
    )

    center_patch_ratio: FloatProperty(
        name="中央パッチ比率",
        description="螺旋開始半径に対するQuad中央パッチの大きさ",
        default=0.58,
        min=0.25,
        max=0.90,
        subtype='FACTOR',
    )

    transition_rings: IntProperty(
        name="中央遷移リング",
        default=3,
        min=0,
        max=8,
    )

    transition_twist_deg: FloatProperty(
        name="中央ねじり",
        default=18.0,
        min=-90.0,
        max=90.0,
    )

    dome_height_ratio: FloatProperty(
        name="ドーム高さ",
        default=0.14,
        min=0.0,
        max=0.50,
        subtype='FACTOR',
    )

    dome_power: FloatProperty(
        name="ドーム形状",
        default=1.75,
        min=0.20,
        max=4.0,
    )

    groove_depth_ratio: FloatProperty(
        name="彫り深さ",
        default=0.095,
        min=0.0,
        max=0.35,
        subtype='FACTOR',
    )

    groove_width_ratio: FloatProperty(
        name="溝幅",
        description="螺旋1ピッチに対する溝幅。0.20ならピッチ幅の約20%",
        default=0.20,
        min=0.03,
        max=0.65,
        subtype='FACTOR',
    )

    groove_edge_softness: FloatProperty(
        name="溝縁の丸み",
        description="溝の縁をどのくらい丸くするか。0で硬く、1でかなり丸い",
        default=0.45,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
    )

    inner_fade_end: FloatProperty(
        name="中心なじみ",
        default=0.12,
        min=0.0,
        max=0.40,
        subtype='FACTOR',
    )

    outer_fade_start: FloatProperty(
        name="外周なだらか開始",
        default=0.58,
        min=0.20,
        max=0.95,
        subtype='FACTOR',
    )

    outer_fade_power: FloatProperty(
        name="外周なだらか強さ",
        default=1.60,
        min=0.20,
        max=4.0,
    )


# ============================================================
# Operators
# ============================================================

class MESH_OT_cloud_spiral_preset(Operator):
    bl_idname = "mesh.cloud_spiral_preset"
    bl_label = "雲の溝スタイル"
    bl_description = "半径・解像度は維持したまま、溝とドームのスタイルを切り替え"
    bl_options = {'REGISTER', 'UNDO'}

    preset: EnumProperty(
        name="スタイル",
        items=[
            ('SOFT', "ふんわり", "浅い溝と丸い縁のふんわり雲"),
            ('CARVED', "くっきり", "深い溝を彫った雲"),
            ('RESET', "標準", "旧v0.3の初期溝・ドーム設定"),
        ],
        default='RESET',
    )

    @classmethod
    def poll(cls, context):
        return context.scene is not None and hasattr(context.scene, "cloud_spiral_settings")

    def execute(self, context):
        s = context.scene.cloud_spiral_settings
        profiles = {
            'SOFT': (0.055, 0.24, 0.75, 0.18),
            'CARVED': (0.14, 0.20, 0.30, 0.10),
            'RESET': (0.095, 0.20, 0.45, 0.14),
        }
        depth, width, softness, dome = profiles[self.preset]
        s.groove_depth_ratio = depth
        s.groove_width_ratio = width
        s.groove_edge_softness = softness
        s.dome_height_ratio = dome
        s.spiral_enabled = True
        self.report({'INFO'}, "雲のスタイルを適用しました。生成ボタンで反映されます。")
        return {'FINISHED'}


class MESH_OT_cloud_spiral_generate(Operator):
    bl_idname = "mesh.cloud_spiral_generate"
    bl_label = "渦ローブ生成"
    bl_description = "Quad中央パッチ＋螺旋エッジフローで渦ローブを生成"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        s = context.scene.cloud_spiral_settings
        actual_segments = normalized_angular_segments(s.angular_segments)
        if actual_segments != s.angular_segments:
            self.report({'INFO'}, f"中央Quadパッチのため円周分割を {actual_segments} に丸めました。")

        layout = ([(0.0, 0.0, 1.0, 0.0, 0.0)] if s.mode == 'SINGLE'
                  else reference_three_layout())

        original_selection = tuple(context.selected_objects)
        original_active = context.view_layer.objects.active
        root = None
        created_objects = []
        created_meshes = []

        try:
            root = bpy.data.objects.new("CloudSpiral_Group", None)
            context.collection.objects.link(root)
            root.location = context.scene.cursor.location.copy()
            root.empty_display_type = 'PLAIN_AXES'

            for i, (xf, yf, scale, angle_offset, zf) in enumerate(layout):
                if s.mode == 'REFERENCE_3' and i > 0:
                    xf *= s.three_spread
                    yf *= s.three_spread
                    scale *= s.three_side_scale
                if s.direction == 'CW':
                    direction_sign = -1.0
                elif s.direction == 'ALTERNATE':
                    direction_sign = 1.0 if i % 2 == 0 else -1.0
                else:
                    direction_sign = 1.0

                mesh, used_segments = create_lobe_mesh(
                    name=f"CloudSpiral_Lobe_{i+1:02d}",
                    radius=s.radius * scale,
                    thickness=s.thickness * scale,
                    angular_segments=actual_segments,
                    radial_segments=s.radial_segments,
                    inner_spiral_radius_ratio=s.inner_spiral_radius_ratio,
                    center_patch_ratio=s.center_patch_ratio,
                    transition_rings=s.transition_rings,
                    transition_twist_deg=s.transition_twist_deg,
                    turns=s.turns,
                    start_angle_deg=s.start_angle + angle_offset,
                    direction_sign=direction_sign,
                    spiral_power=s.spiral_power,
                    spiral_enabled=s.spiral_enabled,
                    groove_depth_ratio=s.groove_depth_ratio,
                    groove_width_ratio=s.groove_width_ratio,
                    groove_edge_softness=s.groove_edge_softness,
                    inner_fade_end=s.inner_fade_end,
                    outer_fade_start=s.outer_fade_start,
                    outer_fade_power=s.outer_fade_power,
                    dome_height_ratio=s.dome_height_ratio,
                    dome_power=s.dome_power,
                )
                created_meshes.append(mesh)
                obj = bpy.data.objects.new(f"CloudSpiral_Lobe_{i+1:02d}", mesh)
                created_objects.append(obj)
                context.collection.objects.link(obj)
                obj.parent = root
                obj.location = (xf * s.radius, yf * s.radius, zf * s.radius)
                obj["cloud_spiral_lobe"] = True
                obj["cloud_spiral_segments"] = used_segments

            # Do not use bpy.ops: it depends on active context and is harder to roll back.
            for obj in original_selection:
                obj.select_set(False)
            for obj in created_objects:
                obj.select_set(True)
            context.view_layer.objects.active = created_objects[0]

            self.report({'INFO'}, f"{len(created_objects)} 個のローブを生成しました。")
            return {'FINISHED'}
        except Exception as exc:
            # Roll back any partially-created objects/meshes and restore user selection.
            for obj in reversed(created_objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            if root is not None:
                bpy.data.objects.remove(root, do_unlink=True)
            for mesh in reversed(created_meshes):
                bpy.data.meshes.remove(mesh, do_unlink=True)
            for obj in original_selection:
                obj.select_set(True)
            context.view_layer.objects.active = original_active
            self.report({'ERROR'}, f"雲の生成を取り消しました: {exc}")
            return {'CANCELLED'}


# ============================================================
# Panel
# ============================================================

class VIEW3D_PT_cloud_spiral_builder(Panel):
    bl_label = "Cloud Spiral Lobe Builder"
    bl_idname = "VIEW3D_PT_cloud_spiral_builder"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Cloud Spiral"

    def draw(self, context):
        layout = self.layout
        s = context.scene.cloud_spiral_settings

        box = layout.box()
        box.label(text="生成", icon='OUTLINER_OB_MESH')
        box.prop(s, "mode", expand=True)
        box.prop(s, "radius")
        box.prop(s, "thickness")
        if s.mode == 'REFERENCE_3':
            column = box.column(align=True)
            column.label(text="3つの独立ローブを配置")
            column.prop(s, "three_spread", slider=True)
            column.prop(s, "three_side_scale", slider=True)

        box = layout.box()
        box.label(text="渦の基本設定", icon='FORCE_VORTEX')
        box.prop(s, "spiral_enabled")
        spiral = box.column(align=True)
        spiral.enabled = s.spiral_enabled
        spiral.prop(s, "turns", slider=True)
        spiral.prop(s, "direction", expand=True)
        if s.mode == 'SINGLE' and s.direction == 'ALTERNATE':
            spiral.label(text="単体時の交互は反時計として生成", icon='INFO')
        spiral.prop(s, "groove_depth_ratio", slider=True)
        spiral.prop(s, "dome_height_ratio", slider=True)

        box = layout.box()
        box.label(text="溝スタイル（現在の半径を維持）")
        row = box.row(align=True)
        row.operator(MESH_OT_cloud_spiral_preset.bl_idname, text="ふんわり").preset = 'SOFT'
        row.operator(MESH_OT_cloud_spiral_preset.bl_idname, text="くっきり").preset = 'CARVED'
        row.operator(MESH_OT_cloud_spiral_preset.bl_idname, text="標準").preset = 'RESET'
        box.label(text="スタイル選択後に生成ボタンを押す", icon='INFO')

        layout.prop(s, "ui_show_advanced", toggle=True)
        if s.ui_show_advanced:
            box = layout.box()
            box.label(text="詳細：螺旋")
            spiral = box.column(align=True)
            spiral.enabled = s.spiral_enabled
            spiral.prop(s, "start_angle")
            spiral.prop(s, "spiral_power", slider=True)
            spiral.prop(s, "groove_width_ratio", slider=True)
            spiral.prop(s, "groove_edge_softness", slider=True)
            spiral.prop(s, "inner_fade_end", slider=True)
            spiral.prop(s, "outer_fade_start", slider=True)
            spiral.prop(s, "outer_fade_power")

            box = layout.box()
            box.label(text="詳細：中央トポロジー")
            box.prop(s, "inner_spiral_radius_ratio")
            box.prop(s, "center_patch_ratio")
            box.prop(s, "transition_rings")
            box.prop(s, "transition_twist_deg")

            box = layout.box()
            box.label(text="詳細：形状と分割")
            box.prop(s, "dome_power")
            box.prop(s, "angular_segments")
            box.prop(s, "radial_segments")
            box.label(text="円周分割は4の倍数に自動調整", icon='INFO')

        layout.separator()
        col = layout.column()
        col.enabled = context.mode == 'OBJECT'
        col.scale_y = 1.5
        col.operator(
            MESH_OT_cloud_spiral_generate.bl_idname,
            text="渦雲を生成",
            icon='MESH_CIRCLE',
        )
        if context.mode != 'OBJECT':
            layout.label(text="オブジェクトモードで生成できます", icon='INFO')



classes = (
    CLOUDSPIRAL_Settings,
    MESH_OT_cloud_spiral_preset,
    MESH_OT_cloud_spiral_generate,
    VIEW3D_PT_cloud_spiral_builder,
)


def register():
    registered = []
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
            registered.append(cls)
        bpy.types.Scene.cloud_spiral_settings = PointerProperty(type=CLOUDSPIRAL_Settings)
    except Exception:
        if hasattr(bpy.types.Scene, "cloud_spiral_settings"):
            del bpy.types.Scene.cloud_spiral_settings
        for cls in reversed(registered):
            bpy.utils.unregister_class(cls)
        raise


def unregister():
    if hasattr(
        bpy.types.Scene,
        "cloud_spiral_settings",
    ):
        del bpy.types.Scene.cloud_spiral_settings

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
