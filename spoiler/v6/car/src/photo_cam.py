"""Camera matching for the owner's photo (v6/brochure/photo/owner_car_original.png).
A Blender-style pinhole camera (lens mm, 36 mm sensor fitted to the width, lens shift in units of the width), a label
rasterizer for the car's parts (numba, from v6/src/zr.py) and photo overlays. No bpy: runs in plain Python."""
import sys, json, math, numpy as np, trimesh
sys.path.insert(0, 'v6/src'); sys.path.insert(0, 'v6/car/src')
from zr import _raster
from car_body import Z_F, Y_G, S_FA, S_RA, TRACK
DROP = 0.028                     # as blend_photo.py: body lowered on its wheels (m)
R_TYRE, W_TYRE = 323.0, 225.0
PHOTO = 'v6/brochure/photo/owner_car_original.png'
CAM_JSON = 'v6/car/data/photo_camera.json'

# the old wing, traced on the 510 x 392 photo: top edge (auto-traced against the sky), right end plate, underside
WING_TOP = [(139, 87), (142, 85), (151, 85), (154, 84), (160, 84), (163, 83), (169, 83), (172, 82), (175, 82), (178, 81),
            (181, 80), (184, 79), (187, 78), (193, 78), (196, 77), (205, 77), (208, 76), (232, 76), (235, 77), (247, 77),
            (250, 78), (268, 78), (271, 77), (280, 77), (283, 74.5), (286, 75.5), (289, 77.5), (292, 80), (295, 82.5), (298, 85),
            (301, 87.5), (304, 90), (307, 93), (308.5, 96)]     # end-plate edge traced ~2.5 px wide: its soft edge
WING_BOTTOM = [(307.5, 98), (301, 99.5), (295, 102), (288, 109), (280, 115), (270, 119), (260, 120), (210, 120),
               (200, 118), (190, 116), (180, 119), (170, 122), (165, 121), (160, 118), (152, 116.5), (149, 112.5),
               (146, 107.5), (143.5, 101.5), (141, 94)]
PILLAR_L = ((128.0, 127.0), (147.0, 105.0))    # left D-pillar edge against the sky, below the wing (extended upwards)

def poly_mask(pts, W, H, ss=4):
    """anti-aliased coverage (0-1) of a polygon given in pixel coordinates"""
    from PIL import Image, ImageDraw
    im = Image.new('L', (W * ss, H * ss), 0)
    ImageDraw.Draw(im).polygon([(x * ss, y * ss) for x, y in pts], fill=255)
    return np.asarray(im.resize((W, H), Image.BOX)).astype(float) / 255

def to_bl(V):                    # car mm (x, y-up, z-rear) -> blender m (X right, Y forward, Z up), ground at Z = 0
    V = np.asarray(V, float)
    return np.column_stack([V[:, 0], -V[:, 2], V[:, 1] - Y_G]) * 0.001

def wheel_centre(axle, side):
    s = S_FA if axle == 'front' else S_RA
    return np.array([side * (TRACK / 2 + 8.0), -(Z_F + s), R_TYRE - 7.0]) * 0.001

def tyre_mesh(c, n=96):
    m = trimesh.creation.cylinder(radius=R_TYRE * 0.001, height=W_TYRE * 0.001, sections=n)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])); m.apply_translation(c)
    return m

def load_parts():
    """the car as blend_photo.build_photo places it: {name: trimesh in blender metres}"""
    P = {}
    body = trimesh.load('v6/car/out/car_body_conf.ply', process=False)
    P['body'] = trimesh.Trimesh(to_bl(body.vertices) - [0, 0, DROP], body.faces, process=False)
    sp = trimesh.load('v6/out/E2.stl')
    P['spoiler'] = trimesh.Trimesh(to_bl(sp.vertices) - [0, 0, DROP], sp.faces, process=False)
    for k in ('mirrors', 'plates', 'handles'):
        m = trimesh.load(f'v6/car/out/{k}.stl'); P[k] = trimesh.Trimesh(to_bl(m.vertices) - [0, 0, DROP], m.faces, process=False)
    P['tyres'] = trimesh.util.concatenate([tyre_mesh(wheel_centre(a, s)) for a in ('front', 'rear') for s in (-1, 1)])
    try:                                               # the body split into glass and the rest (zones as blend_photo)
        g = np.load('v6/car/out/photo_comp/glass_faces.npy')
        P['glass'] = trimesh.Trimesh(P['body'].vertices, P['body'].faces[g], process=False)
        P['paint'] = trimesh.Trimesh(P['body'].vertices, P['body'].faces[~g], process=False)
    except FileNotFoundError: pass
    return P

