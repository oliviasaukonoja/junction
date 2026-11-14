(() => {
  const style = document.createElement("style");
  style.textContent = `
    #site-header header{position:sticky;top:0;z-index:5;background:rgba(255,255,255,.95);border-bottom:1px solid var(--line,#E3E8F0);backdrop-filter:blur(6px)}
    #site-header .wrap{max-width:1080px;margin:0 auto;padding:0 24px}
    #site-header .bar{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:72px;padding:12px 24px}
    #site-header .logo{font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:24px;color:var(--ink,#14213D);text-decoration:none;white-space:nowrap}
    #site-header .bar-r{display:flex;align-items:center;gap:12px}
    #site-header .site-nav{display:flex;align-items:center;gap:4px}
    #site-header .site-nav a{display:inline-flex;align-items:center;min-height:44px;padding:0 12px;border-radius:10px;color:var(--muted,#4A5872);font-weight:600;font-size:16px;text-decoration:none;white-space:nowrap}
    #site-header .site-nav a:hover{color:var(--ink,#14213D);background:#F2F5FA}
    #site-header .site-nav a[aria-current=page]{color:var(--blue-d,#123E91);background:#E8EFFC}
    #site-header select{font:inherit;font-size:15px;min-height:44px;padding:0 12px;border:1px solid #C9D2E0;border-radius:10px;background:#fff;color:var(--ink,#14213D)}
    #site-header .btn{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:0 22px;border-radius:12px;background:var(--blue,#1F5FD6);color:#fff;font-weight:700;font-size:16px;text-decoration:none;border:0;cursor:pointer;font-family:inherit;white-space:nowrap}
    #site-header .btn:hover{background:var(--blue-d,#123E91);color:#fff}
    #site-header .btn.sm{min-height:44px;padding:0 16px;font-size:15px}
    #site-header .menu-btn{display:none;align-items:center;gap:8px;min-height:44px;padding:0 14px;border:1px solid #C9D2E0;border-radius:10px;background:#fff;color:var(--ink,#14213D);font:inherit;font-size:15px;font-weight:600;cursor:pointer}
    #site-header .menu-btn .bars{display:inline-block;width:18px;height:2px;background:currentColor;box-shadow:0 -6px 0 currentColor,0 6px 0 currentColor}
    #site-header .lang-lbl{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
    @media (max-width:860px){
      #site-header .bar{flex-wrap:wrap;gap:8px;min-height:60px;padding:8px 16px}
      #site-header .logo{flex:1;font-size:22px}
      #site-header .menu-btn{display:inline-flex}
      #site-header .bar-r{display:none;flex-basis:100%;flex-direction:column;align-items:stretch;gap:8px;padding:4px 0 8px}
      #site-header header.open .bar-r{display:flex}
      #site-header .site-nav{flex-direction:column;align-items:stretch}
      #site-header .site-nav a{min-height:48px;font-size:17px}
      #site-header .btn.sm{min-height:48px;font-size:16px}
      #site-header select{width:100%;min-height:48px}
    }
  `;
  document.head.append(style);

  const languages = {
    fi: "Suomi", sv: "Svenska", en: "English", ru: "Русский",
    et: "Eesti", ar: "العربية", so: "Soomaali", uk: "Українська"
  };
  const labels = {
    fi: { join: "Liity", menu: "Valikko", about: "Tietoa meistä", faq: "Usein kysytyt kysymykset", feedback: "Anna palautetta", privacy: "Tietosuojaseloste", lungdata: "Keuhkodata", pilotmap: "Pilottikartta" },
    sv: { join: "Anmäl dig", menu: "Meny", about: "Om oss", faq: "Vanliga frågor", feedback: "Ge respons", privacy: "Dataskyddsbeskrivning", lungdata: "Lungdata", pilotmap: "Pilotkarta" },
    en: { join: "Join", menu: "Menu", about: "About us", faq: "Questions", feedback: "Give feedback", privacy: "Privacy notice", lungdata: "Lung data", pilotmap: "Pilot map" },
    ru: { join: "Записаться", menu: "Меню", about: "О нас", faq: "Частые вопросы", feedback: "Оставить отзыв", privacy: "Политика конфиденциальности", lungdata: "Данные о раке лёгких", pilotmap: "Пилотная карта" },
    et: { join: "Liitu", menu: "Menüü", about: "Meist", faq: "Korduma kippuvad küsimused", feedback: "Anna tagasisidet", privacy: "Privaatsusteade", lungdata: "Kopsuvähi andmed", pilotmap: "Pilootkaart" },
    ar: { join: "انضم", menu: "القائمة", about: "من نحن", faq: "أسئلة شائعة", feedback: "أرسل ملاحظاتك", privacy: "إشعار الخصوصية", lungdata: "بيانات سرطان الرئة", pilotmap: "خريطة المشروع التجريبي" },
    so: { join: "Ku biir", menu: "Liiska", about: "Nagu saabsan", faq: "Su'aalaha", feedback: "Na sii ra'yi", privacy: "Ogeysiiska asturnaanta", lungdata: "Xogta kansarka sambabka", pilotmap: "Khariidadda tijaabada" },
    uk: { join: "Записатися", menu: "Меню", about: "Про нас", faq: "Поширені запитання", feedback: "Залишити відгук", privacy: "Повідомлення про конфіденційність", lungdata: "Дані про рак легень", pilotmap: "Пілотна карта" }
  };
  const supported = (document.body.dataset.languages || "fi,sv,en,ru,et,ar,so,uk").split(",");
  const current = () => document.getElementById("lang")?.value || document.documentElement.lang || "fi";
  const copy = () => labels[current()] || labels.fi;
  const path = location.pathname.replace(/\/+$/, "") || "/";
  const here = (href) => (path === href ? ' aria-current="page"' : "");

  const header = document.getElementById("site-header");
  if (header) {
    header.innerHTML = `<header><div class="wrap bar"><a class="logo" href="/">Polku hoitoon</a><button class="menu-btn" type="button" aria-expanded="false" aria-controls="site-menu"><span class="bars" aria-hidden="true"></span><span data-layout="menu"></span></button><div class="bar-r" id="site-menu"><nav class="site-nav" aria-label="Polku hoitoon"><a href="/keuhkodata" data-layout="lungdata"${here("/keuhkodata")}></a><a href="/kartta" data-layout="pilotmap"${here("/kartta")}></a></nav><a class="btn sm" href="/#join" data-layout="join"></a><label for="lang" class="lang-lbl" id="langLbl">Language</label><select id="lang" aria-labelledby="langLbl">${supported.map((code) => `<option value="${code}">${languages[code]}</option>`).join("")}</select></div></div></header>`;
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
    footer.innerHTML = `<footer><div class="wrap"><nav aria-label="More information" style="display:flex;flex-wrap:wrap;gap:18px"><a href="/meista">${t.about}</a><a href="/ukk">${t.faq}</a><a href="/palaute">${t.feedback}</a><a href="/tietosuoja">${t.privacy}</a><a href="/keuhkodata">${t.lungdata}</a><a href="/kartta">${t.pilotmap}</a></nav><div style="margin-top:14px;font-size:15px"><b style="color:var(--ink)">Polku Labs</b> · Junction 2026 · <a href="mailto:info@polkuhoitoon.fi">info@polkuhoitoon.fi</a></div></div></footer>`;
    const note = document.getElementById("site-footer-note");
    if (note) footer.querySelector(".wrap").prepend(note);
  }

  function translate() {
    labelHeader();
    renderFooter();
  }

  document.getElementById("lang")?.addEventListener("change", translate);
  document.addEventListener("DOMContentLoaded", translate);
})();
