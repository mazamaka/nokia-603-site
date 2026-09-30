"""Nokia 603 studio renders (Blender 5.x, Cycles/Metal).

Run:  Blender -b --factory-startup -P scene.py -- <shot> [<shot> ...] [--samples N] [--scale 0.5]
Model units are metres, dimensions from Nokia's spec sheet (113.5 x 57.1 x 12.7 mm).
"""
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
TEX = HERE / "tex"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
MM = 0.001
A, B, R = 28.55, 56.75, 9.0  # half width, half height, corner radius (mm)


def log(msg: str, *args) -> None:
    print(f"[scene {time.strftime('%H:%M:%S')}] " + msg.format(*args), flush=True)


def srgb(hexstr: str, a: float = 1.0) -> tuple:
    c = [int(hexstr[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*lin, a)


COVERS = {  # colour, roughness, coat weight
    "black": ("#151517", 0.34, 0.25),
    "white": ("#EDECE8", 0.22, 0.75),
    "fuchsia": ("#A30D3D", 0.2, 0.8),
    "green": ("#3E9A2C", 0.2, 0.8),
    "yellow": ("#E6C200", 0.26, 0.5),
    "blue": ("#1F3FA8", 0.2, 0.8),
}
PRINT = {"black": "#8E9196", "white": "#63666B", "fuchsia": "#D9D6D8", "green": "#EEF0EE", "yellow": "#6E6A5E", "blue": "#D6D9E0"}


# ---------------------------------------------------------------- geometry
def rrect(a: float, b: float, r: float, nc: int = 16, nl: int = 40, ns: int = 20) -> list[tuple[float, float]]:
    """Rounded rectangle, CCW from (a, 0); constant point count so rings can be bridged."""
    r = max(0.0, min(r, a, b))
    pts = []
    pts += [(a, (b - r) * i / (nl // 2)) for i in range(nl // 2)]
    for cx, cy, a0, seg in (
        (a - r, b - r, 0, [(a - r - (2 * (a - r)) * i / ns, b) for i in range(ns)]),
        (-(a - r), b - r, 90, [(-a, (b - r) - 2 * (b - r) * i / nl) for i in range(nl)]),
        (-(a - r), -(b - r), 180, [(-(a - r) + 2 * (a - r) * i / ns, -b) for i in range(ns)]),
        (a - r, -(b - r), 270, [(a, -(b - r) + (b - r) * i / (nl // 2)) for i in range(nl // 2)]),
    ):
        pts += [(cx + r * math.cos(math.radians(a0 + 90 * i / nc)), cy + r * math.sin(math.radians(a0 + 90 * i / nc))) for i in range(nc)]
        pts += seg
    return pts


def corner_r(d: float, a: float, b: float, r: float) -> float:
    """corner radius of the inset ring: follows the offset near the edge, grows towards a stadium on the dome"""
    t = min(1.0, max(0.0, (d - 5.0) / 11.0))
    t = t * t * (3 - 2 * t)
    return (1 - t) * max(r - d, 0.35) + t * 0.97 * min(a - d, b - d)


def ring_mesh(name: str, profile: list[tuple[float, float]], cap_top: bool, cap_bottom: bool, sharp_top: bool = False,
              a: float = A, b: float = B, r: float = R) -> bpy.types.Object:
    """profile: (inset_mm, z_mm) from top to bottom. Builds bridged rings around the rounded-rectangle outline."""
    bm = bmesh.new()
    rings = []
    for d, z in profile:
        pts = rrect(a - d, b - d, corner_r(d, a, b, r))
        rings.append([bm.verts.new((x * MM, y * MM, z * MM)) for x, y in pts])
    n = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            try:
                bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            except ValueError:
                pass
    caps = []
    if cap_top:
        caps.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_bottom:
        caps.append(bm.faces.new(rings[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    for f in caps:
        f.smooth = False
        if sharp_top:
            for e in f.edges:
                e.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def rounded_box(name: str, sx: float, sy: float, sz: float, bevel: float, segments: int = 6) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz)) * MM
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    m = ob.modifiers.new("bevel", "BEVEL")
    m.width = bevel * MM
    m.segments = segments
    m.limit_method = "NONE"
    for p in me.polygons:
        p.use_smooth = True
    return ob


def cylinder(name: str, r: float, depth: float, verts: int = 64) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r * MM, radius2=r * MM, depth=depth * MM)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = len(p.vertices) == 4
    return ob


# ---------------------------------------------------------------- materials
def _sock(node, name: str, kind: str | None = None, out: bool = False):
    socks = node.outputs if out else node.inputs
    for s in socks:
        if s.name == name and (kind is None or s.type == kind) and s.enabled:
            return s
    for s in socks:
        if s.name == name and (kind is None or s.type == kind):
            return s
    raise KeyError(name)


def new_mat(name: str):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    return m, nt, bsdf


def plastic(name: str, color: str, rough: float, coat: float, metallic: float = 0.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = srgb(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = 0.04
    return m


def img(nt, path: Path, noncolor: bool = False):
    n = nt.nodes.new("ShaderNodeTexImage")
    im = bpy.data.images.load(str(path), check_existing=True)
    if noncolor:
        im.colorspace_settings.name = "Non-Color"
    n.image = im
    n.interpolation = "Cubic"
    n.extension = "CLIP"
    return n


def planar_uv(nt):
    """object-space planar projection matching the 57.1 x 113.5 mm textures"""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / (2 * A * MM), 1 / (2 * B * MM), 1)
    mp.inputs["Location"].default_value = (0.5, 0.5, 0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    return mp.outputs["Vector"], tc


def math_node(nt, op: str, a=None, b=None, clamp: bool = False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def mix_rgb(nt, fac, a, b):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    nt.links.new(fac, _sock(n, "Factor", "VALUE")) if not isinstance(fac, float) else setattr(_sock(n, "Factor", "VALUE"), "default_value", fac)
    for sock, v in ((_sock(n, "A", "RGBA"), a), (_sock(n, "B", "RGBA"), b)):
        if isinstance(v, tuple):
            sock.default_value = v
        else:
            nt.links.new(v, sock)
    return _sock(n, "Result", "RGBA", out=True)


def shell_material(front: str, cover: str):
    """Front housing colour above a y-dependent seam, back cover below; prints/holes/badge on the back."""
    col, rough, coat = COVERS[cover]
    fcol = "#0B0B0C" if front == "black" else "#E9E9E6"
    m, nt, b = new_mat(f"shell_{front}_{cover}")
    uv, tc = planar_uv(nt)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    # seam height: 4.3 mm on the long sides, 1.0 mm at the top/bottom ends (ports sit in the front housing there)
    ay = math_node(nt, "ABSOLUTE", sep.outputs["Y"])
    t = nt.nodes.new("ShaderNodeMapRange")
    t.interpolation_type = "SMOOTHSTEP"
    t.inputs["From Min"].default_value = 44 * MM
    t.inputs["From Max"].default_value = 53.5 * MM
    t.inputs["To Min"].default_value = 4.3 * MM
    t.inputs["To Max"].default_value = 1.0 * MM
    nt.links.new(ay, t.inputs["Value"])
    dz = math_node(nt, "SUBTRACT", sep.outputs["Z"], t.outputs["Result"])
    is_front = math_node(nt, "GREATER_THAN", dz, 0.0)
    groove = math_node(nt, "LESS_THAN", math_node(nt, "ABSOLUTE", dz), 0.09 * MM)
    # back-facing mask for prints
    nsep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Normal"], nsep.inputs["Vector"])
    backf = math_node(nt, "LESS_THAN", nsep.outputs["Z"], -0.35)
    holes = math_node(nt, "MULTIPLY", img(nt, TEX / "back_holes.png", True).outputs["Color"], backf)
    text = math_node(nt, "MULTIPLY", img(nt, TEX / "back_text.png", True).outputs["Color"], backf)
    badge = math_node(nt, "MULTIPLY", img(nt, TEX / "back_badge.png", True).outputs["Color"], backf)
    for n in nt.nodes:
        if n.type == "TEX_IMAGE":
            nt.links.new(uv, n.inputs["Vector"])
    c = mix_rgb(nt, is_front, srgb(col), srgb(fcol))
    c = mix_rgb(nt, text, c, srgb(PRINT[cover]))
    c = mix_rgb(nt, badge, c, srgb("#B4B8BE"))
    c = mix_rgb(nt, holes, c, srgb("#050505"))
    c = mix_rgb(nt, groove, c, srgb("#050505"))
    nt.links.new(c, b.inputs["Base Color"])
    rough_front = 0.3 if front == "black" else 0.28
    r_ = math_node(nt, "ADD", math_node(nt, "MULTIPLY", is_front, rough_front - rough), rough)
    r_ = math_node(nt, "ADD", r_, math_node(nt, "MULTIPLY", holes, 0.8))
    r_ = math_node(nt, "ADD", r_, math_node(nt, "MULTIPLY", badge, 0.3 - rough))
    nt.links.new(r_, b.inputs["Roughness"])
    nt.links.new(math_node(nt, "MULTIPLY", badge, 0.95), b.inputs["Metallic"])
    coat_ = math_node(nt, "ADD", math_node(nt, "MULTIPLY", is_front, 0.18 - coat), coat)
    coat_ = math_node(nt, "MULTIPLY", coat_, math_node(nt, "SUBTRACT", 1.0, math_node(nt, "ADD", holes, badge, clamp=True)))
    nt.links.new(coat_, b.inputs["Coat Weight"])
    b.inputs["Coat Roughness"].default_value = 0.05
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.12 * MM
    height = math_node(nt, "SUBTRACT", math_node(nt, "ADD", badge, math_node(nt, "MULTIPLY", groove, -0.6)), holes)
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def glass_material(front: str, screen: str, brightness: float):
    m, nt, b = new_mat(f"glass_{front}_{screen}")
    uv, _ = planar_uv(nt)
    base = img(nt, TEX / f"front_{front}.png")
    emi = img(nt, TEX / f"emit_{screen}.png")
    for n in (base, emi):
        nt.links.new(uv, n.inputs["Vector"])
    nt.links.new(base.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(emi.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = brightness
    b.inputs["Roughness"].default_value = 0.25
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.012
    b.inputs["Coat IOR"].default_value = 1.52
    return m


def emissive(name: str, color: str, strength: float):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Color"].default_value = srgb(color)
    b.inputs["Emission Strength"].default_value = strength
    return m


def assign(ob, mat) -> None:
    ob.data.materials.clear()
    ob.data.materials.append(mat)


# ---------------------------------------------------------------- phone
BODY_PROFILE = [(1.75, 6.05), (1.35, 6.2), (1.05, 6.12), (0.75, 5.8), (0.45, 5.2), (0.22, 4.45), (0.12, 3.6), (0.03, 2.8), (0.0, 2.0), (0.03, 1.3), (0.08, 0.7)]
for _a in (12, 24, 36, 48, 60, 72, 84, 90):
    BODY_PROFILE.append((0.08 + 5.5 * (1 - math.cos(math.radians(_a))), 0.7 - 5.5 * math.sin(math.radians(_a))))
for _s in (0.06, 0.14, 0.24, 0.36, 0.5, 0.64, 0.78, 0.9, 1.0):
    BODY_PROFILE.append((5.58 + (A - 1.0 - 5.58) * _s, -4.8 - 1.55 * math.sin(_s * math.pi / 2) ** 2))
GLASS_PROFILE = [(1.6, 5.4), (1.6, 6.12), (1.63, 6.28), (1.71, 6.34), (1.84, 6.35)]


def surface_z(body, x: float, y: float) -> float:
    """z (mm) of the back surface under (x, y), by ray cast from behind"""
    dg = bpy.context.evaluated_depsgraph_get()
    ok, loc, *_ = bpy.context.scene.ray_cast(dg, Vector((x * MM, y * MM, -0.05)), Vector((0, 0, 1)))
    return loc.z / MM if ok else -6.0


def build_phone(tag: str, front: str = "black", cover: str = "black", screen: str = "home", brightness: float = 1.6):
    root = bpy.data.objects.new(f"phone_{tag}", None)
    bpy.context.collection.objects.link(root)
    parts = []
    body = ring_mesh(f"body_{tag}", BODY_PROFILE, cap_top=True, cap_bottom=True)
    assign(body, shell_material(front, cover))
    parts.append(body)
    glass = ring_mesh(f"glass_{tag}", GLASS_PROFILE, cap_top=True, cap_bottom=True, sharp_top=True)
    assign(glass, glass_material(front, screen, brightness))
    parts.append(glass)
    # top edge: micro-USB and 3.5 mm jack as flush inserts (clean edges in macro shots), lock key
    port_mat = plastic("port_inner", "#030303", 0.95, 0.0)
    steel = plastic("usb_shell", "#9A9DA3", 0.3, 0.0, metallic=1.0)
    wall = B - 0.06
    usb = ring_mesh(f"usb_{tag}", [(0.0, 0.3), (0.0, -0.3)], True, True, a=3.5, b=1.1, r=1.0)
    usb.rotation_euler = (math.radians(-90), 0, 0)
    usb.location = (-13.45 * MM, (wall - 0.26) * MM, 2.0 * MM)
    assign(usb, steel)
    usb_in = ring_mesh(f"usbin_{tag}", [(0.0, 0.3), (0.0, -0.3)], True, True, a=3.18, b=0.8, r=0.75)
    usb_in.rotation_euler = (math.radians(-90), 0, 0)
    usb_in.location = (-13.45 * MM, (wall - 0.2) * MM, 2.0 * MM)
    assign(usb_in, port_mat)
    tongue = rounded_box(f"usbtongue_{tag}", 5.0, 0.2, 0.42, 0.08, 2)
    tongue.location = (-13.45 * MM, (wall + 0.09) * MM, 2.2 * MM)
    assign(tongue, plastic("usb_tongue", "#26282C", 0.5, 0.0))
    jring = cylinder(f"jackring_{tag}", 2.15, 0.6)
    jring.rotation_euler = (math.radians(90), 0, 0)
    jring.location = (0, (wall - 0.24) * MM, 2.0 * MM)
    assign(jring, plastic("jack_ring", "#1A1B1E", 0.35, 0.3, metallic=0.6))
    jack = cylinder(f"jack_{tag}", 1.75, 0.6)
    jack.rotation_euler = (math.radians(90), 0, 0)
    jack.location = (0, (wall - 0.2) * MM, 2.0 * MM)
    assign(jack, port_mat)
    parts += [usb, usb_in, tongue, jring, jack]
    key_mat = body.data.materials[0]
    lock = rounded_box(f"lock_{tag}", 7.2, 1.2, 2.3, 0.55, 6)
    lock.location = (13.45 * MM, (B - 0.3) * MM, 2.0 * MM)
    assign(lock, plastic("lock_key", "#0E0E10" if front == "black" else "#E6E6E3", 0.25, 0.5))
    parts.append(lock)
    # right side: volume (long) + camera key
    for name, yc, length in (("vol", 28.4, 18.9), ("cam", -31.5, 10.5)):
        k = rounded_box(f"{name}_{tag}", 1.2, length, 2.5, 0.55, 6)
        k.location = ((A + 0.12) * MM, yc * MM, 2.2 * MM)
        assign(k, key_mat)
        parts.append(k)
    # camera module on the back
    bpy.context.view_layer.update()
    cz = surface_z(body, 0, 39.35)
    mod_ob = ring_mesh(f"cammod_{tag}", [(0.0, 0.6), (0.0, -0.55), (0.12, -0.95), (0.35, -1.12), (0.7, -1.18)],
                       cap_top=True, cap_bottom=True, a=5.1, b=4.8, r=2.6)
    mod_ob.rotation_euler = (0, 0, 0)
    mod_ob.location = (0, 39.35 * MM, cz * MM)
    assign(mod_ob, plastic("cam_module", "#0A0A0B", 0.12, 1.0))
    ring = cylinder(f"camring_{tag}", 2.75, 0.3)
    ring.location = (0, 39.35 * MM, (cz - 1.1) * MM)
    assign(ring, plastic("cam_ring", "#3A3D44", 0.28, 0.0, metallic=1.0))
    lens = cylinder(f"lens_{tag}", 2.2, 0.3)
    lens.location = (0, 39.35 * MM, (cz - 1.16) * MM)
    lm = plastic("lens_glass", "#04060D", 0.05, 1.0)
    lm.node_tree.nodes["Principled BSDF"].inputs["Coat Roughness"].default_value = 0.0
    assign(lens, lm)
    parts += [mod_ob, ring, lens]
    for p in parts:
        p.parent = root
    return root


# ---------------------------------------------------------------- studio
def reset() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as e:  # CPU fallback
        log("GPU unavailable: {}", e)
    sc.cycles.use_denoising = True
    sc.cycles.use_adaptive_sampling = True
    sc.view_settings.view_transform = "Khronos PBR Neutral"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("black")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0, 0, 0, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    sc.world = world


def area(name: str, loc, target, size: tuple[float, float], energy: float, color: str = "#FFFFFF", roll: float = 0.0, glossy: bool = True):
    li = bpy.data.lights.new(name, "AREA")
    li.shape = "RECTANGLE"
    li.size, li.size_y = size
    li.energy = energy
    li.color = srgb(color)[:3]
    ob = bpy.data.objects.new(name, li)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    q = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
    if roll:
        from mathutils import Quaternion
        q = q @ Quaternion((0, 0, 1), math.radians(roll))
    ob.rotation_euler = q.to_euler()
    ob.visible_camera = False
    ob.visible_glossy = glossy
    return ob


def studio(rim: float = 1.0, key: float = 1.0, fill: float = 1.0, warm_rim: bool = False, key_glossy: bool = True, sheen: float = 0.0) -> None:
    """Black stage for an upright phone facing -Y: front-top softbox, two thin rim strips behind, top kicker, faint fill.
    key_glossy=False keeps the softbox out of the glass so the screen stays inky; sheen adds a soft gradient card in the reflection."""
    rc = "#FFE2C8" if warm_rim else "#E8F0FF"
    k = area("key", (0.0, -0.32, 0.42), (0, 0, 0.01), (0.5, 0.28), 26 * key)
    k.visible_glossy = key_glossy
    area("rimL", (-0.3, 0.16, 0.04), (0, 0, 0), (0.02, 0.6), 30 * rim, rc)
    area("rimR", (0.3, 0.16, 0.04), (0, 0, 0), (0.02, 0.6), 30 * rim, rc)
    area("top", (0.0, 0.18, 0.34), (0, 0, 0.05), (0.3, 0.06), 10 * rim, rc)
    f = area("fill", (0.0, -0.7, -0.05), (0, 0, 0), (0.7, 0.5), 1.6 * fill)
    f.visible_glossy = False
    if sheen:
        card = bpy.data.objects.new("sheen", bpy.data.meshes.new("sheen"))
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.25)
        bm.to_mesh(card.data)
        bm.free()
        bpy.context.collection.objects.link(card)
        card.location = (-0.22, -0.55, 0.3)
        card.rotation_euler = (Vector((0, 0, 0)) - Vector(card.location)).to_track_quat("Z", "Y").to_euler()
        m, nt, b = new_mat("sheen")
        b.inputs["Base Color"].default_value = (0, 0, 0, 1)
        grad = nt.nodes.new("ShaderNodeTexGradient")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(tc.outputs["Generated"], grad.inputs["Vector"])
        pw = math_node(nt, "POWER", grad.outputs["Fac"], 2.2)
        nt.links.new(math_node(nt, "MULTIPLY", pw, sheen), b.inputs["Emission Strength"])
        b.inputs["Emission Color"].default_value = (1, 1, 1, 1)
        assign(card, m)
        card.visible_camera = False
        card.visible_diffuse = False
        card.visible_shadow = False


def camera(loc, target, focal: float = 100, fstop: float | None = None, focus=None):
    cam = bpy.data.cameras.new("cam")
    cam.lens = focal
    cam.clip_start = 0.005
    ob = bpy.data.objects.new("cam", cam)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if fstop:
        cam.dof.use_dof = True
        cam.dof.aperture_fstop = fstop
        cam.dof.focus_distance = (Vector(focus or target) - Vector(loc)).length
    bpy.context.scene.camera = ob
    return ob


def render(name: str, w: int, h: int, samples: int, scale: float) -> None:
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = round(100 * scale)
    sc.cycles.samples = samples
    sc.render.filepath = str(OUT / f"{name}.png")
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    log("rendered {} {}x{} @{}% in {:.0f}s", name, w, h, round(100 * scale), time.time() - t0)


def place(root, loc=(0, 0, 0), rot_deg=(0, 0, 0)) -> None:
    root.location = loc
    root.rotation_euler = tuple(math.radians(a) for a in rot_deg)


# ---------------------------------------------------------------- shots
# convention: phone stands upright -> rotate X by 90 deg so the front (+Z local) faces -Y (towards camera at -Y)
UP = 90


def wpos(root, x: float, y: float, z: float) -> Vector:
    """world position of a point given in the phone's local mm coordinates"""
    bpy.context.view_layer.update()
    return root.matrix_world @ Vector((x * MM, y * MM, z * MM))


def shot_hero(samples, scale, front="black", cover="black", name="hero_black"):
    reset()
    p = build_phone("a", front, cover, "home")
    place(p, rot_deg=(UP, 0, -14))
    studio(key_glossy=False, sheen=1.2, rim=0.8)
    camera((0.0, -0.40, 0.0), (0, 0, -0.002), focal=85)
    render(name, 1600, 2000, samples, scale)


def shot_back(samples, scale, cover="fuchsia", front="black", name=None):
    reset()
    p = build_phone("a", front, cover, "off")
    place(p, rot_deg=(UP, 0, 180 + 16))
    studio(key=0.8, key_glossy=False, sheen=0.9, warm_rim=cover in ("fuchsia", "yellow"))
    camera((0.0, -0.40, 0.0), (0, 0, -0.002), focal=85)
    render(name or f"back_{cover}", 1600, 2000, samples, scale)


def shot_lineup(samples, scale):
    reset()
    order = ["black", "white", "fuchsia", "green", "yellow", "blue"]
    for i, c in enumerate(order):
        p = build_phone(str(i), "white" if c == "white" else "black", c, "off")
        k = i - 2.5
        place(p, loc=(k * 0.041, 0.006 * k * k, 0), rot_deg=(UP, 0, 180 + 22 - 3 * k))
    studio(rim=1.1, key=0.9, key_glossy=False, sheen=0.9)
    camera((0.0, -0.58, 0.035), (0, 0.02, 0.0), focal=70)
    render("lineup", 2400, 1350, samples, scale)


def shot_profile(samples, scale):
    reset()
    p = build_phone("a", "black", "black", "off")
    place(p, rot_deg=(UP, 0, 180 - 58))
    area("rimL", (-0.2, 0.38, 0.05), (0, 0, 0), (0.02, 0.6), 24, "#EEF3FF")
    area("rimR", (0.26, 0.3, 0.0), (0, 0, 0), (0.02, 0.6), 8, "#EEF3FF")
    area("top", (0.0, 0.1, 0.36), (0, 0, 0.04), (0.25, 0.05), 8)
    f = area("fill", (0.2, -0.5, 0.05), (0, 0, 0), (0.6, 0.6), 1.0)
    f.visible_glossy = False
    camera((0.0, -0.44, 0.012), (0.052, 0, 0.0), focal=70)
    render("profile", 2400, 1350, samples, scale)


def shot_duo(samples, scale):
    reset()
    a = build_phone("a", "black", "black", "home")
    place(a, loc=(-0.034, 0.0, 0), rot_deg=(UP, 0, 12))
    b = build_phone("b", "white", "fuchsia", "off")
    place(b, loc=(0.034, 0.012, 0), rot_deg=(UP, 0, 180 - 12))
    studio(rim=1.0, key=0.9, key_glossy=False, sheen=0.7)
    camera((0.0, -0.46, 0.01), (0, 0.004, 0), focal=70)
    render("duo", 2400, 1350, samples, scale)


def shot_ports(samples, scale):
    reset()
    p = build_phone("a", "black", "black", "off")
    place(p, rot_deg=(0, 180, 180))  # lying on its front, top edge towards the camera
    t = wpos(p, 0, B, 2.0)
    area("key", (-0.06, t.y - 0.16, 0.12), tuple(t), (0.3, 0.12), 7.0, glossy=False)
    area("front", (0.05, t.y - 0.3, 0.02), tuple(t), (0.4, 0.2), 1.5)
    area("rim", (0.0, t.y + 0.25, 0.03), tuple(t), (0.4, 0.012), 2.0, "#E8F0FF")
    area("side", (-0.2, t.y - 0.1, 0.06), tuple(t), (0.05, 0.2), 1.5)
    camera((0.004, t.y - 0.11, t.z + 0.0035), (t.x, t.y, t.z + 0.0003), focal=85, fstop=5.6)
    render("ports", 2400, 960, samples, scale)


def shot_keys(samples, scale):
    reset()
    p = build_phone("a", "black", "black", "home", brightness=1.2)
    place(p, rot_deg=(0, 0, 0))  # lying on its back, screen up
    t = wpos(p, 0, -45.3, 6.35)
    area("key", (0.0, t.y - 0.25, 0.3), tuple(t), (0.5, 0.2), 4, glossy=False)
    camera((0.0, t.y - 0.078, t.z + 0.117), tuple(t), focal=100, fstop=4.0)
    render("keys", 2400, 960, samples, scale)


def shot_camera(samples, scale):
    reset()
    p = build_phone("a", "black", "fuchsia", "off")
    place(p, rot_deg=(180, 0, 0))  # lying on its face, back up
    t = wpos(p, 0, 39.35, -7.3)
    area("key", (0.08, t.y - 0.2, 0.25), tuple(t), (0.3, 0.2), 2.2, "#FFF1E6", glossy=False)
    area("streak", (0.1, t.y + 0.12, 0.1), tuple(t), (0.005, 0.3), 1.0, roll=-25)
    area("rim", (-0.2, t.y + 0.15, 0.06), tuple(t), (0.02, 0.4), 7, "#FFD9C2")
    b = area("bounce", (0.15, t.y + 0.05, 0.05), tuple(t), (0.3, 0.3), 0.6, "#FF4D7A")
    b.visible_glossy = False
    camera((t.x + 0.03, t.y - 0.075, t.z + 0.05), tuple(t), focal=100, fstop=4.0)
    render("camera", 2400, 1350, samples, scale)


def shot_display(samples, scale):
    reset()
    p = build_phone("a", "black", "black", "home", brightness=1.9)
    place(p, loc=(0.02, 0, 0), rot_deg=(0, 0, -28))  # lying on its back, screen up
    t = wpos(p, 0, 0, 6.35)
    area("streak", (0.05, 0.26, 0.15), tuple(t), (0.004, 0.5), 0.35, roll=40)
    area("soft", (0.2, 0.1, 0.4), tuple(t), (0.4, 0.4), 5, glossy=False)
    area("rim", (0.3, 0.3, 0.02), tuple(t), (0.02, 0.5), 10, "#E8F0FF")
    camera((-0.05, -0.235, 0.165), (t.x - 0.004, t.y - 0.004, t.z), focal=70, fstop=9.0, focus=tuple(t))
    render("display", 2400, 1350, samples, scale)


def shot_nfc(samples, scale):
    reset()
    spk = cylinder("speaker", 32, 44, 96)
    spk.location = (0.03, 0, -0.03)
    fab, nt, b = new_mat("fabric")
    b.inputs["Base Color"].default_value = srgb("#0E0F11")
    b.inputs["Roughness"].default_value = 0.95
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1800
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    assign(spk, fab)
    top = cylinder("spk_top", 31.2, 1.0, 96)
    top.location = (0.03, 0, -0.03 + 0.0225)
    assign(top, plastic("spk_top", "#0E0E10", 0.3, 0.4))
    p = build_phone("a", "black", "black", "home", brightness=1.5)
    place(p, loc=(0.0, 0.0, 0.035), rot_deg=(UP - 58, 0, -18))
    for i, (r, st) in enumerate(((0.026, 5.0), (0.038, 2.6), (0.051, 1.1))):
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=False, radius=r, segments=160)
        me = bpy.data.meshes.new(f"ring{i}")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f"ring{i}", me)
        bpy.context.collection.objects.link(ob)
        ob.location = (0.03, 0, -0.03 + 0.0235)
        ob.modifiers.new("skin", "SKIN")
        for v in me.skin_vertices[0].data:
            v.radius = (0.00032, 0.00032)
        assign(ob, emissive(f"ring{i}", "#CFE4FF", st))
    studio(rim=0.7, key=0.6, key_glossy=False, sheen=0.25)
    camera((0.11, -0.44, 0.15), (0.022, 0, 0.018), focal=60)
    render("nfc", 2400, 1350, samples, scale)


SHOTS = {
    "hero_black": lambda s, k: shot_hero(s, k),
    "hero_white": lambda s, k: shot_hero(s, k, "white", "white", "hero_white"),
    "back_black": lambda s, k: shot_back(s, k, "black"),
    "back_white": lambda s, k: shot_back(s, k, "white", front="white"),
    "back_fuchsia": lambda s, k: shot_back(s, k, "fuchsia"),
    "back_green": lambda s, k: shot_back(s, k, "green"),
    "back_yellow": lambda s, k: shot_back(s, k, "yellow"),
    "back_blue": lambda s, k: shot_back(s, k, "blue"),
    "lineup": shot_lineup,
    "profile": shot_profile,
    "duo": shot_duo,
    "ports": shot_ports,
    "keys": shot_keys,
    "camera": shot_camera,
    "display": shot_display,
    "nfc": shot_nfc,
}

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    samples, scale = 160, 1.0
    if "--samples" in argv:
        i = argv.index("--samples")
        samples = int(argv[i + 1])
        del argv[i : i + 2]
    if "--scale" in argv:
        i = argv.index("--scale")
        scale = float(argv[i + 1])
        del argv[i : i + 2]
    for name in argv or list(SHOTS):
        log("shot {} samples={} scale={}", name, samples, scale)
        SHOTS[name](samples, scale)
