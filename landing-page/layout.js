(() => {
  // Styles live in /site.css (linked by every page). This script renders the shared header and footer.
  document.documentElement.classList.add("js");
  const mark = '<svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true"><path d="M3 18c4 0 4-6 8-6s4-6 8-6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="19" cy="6" r="2.4" fill="#8CC3CA"/></svg>';

  const languages = {
    fi: "Suomi", sv: "Svenska", en: "English", ru: "Русский",
    et: "Eesti", ar: "العربية", so: "Soomaali", uk: "Українська"
  };
  const labels = {
    fi: { more: "Lisätietoa", join: "Liity", menu: "Valikko", about: "Tietoa meistä", faq: "Usein kysytyt kysymykset", feedback: "Anna palautetta", privacy: "Tietosuojaseloste", lungdata: "Keuhkodata", pilotmap: "Pilottikartta" },
    sv: { more: "Mer information", join: "Anmäl dig", menu: "Meny", about: "Om oss", faq: "Vanliga frågor", feedback: "Ge respons", privacy: "Dataskyddsbeskrivning", lungdata: "Lungdata", pilotmap: "Pilotkarta" },
    en: { more: "More information", join: "Join", menu: "Menu", about: "About us", faq: "Questions", feedback: "Give feedback", privacy: "Privacy notice", lungdata: "Lung data", pilotmap: "Pilot map" },
    ru: { more: "Дополнительно", join: "Записаться", menu: "Меню", about: "О нас", faq: "Частые вопросы", feedback: "Оставить отзыв", privacy: "Политика конфиденциальности", lungdata: "Данные о раке лёгких", pilotmap: "Пилотная карта" },
    et: { more: "Lisateave", join: "Liitu", menu: "Menüü", about: "Meist", faq: "Korduma kippuvad küsimused", feedback: "Anna tagasisidet", privacy: "Privaatsusteade", lungdata: "Kopsuvähi andmed", pilotmap: "Pilootkaart" },
    ar: { more: "مزيد من المعلومات", join: "انضم", menu: "القائمة", about: "من نحن", faq: "أسئلة شائعة", feedback: "أرسل ملاحظاتك", privacy: "إشعار الخصوصية", lungdata: "بيانات سرطان الرئة", pilotmap: "خريطة المشروع التجريبي" },
    so: { more: "Macluumaad dheeraad ah", join: "Ku biir", menu: "Liiska", about: "Nagu saabsan", faq: "Su'aalaha", feedback: "Na sii ra'yi", privacy: "Ogeysiiska asturnaanta", lungdata: "Xogta kansarka sambabka", pilotmap: "Khariidadda tijaabada" },
    uk: { more: "Більше інформації", join: "Записатися", menu: "Меню", about: "Про нас", faq: "Поширені запитання", feedback: "Залишити відгук", privacy: "Повідомлення про конфіденційність", lungdata: "Дані про рак легень", pilotmap: "Пілотна карта" }
  };
  const supported = (document.body.dataset.languages || "fi,sv,en,ru,et,ar,so,uk").split(",");
  const current = () => document.getElementById("lang")?.value || document.documentElement.lang || "fi";
  const copy = () => labels[current()] || labels.fi;
  const path = location.pathname.replace(/\/+$/, "") || "/";
  const here = (href) => (path === href ? ' aria-current="page"' : "");

  const header = document.getElementById("site-header");
  if (header) {
    header.innerHTML = `<header><div class="wrap bar"><a class="logo" href="/">${mark}<span>Polku hoitoon</span></a><button class="menu-btn" type="button" aria-expanded="false" aria-controls="site-menu"><span class="bars" aria-hidden="true"></span><span data-layout="menu"></span></button><div class="bar-r" id="site-menu"><nav class="site-nav" aria-label="Polku hoitoon"><a href="/keuhkodata" data-layout="lungdata"${here("/keuhkodata")}></a><a href="/kartta" data-layout="pilotmap"${here("/kartta")}></a></nav><a class="btn sm" href="/#join" data-layout="join"></a><label for="lang" class="lang-lbl" id="langLbl">Language</label><select id="lang" aria-labelledby="langLbl">${supported.map((code) => `<option value="${code}">${languages[code]}</option>`).join("")}</select></div></div></header>`;
    const bar = header.querySelector("header"), btn = header.querySelector(".menu-btn");
    const setOpen = (open) => { bar.classList.toggle("open", open); btn.setAttribute("aria-expanded", String(open)); };
    btn.addEventListener("click", () => setOpen(!bar.classList.contains("open")));
    header.querySelectorAll("#site-menu a").forEach((a) => a.addEventListener("click", () => setOpen(false)));
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && bar.classList.contains("open")) { setOpen(false); btn.focus(); } });
    document.addEventListener("click", (ev) => { if (bar.classList.contains("open") && !header.contains(ev.target)) setOpen(false); });
    labelHeader();
  }

  function labelHeader() {
    const t = copy();
    document.querySelectorAll("#site-header [data-layout]").forEach((el) => { el.textContent = t[el.dataset.layout]; });
  }

  function renderFooter() {
    const footer = document.getElementById("site-footer");
    if (!footer) return;
    const t = copy();
    footer.innerHTML = `<footer><div class="wrap"><nav aria-label="${t.more}"><a href="/keuhkodata">${t.lungdata}</a><a href="/kartta">${t.pilotmap}</a><a href="/ukk">${t.faq}</a><a href="/meista">${t.about}</a><a href="/palaute">${t.feedback}</a><a href="/tietosuoja">${t.privacy}</a></nav><div class="colophon"><span><b>Polku Labs</b> · Junction 2026</span><a href="mailto:info@polkuhoitoon.fi">info@polkuhoitoon.fi</a></div></div></footer>`;
    const note = document.getElementById("site-footer-note");
    if (note) footer.querySelector(".wrap").prepend(note);
    reveal();
  }

  // Sections marked .reveal fade in once (12 px rise). Content is visible by default; see site.css.
  function reveal() {
    const items = document.querySelectorAll(".reveal:not(.in)");
    if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) { items.forEach((el) => el.classList.add("in")); return; }
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { rootMargin: "0px 0px -8% 0px" });
    items.forEach((el) => io.observe(el));
  }

  function translate() {
    labelHeader();
    renderFooter();
  }

  document.getElementById("lang")?.addEventListener("change", translate);
  document.addEventListener("DOMContentLoaded", translate);
})();
