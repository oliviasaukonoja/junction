// Home hero: the Polku hoitoon screening bus in 3D.
// Drives in on load, idles, and on hover / tap / "look inside" turns see-through to show the CT scanner inside.
// Build: npx esbuild landing-page/src/bus3d.js --bundle --minify --format=esm --legal-comments=eof --outfile=landing-page/assets/bus3d.js
import {
  Scene, PerspectiveCamera, WebGLRenderer, Group, Mesh, Shape, ExtrudeGeometry, BoxGeometry, CylinderGeometry, TorusGeometry,
  CapsuleGeometry, PlaneGeometry, CircleGeometry, MeshStandardMaterial, MeshBasicMaterial, HemisphereLight, DirectionalLight,
  CanvasTexture, Vector3, DoubleSide, SRGBColorSpace, EdgesGeometry, LineSegments, LineBasicMaterial,
} from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";

const COL = { teal: 0x2ba39a, tealD: 0x1d7c75, amber: 0xe39a2d, ink: 0x0f1a24, white: 0xffffff, grey: 0xdfe3e3, grey2: 0x9aa3a8, glass: 0x16323a };
const L = 6.2, H = 2.55, W = 2.3, Z = 0.36;             // bus length, height, width, ground clearance
const easeOut = (p) => 1 - Math.pow(1 - p, 3);
const easeInOut = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);

function mat(color, o = {}) { return new MeshStandardMaterial({ color, roughness: 0.55, metalness: 0.05, ...o }); }

function blobTexture() {                                  // soft contact shadow
  const c = document.createElement("canvas"); c.width = c.height = 128; const g = c.getContext("2d");
  const r = g.createRadialGradient(64, 64, 4, 64, 64, 64); r.addColorStop(0, "rgba(15,26,36,.32)"); r.addColorStop(1, "rgba(15,26,36,0)");
  g.fillStyle = r; g.fillRect(0, 0, 128, 128); const t = new CanvasTexture(c); t.colorSpace = SRGBColorSpace; return t;
}
function logoTexture() {                                  // the Polku path mark on the side
  const c = document.createElement("canvas"); c.width = 256; c.height = 128; const g = c.getContext("2d");
  g.strokeStyle = "#fff"; g.lineWidth = 10; g.lineCap = "round"; g.beginPath(); g.moveTo(20, 104); g.bezierCurveTo(70, 104, 70, 64, 120, 64); g.bezierCurveTo(170, 64, 170, 24, 220, 24); g.stroke();
  g.fillStyle = "#E39A2D"; g.beginPath(); g.arc(222, 24, 14, 0, Math.PI * 2); g.fill();
  const t = new CanvasTexture(c); t.colorSpace = SRGBColorSpace; return t;
}

