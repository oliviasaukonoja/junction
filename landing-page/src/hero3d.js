// Keuhkodata: Finland from the 308 municipalities (Statistics Finland outlines, simplified), as the region picker.
// Wellbeing services counties whose SMR is significantly above 1 rise in signal red, height = SMR - 1.
// Counties significantly below 1 are tinted blue and stay flat. Everything else is light grey.
// Hover lightens a region; click selects it (it lifts and gets an amber outline) and calls onPick(hva).
// Build: npx esbuild landing-page/src/hero3d.js --bundle --minify --format=esm --legal-comments=eof --outfile=landing-page/assets/hero3d.js
import {
  Scene, PerspectiveCamera, WebGLRenderer, Shape, ExtrudeGeometry, Mesh, MeshLambertMaterial,
  AmbientLight, DirectionalLight, Group, BufferGeometry, Float32BufferAttribute, LineLoop, LineBasicMaterial, Vector3, Vector2, Color, Raycaster,
} from "three";

const C = { bg: 0xffffff, base: 0xdfe3e3, baseHover: 0xc9cfd1, baseLine: 0xffffff, worse: 0xd92d20, worseHover: 0xe8574b, worseLine: 0xf6c9c4,
            better: 0x2f6fb5, betterHover: 0x5287c6, betterLine: 0xd3e2f3, sel: 0xe39a2d };
const RISE_MS = 1500, DRIFT_MS = 5200, K = 320, BASE = 5, LIFT = 46;
const ease = (t) => {           // cubic-bezier(.2,.8,.2,1), solved numerically
  const cx = 0.6, bx = -0.3, ax = 0.7, cy = 2.4, by = -3, ay = 1.6;   // from P1(.2,.8) P2(.2,1)
  let x = t; for (let i = 0; i < 6; i++) { const f = ((ax * x + bx) * x + cx) * x - t, d = (3 * ax * x + 2 * bx) * x + cx; if (Math.abs(d) < 1e-6) break; x -= f / d; }
  return ((ay * x + by) * x + cy) * x;
};

