// Keuhkodata hero: Finland from the 308 municipalities (Statistics Finland outlines, simplified).
// Wellbeing services counties whose SMR is significantly above 1 rise in signal red, height = SMR - 1.
// Counties significantly below 1 are tinted calm blue and stay flat. Everything else is ink.
// Build: npx esbuild landing-page/src/hero3d.js --bundle --minify --format=esm --legal-comments=eof --outfile=landing-page/assets/hero3d.js
import {
  Scene, PerspectiveCamera, WebGLRenderer, Shape, ExtrudeGeometry, Mesh, MeshLambertMaterial,
  AmbientLight, DirectionalLight, Group, BufferGeometry, Float32BufferAttribute, LineLoop, LineBasicMaterial, Vector3, Color,
} from "three";

const C = { ink: 0x0f1a24, base: 0x1d2a36, baseLine: 0x34434f, worse: 0xd92d20, worseLine: 0xf3a59c, better: 0x2f6fb5, betterLine: 0x8db3dc };
const RISE_MS = 1500, DRIFT_MS = 5200, K = 320, BASE = 5;
const ease = (t) => {           // cubic-bezier(.2,.8,.2,1), solved numerically
  const cx = 0.6, bx = -0.3, ax = 0.7, cy = 2.4, by = -3, ay = 1.6;   // from P1(.2,.8) P2(.2,1)
  let x = t; for (let i = 0; i < 6; i++) { const f = ((ax * x + bx) * x + cx) * x - t, d = (3 * ax * x + 2 * bx) * x + cx; if (Math.abs(d) < 1e-6) break; x -= f / d; }
  return ((ay * x + by) * x + cy) * x;
};

export function mount(el, { data, areas, onLabels }) {
  const renderer = new WebGLRenderer({ antialias: true, alpha: false, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(C.ink, 1);
  el.prepend(renderer.domElement);
  renderer.domElement.setAttribute("aria-hidden", "true");

  const scene = new Scene();
  scene.add(new AmbientLight(0xffffff, 1.35));
  const sun = new DirectionalLight(0xffffff, 1.6); sun.position.set(-300, -500, 900); scene.add(sun);

  let maxX = 0, maxY = 0;
  for (const [, , rings] of data.m) for (const r of rings) for (let i = 0; i < r.length; i += 2) { maxX = Math.max(maxX, r[i]); maxY = Math.max(maxY, r[i + 1]); }
  const cx = maxX / 2, cy = maxY / 2;
  const map = new Group(); map.position.set(-cx, -cy, 0); scene.add(map);

  const mats = {
    base: new MeshLambertMaterial({ color: C.base }), worse: new MeshLambertMaterial({ color: C.worse }), better: new MeshLambertMaterial({ color: C.better }),
    baseLine: new LineBasicMaterial({ color: C.baseLine }), worseLine: new LineBasicMaterial({ color: C.worseLine }), betterLine: new LineBasicMaterial({ color: C.betterLine }),
  };
  const rising = [];                 // {mesh, target}
  const centroid = {};               // hva -> [sx, sy, n]
  for (const [, hva, rings] of data.m) {
    const a = areas[hva] || {}, kind = a.sig === "hi" ? "worse" : a.sig === "lo" ? "better" : "base";
    for (const r of rings) {
      const sh = new Shape(); sh.moveTo(r[0], r[1]);
      for (let i = 2; i < r.length; i += 2) sh.lineTo(r[i], r[i + 1]);
      const geo = new ExtrudeGeometry(sh, { depth: 1, bevelEnabled: false });
      const mesh = new Mesh(geo, mats[kind]);
      const pts = []; for (let i = 0; i < r.length; i += 2) pts.push(r[i], r[i + 1], 1.001);
      const lg = new BufferGeometry(); lg.setAttribute("position", new Float32BufferAttribute(pts, 3));
      mesh.add(new LineLoop(lg, mats[kind + "Line"]));
      const target = kind === "worse" ? BASE + (a.smr - 1) * K : BASE;
      mesh.scale.z = BASE; map.add(mesh);
      if (kind === "worse") {
        rising.push({ mesh, target });
        const c = centroid[hva] || (centroid[hva] = [0, 0, 0]);
        for (let i = 0; i < r.length; i += 2) { c[0] += r[i]; c[1] += r[i + 1]; c[2]++; }
      }
    }
  }
  const labelAnchors = Object.entries(centroid).map(([hva, c]) => ({ hva, v: new Vector3(c[0] / c[2] - cx, c[1] / c[2] - cy, 0), top: BASE + (areas[hva].smr - 1) * K }));

  const camera = new PerspectiveCamera(26, 1, 10, 8000);
  const target = new Vector3(0, -20, 30);
  const view = (az, el2, dist) => {             // az/el in degrees around the target
    const a = (az * Math.PI) / 180, e = (el2 * Math.PI) / 180;
    camera.position.set(target.x + dist * Math.cos(e) * Math.sin(a), target.y - dist * Math.cos(e) * Math.cos(a), target.z + dist * Math.sin(e));
    camera.up.set(0, 0, 1); camera.lookAt(target);
  };
  let w = 0, h = 0, dist = 2900;
  const resize = () => {
    const r = el.getBoundingClientRect(); w = Math.max(1, r.width); h = Math.max(1, r.height);
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    const tn = Math.tan((camera.fov * Math.PI) / 360);   // fit Finland (about 560 x 1150 km, foreshortened by the tilt)
    dist = Math.max((maxY * 0.86) / 2 / tn, (maxX * 1.15) / 2 / (tn * camera.aspect)) * 1.04;
  };

  const v = new Vector3();
  const labels = () => {
    if (!onLabels) return;
    onLabels(labelAnchors.map((L) => {
      v.copy(L.v); v.z = L.cur ?? BASE; v.project(camera);
      return { hva: L.hva, x: (v.x * 0.5 + 0.5) * 100, y: (-v.y * 0.5 + 0.5) * 100 };
    }));
  };

  let t = 0, last = 0, raf = 0, visible = true, done = false;   // t = animation time; pauses while off screen
  const frame = (now) => {
    t += last ? Math.min(64, now - last) : 0; last = now;
    const k = ease(Math.min(1, Math.max(0, (t - 250) / RISE_MS)));
    for (const r of rising) r.mesh.scale.z = BASE + (r.target - BASE) * k;
    for (const L of labelAnchors) L.cur = BASE + (L.top - BASE) * k;
    const d = ease(Math.min(1, t / DRIFT_MS));
    view(-24 + 16 * d, 58 - 8 * d, dist * (1.06 - 0.06 * d));
    renderer.render(scene, camera); labels();
    if (t < Math.max(DRIFT_MS, RISE_MS + 250)) { raf = visible ? requestAnimationFrame(frame) : 0; if (!raf) last = 0; } else { done = true; raf = 0; }
  };
  const still = () => { view(-8, 50, dist); renderer.render(scene, camera); labels(); };

  resize();
  new ResizeObserver(() => { resize(); if (done) still(); }).observe(el);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible && !done && !raf) { last = 0; raf = requestAnimationFrame(frame); } }).observe(el);
  raf = requestAnimationFrame(frame);
  return { still, renderer };
}
