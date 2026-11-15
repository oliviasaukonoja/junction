// Keuhkodata insight tiles: small 3D bar charts that rise when they scroll into view and follow the pointer a little.
// Build: npx esbuild landing-page/src/bars3d.js --bundle --minify --format=esm --legal-comments=eof --outfile=landing-page/assets/bars3d.js
import { Scene, PerspectiveCamera, WebGLRenderer, Mesh, MeshStandardMaterial, HemisphereLight, DirectionalLight, Group, Vector3, PlaneGeometry, MeshBasicMaterial, SRGBColorSpace } from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";

const ease = (p) => 1 - Math.pow(1 - p, 3);

// bars: [{v, color, top, label, group}] ; groups get a gap between them
export function mount(el, { bars, max, H = 3.2 }) {
  const renderer = new WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.setClearColor(0xffffff, 0);
  el.prepend(renderer.domElement);
  renderer.domElement.setAttribute("aria-hidden", "true");

  const scene = new Scene();
  scene.add(new HemisphereLight(0xffffff, 0xdfe3e3, 2.0));
  const sun = new DirectionalLight(0xffffff, 1.5); sun.position.set(3, 6, 5); scene.add(sun);
  const camera = new PerspectiveCamera(30, 1, 0.1, 100);

  const W = 0.66, gap = 0.4, ggap = 0.5;
  const g = new Group(); scene.add(g);
  let x = 0, last = null;
  const items = bars.map((b) => {
    if (last !== null && b.group !== last) x += ggap;
    last = b.group;
    const h = Math.max(0.04, (b.v / max) * H);
    const geo = new RoundedBoxGeometry(W, 1, W, 3, 0.06);
    geo.translate(0, 0.5, 0);
    const m = new Mesh(geo, new MeshStandardMaterial({ color: b.color, roughness: 0.45, metalness: 0.05 }));
    m.position.x = x; m.scale.y = 0.001; g.add(m);
    const it = { b, m, h, x };
    x += W + gap;
    return it;
  });
  const width = x - gap;
  g.position.x = -width / 2;
  const floor = new Mesh(new PlaneGeometry(width + 1.2, 1.6), new MeshBasicMaterial({ color: 0xf1f3f3 }));
  floor.rotation.x = -Math.PI / 2; floor.position.y = -0.001; scene.add(floor);

  // labels: value above each bar, name under it
  const tops = items.map((it) => { const d = document.createElement("div"); d.className = "b3v"; d.textContent = it.b.top; el.appendChild(d); return d; });
  const names = items.map((it) => { const d = document.createElement("div"); d.className = "b3n"; d.textContent = it.b.label || ""; el.appendChild(d); return d; });
  const gl = {};             // group labels under the middle of each group
  items.forEach((it) => { if (!it.b.gname) return; const q = gl[it.b.group] || (gl[it.b.group] = { a: it.x, z: it.x, t: it.b.gname }); q.z = it.x; });
  const gEls = Object.values(gl).map((q) => { const d = document.createElement("div"); d.className = "b3g"; d.textContent = q.t; el.appendChild(d); return { q, d }; });

  let w = 1, h = 1;
  const fit = () => {
    const r = el.getBoundingClientRect(); w = Math.max(1, r.width); h = Math.max(1, r.height);
    renderer.setSize(w, h, false); camera.aspect = w / h;
    const tn = Math.tan((camera.fov * Math.PI) / 360);
    const dist = Math.max((width / 2 + 0.9) / (tn * camera.aspect), (H / 2 + 0.8) / tn) * 0.9;
    camera.position.set(0, H * 0.9, dist); camera.updateProjectionMatrix();
  };
  fit(); new ResizeObserver(() => { fit(); draw(); }).observe(el);

  const v = new Vector3();
  let k = 0, mx = 0, tx = 0, start = 0, raf = 0, seen = false;
  const draw = () => {
    g.rotation.y = -0.22 + mx * 0.16; floor.rotation.z = 0;
    camera.lookAt(0, H * 0.38, 0);
    renderer.render(scene, camera);
    items.forEach((it, i) => {
      v.set(it.x - width / 2, it.m.scale.y + 0.22, 0).applyAxisAngle(new Vector3(0, 1, 0), g.rotation.y); v.project(camera);
      tops[i].style.transform = `translate(${((v.x + 1) / 2) * w}px,${((1 - v.y) / 2) * h}px) translate(-50%,-100%)`;
      tops[i].style.opacity = Math.min(1, k * 1.4);
      v.set(it.x - width / 2, -0.05, 0.45).applyAxisAngle(new Vector3(0, 1, 0), g.rotation.y); v.project(camera);
      names[i].style.transform = `translate(${((v.x + 1) / 2) * w}px,${((1 - v.y) / 2) * h}px) translate(-50%,0)`;
    });
    gEls.forEach(({ q, d }) => {
      v.set((q.a + q.z) / 2 - width / 2, -0.05, 0.95).applyAxisAngle(new Vector3(0, 1, 0), g.rotation.y); v.project(camera);
      d.style.transform = `translate(${((v.x + 1) / 2) * w}px,${((1 - v.y) / 2) * h}px) translate(-50%,0)`;
    });
  };
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const frame = (now) => {
    if (!start) start = now;
    const p = Math.min(1, (now - start) / 1300);
    items.forEach((it, i) => { const q = ease(Math.max(0, Math.min(1, p * 1.25 - i * 0.07))); it.m.scale.y = it.h * q; });
    k = ease(p);
    mx += (tx - mx) * 0.08;
    draw();
    raf = p < 1 || Math.abs(tx - mx) > 0.002 ? requestAnimationFrame(frame) : 0;
  };
  const go = () => { if (!raf) raf = requestAnimationFrame(frame); };
  if (reduce) { items.forEach((it) => (it.m.scale.y = it.h)); k = 1; draw(); }
  new IntersectionObserver(([e]) => { if (e.isIntersecting && !seen && !reduce) { seen = true; start = 0; go(); } }, { threshold: 0.35 }).observe(el);
  el.addEventListener("pointermove", (e) => { if (reduce) return; const r = el.getBoundingClientRect(); tx = ((e.clientX - r.left) / r.width) * 2 - 1; if (seen) go(); });
  el.addEventListener("pointerleave", () => { tx = 0; if (seen && !reduce) go(); });
  return { draw };
}