export function mount(el, { data, areas, onLabels, onPick, onHover, selected = null }) {
  const renderer = new WebGLRenderer({ antialias: true, alpha: false, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(C.bg, 1);
  el.prepend(renderer.domElement);
  renderer.domElement.setAttribute("aria-hidden", "true");

  const scene = new Scene();
  scene.add(new AmbientLight(0xffffff, 1.35));
  const sun = new DirectionalLight(0xffffff, 1.6); sun.position.set(-300, -500, 900); scene.add(sun);

  let maxX = 0, maxY = 0;
  for (const [, , rings] of data.m) for (const r of rings) for (let i = 0; i < r.length; i += 2) { maxX = Math.max(maxX, r[i]); maxY = Math.max(maxY, r[i + 1]); }
  const cx = maxX / 2, cy = maxY / 2;
  const map = new Group(); map.position.set(-cx, -cy, 0); scene.add(map);

  // one material pair per region, so hover and selection recolour a whole region
  const R = {};                     // hva -> {kind, mat, line, meshes, top, cur, c:[sx,sy,n]}
  const meshes = [];
  for (const [, hva, rings] of data.m) {
    const a = areas[hva] || {}, kind = a.sig === "hi" ? "worse" : a.sig === "lo" ? "better" : "base";
    const reg = R[hva] || (R[hva] = { kind, mat: new MeshLambertMaterial({ color: C[kind] }), line: new LineBasicMaterial({ color: C[kind + "Line"] }), meshes: [],
      top: kind === "worse" ? BASE + (a.smr - 1) * K : BASE, cur: BASE, c: [0, 0, 0] });
    for (const r of rings) {
      const sh = new Shape(); sh.moveTo(r[0], r[1]);
      for (let i = 2; i < r.length; i += 2) sh.lineTo(r[i], r[i + 1]);
      const mesh = new Mesh(new ExtrudeGeometry(sh, { depth: 1, bevelEnabled: false }), reg.mat);
      const pts = []; for (let i = 0; i < r.length; i += 2) { pts.push(r[i], r[i + 1], 1.001); reg.c[0] += r[i]; reg.c[1] += r[i + 1]; reg.c[2]++; }
      const lg = new BufferGeometry(); lg.setAttribute("position", new Float32BufferAttribute(pts, 3));
      mesh.add(new LineLoop(lg, reg.line));
      mesh.scale.z = BASE; mesh.userData.hva = hva; map.add(mesh); reg.meshes.push(mesh); meshes.push(mesh);
    }
  }
  const anchors = Object.entries(R).map(([hva, r]) => ({ hva, v: new Vector3(r.c[0] / r.c[2] - cx, r.c[1] / r.c[2] - cy, 0) }));

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
    onLabels(anchors.map((A) => {
      v.copy(A.v); v.z = R[A.hva].cur; v.project(camera);
      return { hva: A.hva, x: (v.x * 0.5 + 0.5) * 100, y: (-v.y * 0.5 + 0.5) * 100 };
    }));
  };

  // ---- state: hover + selection
  let hover = null, sel = selected;
  const paint = () => {
    for (const [hva, r] of Object.entries(R)) {
      r.mat.color.setHex(hva === hover ? C[r.kind + "Hover"] : C[r.kind]);
      r.line.color.setHex(hva === sel ? C.sel : C[r.kind + "Line"]);
    }
  };
  paint();

  // ---- loop: runs while anything moves, then sleeps
  let t = 0, last = 0, raf = 0, visible = true, intro = true;
  const frame = (now) => {
    const dt = last ? Math.min(64, now - last) : 0; last = now; t += dt;
    const k = ease(Math.min(1, Math.max(0, (t - 250) / RISE_MS)));
    let moving = false;
    for (const [hva, r] of Object.entries(R)) {
      const goal = BASE + (r.top - BASE) * k + (hva === sel ? LIFT * k : 0);
      const nxt = r.cur + (goal - r.cur) * Math.min(1, dt / 90);
      if (Math.abs(goal - nxt) > 0.05) moving = true;
      r.cur = Math.abs(goal - nxt) > 0.05 ? nxt : goal;
      for (const m of r.meshes) m.scale.z = r.cur;
    }
    const d = ease(Math.min(1, t / DRIFT_MS));
    view(-24 + 16 * d, 58 - 8 * d, dist * (1.06 - 0.06 * d));
    if (t >= Math.max(DRIFT_MS, RISE_MS + 250)) intro = false;
    renderer.render(scene, camera); labels();
    raf = (visible && (intro || moving)) ? requestAnimationFrame(frame) : 0;
    if (!raf) last = 0;
  };
  const kick = () => { if (!raf && visible) raf = requestAnimationFrame(frame); };

  // ---- picking
  const ray = new Raycaster(), ndc = new Vector2();
  const pick = (e) => {
    const r = el.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(meshes, false)[0];
    return hit ? hit.object.userData.hva : null;
  };
  let pend = 0;
  el.addEventListener("pointermove", (e) => {
    if (e.pointerType !== "mouse" || pend) return;
    pend = requestAnimationFrame(() => {
      pend = 0; const hv = pick(e);
      if (hv !== hover) { hover = hv; paint(); el.style.cursor = hv ? "pointer" : ""; onHover && onHover(hv); kick(); if (!raf) { renderer.render(scene, camera); labels(); } }
    });
  });
  el.addEventListener("pointerleave", () => { if (hover) { hover = null; paint(); el.style.cursor = ""; onHover && onHover(null); renderer.render(scene, camera); labels(); } });
  el.addEventListener("click", (e) => { const hv = pick(e); if (hv) { onPick && onPick(hv); } });

  resize();
  new ResizeObserver(() => { resize(); renderer.render(scene, camera); labels(); }).observe(el);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) kick(); }).observe(el);
  raf = requestAnimationFrame(frame);
  return {
    select(hva) { sel = hva; paint(); kick(); },
    renderer,
  };
}