class Cam:
    """loc (m), yaw/pitch/roll (deg): yaw = heading of the view direction from +Y towards +X, pitch up +, roll
    clockwise +; lens (mm) on a 36 mm wide sensor; shift_x/shift_y as Blender (fractions of the image width)"""
    def __init__(self, loc, yaw, pitch, roll=0.0, lens=55.0, shift_x=0.0, shift_y=0.0, W=510, H=392):
        self.loc = np.asarray(loc, float); self.yaw, self.pitch, self.roll = yaw, pitch, roll
        self.lens, self.shift_x, self.shift_y, self.W, self.H = lens, shift_x, shift_y, W, H
    @classmethod
    def look_at(cls, loc, tgt, **kw):
        d = np.asarray(tgt, float) - np.asarray(loc, float)
        yaw = math.degrees(math.atan2(d[0], d[1])); pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
        return cls(loc, yaw, pitch, **kw)
    def axes(self):
        y, p, r = map(math.radians, (self.yaw, self.pitch, self.roll))
        f = np.array([math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)])
        rt = np.array([math.cos(y), -math.sin(y), 0.0])            # right, level
        up = np.cross(rt, f)
        rt, up = rt * math.cos(r) - up * math.sin(r), up * math.cos(r) + rt * math.sin(r)   # roll clockwise
        return rt, up, f
    def project(self, X):
        rt, up, f = self.axes(); d = np.atleast_2d(X) - self.loc
        x, y, z = d @ rt, d @ up, d @ f
        s = self.lens / 36.0 * self.W
        u = self.W / 2 + s * x / z - self.shift_x * self.W
        v = self.H / 2 - s * y / z + self.shift_y * self.W
        return np.column_stack([u, v]), z
    def blender(self):
        """location, euler XYZ (rad) and lens/shift for a Blender camera object (sensor_width 36, fit AUTO)"""
        from scipy.spatial.transform import Rotation
        rt, up, f = self.axes()
        Rm = np.column_stack([rt, up, -f])                          # camera local X, Y, Z in world
        return dict(location=self.loc.tolist(), rotation_euler=Rotation.from_matrix(Rm).as_euler('xyz').tolist(),
                    lens=self.lens, sensor_width=36.0, shift_x=self.shift_x, shift_y=self.shift_y, W=self.W, H=self.H)
    def to_json(self, path=CAM_JSON, **extra):
        d = dict(loc=self.loc.tolist(), yaw=self.yaw, pitch=self.pitch, roll=self.roll, lens=self.lens,
                 shift_x=self.shift_x, shift_y=self.shift_y, W=self.W, H=self.H, blender=self.blender(), **extra)
        json.dump(d, open(path, 'w'), indent=1)
    @classmethod
    def from_json(cls, path=CAM_JSON, W=None, H=None):
        d = json.load(open(path))
        return cls(d['loc'], d['yaw'], d['pitch'], d['roll'], d['lens'], d['shift_x'], d['shift_y'], W or d['W'], H or d['H'])

BODY_PARTS = ('body', 'spoiler', 'mirrors', 'plates', 'handles', 'glass', 'paint')     # move with the body (ride height); tyres stay

def raster_labels(cam, parts, names, ss=1, dz_body=0.0):
    """label image (0 = background, i+1 = names[i]) and depth, at ss x the camera's resolution.
    dz_body: lower the body parts by this much (m) on the wheels"""
    W, H = cam.W * ss, cam.H * ss
    c2 = Cam(cam.loc, cam.yaw, cam.pitch, cam.roll, cam.lens, cam.shift_x, cam.shift_y, W, H)
    zb = np.full((H, W), np.inf); tid = np.full((H, W), -1, np.int64); b0 = np.zeros((H, W)); b1 = np.zeros((H, W))
    lab_of = []; off = 0
    for i, k in enumerate(names):
        m = parts[k]; V = m.vertices if (dz_body == 0.0 or k not in BODY_PARTS) else m.vertices - [0.0, 0.0, dz_body]
        uv, z = c2.project(V)
        _raster(uv[:, 0], uv[:, 1], z, np.asarray(m.faces, np.int64), W, H, zb, tid, b0, b1, off)
        lab_of.append(np.full(len(m.faces), i + 1)); off += len(m.faces)
    lab_of = np.concatenate(lab_of)
    lab = np.where(tid >= 0, lab_of[np.maximum(tid, 0)], 0)
    return lab, zb

def overlay(cam, parts, out, names=('body', 'spoiler', 'mirrors', 'plates', 'tyres'), pts=None, k=2, photo=PHOTO,
            colors=None, dz_body=0.0):
    """photo with the model's part outlines drawn over it (k x upscaled); pts: {name: ((u, v) photo, (u, v) model)}"""
    from PIL import Image, ImageDraw
    colors = colors or {'body': (255, 255, 0), 'spoiler': (255, 60, 60), 'mirrors': (0, 255, 0), 'plates': (0, 255, 255),
                        'tyres': (255, 0, 255), 'handles': (255, 160, 0)}
    lab, _ = raster_labels(cam, parts, list(names), ss=k, dz_body=dz_body)
    im = Image.open(photo).convert('RGB'); im = im.resize((im.width * k, im.height * k), Image.LANCZOS)
    A = np.asarray(im).copy()
    for i, nm in enumerate(names):
        m = lab == i + 1
        e = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
        A[e] = colors.get(nm, (255, 255, 255))
    im = Image.fromarray(A); d = ImageDraw.Draw(im)
    for nm, (pp, pm) in (pts or {}).items():
        x, y = pp[0] * k, pp[1] * k; d.ellipse([x - 4, y - 4, x + 4, y + 4], outline=(0, 255, 0), width=2)
        x2, y2 = pm[0] * k, pm[1] * k; d.line([(x - 0, y - 0), (x2, y2)], fill=(255, 0, 0), width=2)
        d.rectangle([x2 - 3, y2 - 3, x2 + 3, y2 + 3], outline=(255, 0, 0), width=2)
    im.save(out)
    return lab