export function mount(el, { rtl = false, labels = {}, onState } = {}) {
  const renderer = new WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.setClearColor(0xffffff, 0);
  el.prepend(renderer.domElement);
  renderer.domElement.setAttribute("aria-hidden", "true");

  const scene = new Scene();
  scene.add(new HemisphereLight(0xffffff, 0xdfe3e3, 1.9));
  const sun = new DirectionalLight(0xffffff, 1.6); sun.position.set(4, 8, 6); scene.add(sun);
  const fill = new DirectionalLight(0xffffff, 0.5); fill.position.set(-6, 3, -4); scene.add(fill);

  const camera = new PerspectiveCamera(28, 1, 0.1, 100);
  const target = new Vector3(0, 1.45, 0);

  // ---- ground: a long hairline road and a soft shadow that follows the bus
  const road = new Mesh(new PlaneGeometry(60, 0.04), new MeshBasicMaterial({ color: 0xcdd2d3 }));
  road.rotation.x = -Math.PI / 2; road.position.set(0, 0.002, W / 2 + 0.6); scene.add(road);
  const dashes = new Group(); scene.add(dashes);
  for (let i = -14; i <= 14; i++) { const d = new Mesh(new PlaneGeometry(0.7, 0.05), new MeshBasicMaterial({ color: 0xe3e6e6 })); d.rotation.x = -Math.PI / 2; d.position.set(i * 1.6, 0.002, -W / 2 - 0.6); dashes.add(d); }
  const shadow = new Mesh(new PlaneGeometry(L * 1.35, W * 2.1), new MeshBasicMaterial({ map: blobTexture(), transparent: true, depthWrite: false }));
  shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.004; scene.add(shadow);

  // ---- the bus
  const bus = new Group(); scene.add(bus);
  const chassis = new Group(); bus.add(chassis);          // everything that pitches / bobs (not the wheels)

  // shell: side profile extruded across the width; transparent-capable
  const shellMats = [];
  const fade = (m, min) => { m.transparent = true; m.userData.min = min; shellMats.push(m); return m; };
  const p = new Shape(), r = 0.32, x0 = -L / 2, x1 = L / 2, yb = Z, yt = Z + H;
  p.moveTo(x0 + r, yb); p.lineTo(x1 - 0.25, yb); p.quadraticCurveTo(x1, yb, x1, yb + 0.25); p.lineTo(x1, yb + 1.05);
  p.lineTo(x1 - 0.62, yt - 0.18); p.quadraticCurveTo(x1 - 0.72, yt, x1 - 0.95, yt); p.lineTo(x0 + r, yt); p.quadraticCurveTo(x0, yt, x0, yt - r);
  p.lineTo(x0, yb + r); p.quadraticCurveTo(x0, yb, x0 + r, yb);
  const shellGeo = new ExtrudeGeometry(p, { depth: W - 0.16, bevelEnabled: true, bevelThickness: 0.08, bevelSize: 0.08, bevelSegments: 4, curveSegments: 16 });
  shellGeo.translate(0, 0, -(W - 0.16) / 2);
  const shellMat = fade(mat(COL.teal, { roughness: 0.42 }), 0.06);
  const shell = new Mesh(shellGeo, shellMat); shell.renderOrder = 2; chassis.add(shell);
  // glass outline: appears as the shell fades, so the bus keeps its shape in x-ray mode
  const edgeMat = new LineBasicMaterial({ color: COL.tealD, transparent: true, opacity: 0 });
  const edges = new LineSegments(new EdgesGeometry(shellGeo, 25), edgeMat); edges.renderOrder = 5; chassis.add(edges);

  // lower skirt (darker) and the amber line
  const skirt = new Mesh(new RoundedBoxGeometry(L + 0.12, 0.42, W + 0.06, 3, 0.08), fade(mat(COL.tealD, { roughness: 0.5 }), 0.12));
  skirt.position.set(0, Z + 0.24, 0); skirt.renderOrder = 2; chassis.add(skirt);
  const stripe = new Mesh(new BoxGeometry(L + 0.14, 0.07, W + 0.08), fade(mat(COL.amber, { roughness: 0.4, emissive: COL.amber, emissiveIntensity: 0.15 }), 0.35));
  stripe.position.set(0, Z + 0.5, 0); stripe.renderOrder = 3; chassis.add(stripe);

  // windows (both sides), windscreen, door
  const glass = fade(mat(COL.glass, { roughness: 0.15, metalness: 0.3 }), 0.03);
  const side = (zs) => {
    [[-2.25, 1.0], [-1.05, 1.0]].forEach(([x, w]) => { const g = new Mesh(new RoundedBoxGeometry(w, 0.72, 0.04, 2, 0.06), glass); g.position.set(x, Z + 1.75, zs * (W / 2 + 0.005)); g.renderOrder = 3; chassis.add(g); });
    const door = new Mesh(new RoundedBoxGeometry(0.62, 1.7, 0.04, 2, 0.05), fade(mat(COL.tealD, { roughness: 0.5 }), 0.08));
    door.position.set(2.15, Z + 1.18, zs * (W / 2 + 0.006)); door.renderOrder = 3; chassis.add(door);
    const dw = new Mesh(new RoundedBoxGeometry(0.42, 0.6, 0.045, 2, 0.04), glass); dw.position.set(2.15, Z + 1.62, zs * (W / 2 + 0.01)); dw.renderOrder = 4; chassis.add(dw);
    // the white "scanner on board" panel, as on the 2D bus
    const panel = new Mesh(new RoundedBoxGeometry(1.5, 1.05, 0.04, 2, 0.06), fade(mat(COL.white, { roughness: 0.6 }), 0.0));
    panel.position.set(0.55, Z + 1.55, zs * (W / 2 + 0.005)); panel.renderOrder = 3; chassis.add(panel);
    const ring = new Mesh(new TorusGeometry(0.3, 0.07, 12, 40), fade(mat(COL.ink, { roughness: 0.4 }), 0.0));
    ring.position.set(0.32, Z + 1.58, zs * (W / 2 + 0.04)); ring.renderOrder = 4; chassis.add(ring);
    const bed = new Mesh(new BoxGeometry(0.85, 0.06, 0.02), fade(mat(COL.grey2), 0.0)); bed.position.set(0.72, Z + 1.5, zs * (W / 2 + 0.04)); bed.renderOrder = 4; chassis.add(bed);
    const logo = new Mesh(new PlaneGeometry(0.62, 0.31), fade(new MeshBasicMaterial({ map: logoTexture(), transparent: true, side: DoubleSide }), 0.0));
    logo.position.set(-2.45, Z + 0.95, zs * (W / 2 + 0.012)); if (zs < 0) logo.rotation.y = Math.PI; logo.renderOrder = 4; chassis.add(logo);
  };
  side(1); side(-1);
  // windscreen sits on the sloped front face, just proud of the bevel
  const sA = new Vector3(x1, yb + 1.05, 0), sB = new Vector3(x1 - 0.62, yt - 0.18, 0), sMid = sA.clone().add(sB).multiplyScalar(0.5);
  const sN = new Vector3(sA.y - sB.y, sB.x - sA.x, 0).normalize();
  const screen = new Mesh(new PlaneGeometry(W - 0.3, sA.distanceTo(sB) * 0.86), glass);
  screen.position.copy(sMid).addScaledVector(sN, 0.095); screen.lookAt(sMid.clone().addScaledVector(sN, 10)); screen.renderOrder = 3; chassis.add(screen);
  const lamp = (zs) => { const l = new Mesh(new RoundedBoxGeometry(0.06, 0.16, 0.34, 2, 0.03), mat(COL.amber, { emissive: COL.amber, emissiveIntensity: 0.6 })); l.position.set(x1 + 0.07, Z + 0.72, zs * (W / 2 - 0.3)); chassis.add(l); };
  lamp(1); lamp(-1);

  // ---- inside: floor, CT gantry, table and patient. Visible when the shell fades.
  const inside = new Group(); chassis.add(inside);
  const floor = new Mesh(new BoxGeometry(L - 0.4, 0.04, W - 0.25), mat(0xf5f6f6)); floor.position.set(0, Z + 0.52, 0); inside.add(floor);
  const gantry = new Group(); gantry.position.set(-0.55, Z + 1.42, 0); inside.add(gantry);
  const housing = new Mesh(new TorusGeometry(0.66, 0.26, 24, 64), mat(COL.white, { roughness: 0.35 })); housing.rotation.y = Math.PI / 2; housing.scale.z = 1.6; gantry.add(housing);
  const base = new Mesh(new RoundedBoxGeometry(0.55, 0.42, 1.25, 3, 0.08), mat(COL.white, { roughness: 0.35 })); base.position.set(0, -0.7, 0); gantry.add(base);
  const glow = new Mesh(new TorusGeometry(0.43, 0.025, 8, 64), new MeshBasicMaterial({ color: COL.teal })); glow.rotation.y = Math.PI / 2; gantry.add(glow);
  const spin = new Group(); spin.rotation.y = Math.PI / 2; gantry.add(spin);       // the rotating scan beam
  const beam = new Mesh(new PlaneGeometry(0.09, 0.86), new MeshBasicMaterial({ color: COL.amber, transparent: true, opacity: 0.95, side: DoubleSide })); spin.add(beam);
  const dot = new Mesh(new CircleGeometry(0.06, 16), new MeshBasicMaterial({ color: COL.amber, side: DoubleSide })); dot.position.y = 0.42; spin.add(dot);
  const table = new Group(); table.position.set(0.9, Z + 0.95, 0); inside.add(table);
  const top = new Mesh(new RoundedBoxGeometry(2.3, 0.08, 0.5, 2, 0.03), mat(COL.grey2, { roughness: 0.5 })); table.add(top);
  const leg = new Mesh(new BoxGeometry(0.5, 0.42, 0.34), mat(COL.white)); leg.position.set(0.5, -0.24, 0); inside.add(leg); leg.position.add(table.position);
  const patient = new Mesh(new CapsuleGeometry(0.17, 1.15, 6, 16), mat(0xf2d7c2, { roughness: 0.8 })); patient.rotation.z = Math.PI / 2; patient.position.set(0, 0.2, 0); table.add(patient);
  const head = new Mesh(new CapsuleGeometry(0.13, 0.04, 6, 16), mat(0xf2d7c2, { roughness: 0.8 })); head.position.set(-0.86, 0.22, 0); table.add(head);
  const gown = new Mesh(new CapsuleGeometry(0.185, 0.8, 6, 16), mat(COL.teal, { roughness: 0.8 })); gown.rotation.z = Math.PI / 2; gown.position.set(-0.05, 0.21, 0); table.add(gown);
  const desk = new Mesh(new RoundedBoxGeometry(0.7, 0.75, 0.5, 2, 0.05), mat(COL.white)); desk.position.set(2.3, Z + 0.92, -0.62); inside.add(desk);
  const monitor = new Mesh(new RoundedBoxGeometry(0.5, 0.34, 0.04, 2, 0.02), new MeshBasicMaterial({ color: COL.teal })); monitor.position.set(2.3, Z + 1.55, -0.62); monitor.rotation.y = -0.6; inside.add(monitor);

  // ---- wheels (outside the chassis so they don't bob)
  const wheels = [];
  const tyre = mat(COL.ink, { roughness: 0.9 }), hub = mat(0xcdd2d3, { roughness: 0.3, metalness: 0.4 });
  [[-L / 2 + 1.2, 1], [-L / 2 + 1.2, -1], [L / 2 - 1.25, 1], [L / 2 - 1.25, -1]].forEach(([x, zs]) => {
    const w = new Group(); w.position.set(x, 0.42, zs * (W / 2 - 0.12)); bus.add(w);
    const t = new Mesh(new CylinderGeometry(0.42, 0.42, 0.32, 28), tyre); t.rotation.x = Math.PI / 2; w.add(t);
    const h = new Mesh(new CylinderGeometry(0.2, 0.2, 0.34, 6), hub); h.rotation.x = Math.PI / 2; w.add(h);
    wheels.push(w);
  });
  if (rtl) bus.scale.x = -1;

  // ---- label that floats over the scanner when open
  const tag = document.createElement("div"); tag.className = "bus3d-tag"; tag.textContent = labels.ct || "Low-dose CT"; el.appendChild(tag);

  // ---- sizing
  let w = 1, h = 1;
  const fit = () => {
    const r = el.getBoundingClientRect(); w = Math.max(1, r.width); h = Math.max(1, r.height);
    renderer.setSize(w, h, false); camera.aspect = w / h;
    camera.fov = w / h < 1.3 ? 34 : 28; camera.updateProjectionMatrix();
  };
  fit(); const ro = new ResizeObserver(fit); ro.observe(el);

  // ---- interaction
  let want = 0, open = 0, peek = -1, hover = 0, pinned = 0;
  const set = () => { want = pinned || hover || peek > 0 ? 1 : 0; onState && onState(!!want); };
  el.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") { hover = 1; peek = 0; set(); } });
  el.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") { hover = 0; set(); } });
  el.addEventListener("click", () => { pinned = pinned ? 0 : 1; peek = 0; set(); });
  let px = 0, py = 0, mx = 0, my = 0;
  const onMove = (e) => { px = (e.clientX / window.innerWidth) * 2 - 1; py = (e.clientY / window.innerHeight) * 2 - 1; };
  window.addEventListener("pointermove", onMove, { passive: true });

  // ---- loop
  const DRIVE = 2100, START_X = -13;
  let t0 = 0, last = 0, raf = 0, visible = true, arrived = 0;
  const v = new Vector3();
  const frame = (now) => {
    if (!t0) t0 = now; const t = now - t0, dt = Math.min(0.05, (now - (last || now)) / 1000); last = now;
    // drive in, then brake with a small nose dip
    const pd = Math.min(1, t / DRIVE), x = START_X * (1 - easeOut(pd));
    bus.position.x = x; shadow.position.x = x;
    wheels.forEach((wh) => { wh.rotation.z = -(x - START_X) / 0.42 * (rtl ? -1 : 1); });
    if (pd >= 1 && !arrived) { arrived = t; if (peek < 0) peek = 1, set(); }
    const since = arrived ? (t - arrived) / 1000 : 0;
    const dip = arrived ? -0.035 * Math.exp(-since * 4.5) * Math.sin(since * 11) : 0.012 * Math.sin(t / 90) * (1 - pd);
    chassis.rotation.z = dip * (rtl ? -1 : 1);
    chassis.position.y = 0.012 * Math.sin(t / 420) + (1 - pd) * 0.01 * Math.sin(t / 37);
    if (peek > 0 && since > 2.9) { peek = 0; set(); }   // one automatic look inside, then back to the closed bus
    // open / close the shell
    open += (want - open) * Math.min(1, dt * 5);
    const o = easeInOut(Math.max(0, Math.min(1, open)));
    shellMats.forEach((m) => { m.opacity = 1 - (1 - m.userData.min) * o; m.depthWrite = o < 0.04; });
    edgeMat.opacity = 0.75 * o;
    const scanSpeed = 1.2 + 6 * o; spin.rotation.x += dt * scanSpeed;
    glow.material.color.setHex(o > 0.5 ? COL.amber : COL.teal);
    table.position.x = 0.9 - 0.9 * o * (0.5 + 0.5 * Math.sin(t / 1400));
    // camera: 3/4 front view, eases round a little when open; follows the pointer gently
    mx += (px - mx) * Math.min(1, dt * 3); my += (py - my) * Math.min(1, dt * 3);
    const az = 0.5 + 0.12 * o + mx * 0.12, el_ = 0.2 + 0.1 * o - my * 0.05, dist = 11.4 - 0.4 * o;
    camera.position.set(Math.sin(az) * dist * (rtl ? -1 : 1), target.y + Math.sin(el_) * dist, Math.cos(az) * dist);
    camera.lookAt(target);
    renderer.render(scene, camera);
    // label over the gantry
    gantry.getWorldPosition(v); v.y += 1.05; v.project(camera);
    tag.style.transform = `translate(${((v.x + 1) / 2) * w}px, ${((1 - v.y) / 2) * h}px) translate(-50%,-100%)`;
    tag.style.opacity = o > 0.6 ? (o - 0.6) / 0.4 : 0;
    raf = visible ? requestAnimationFrame(frame) : 0;
  };
  const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible && !raf) { last = 0; raf = requestAnimationFrame(frame); } }, { threshold: 0 });
  io.observe(el);
  raf = requestAnimationFrame(frame);

  return {
    toggle() { pinned = pinned ? 0 : 1; peek = 0; set(); return !!pinned; },
    setLabel(s) { tag.textContent = s; },
    destroy() { cancelAnimationFrame(raf); ro.disconnect(); io.disconnect(); window.removeEventListener("pointermove", onMove); renderer.dispose(); },
  };
}
