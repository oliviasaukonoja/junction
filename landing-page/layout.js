(() => {
  const style = document.createElement("style");
  style.textContent = `
    #site-header header{position:sticky;top:0;z-index:5;background:rgba(255,255,255,.95);border-bottom:1px solid var(--line);backdrop-filter:blur(6px)}
    #site-header .wrap{max-width:1080px;margin:0 auto;padding:0 24px}
    #site-header .bar{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:72px;flex-wrap:wrap;padding:12px 24px}
    #site-header .logo{font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:24px;color:var(--ink);text-decoration:none}
    #site-header .bar-r{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
    #site-header select{font:inherit;font-size:15px;min-height:44px;padding:0 12px;border:1px solid #C9D2E0;border-radius:10px;background:#fff;color:var(--ink)}
    #site-header .btn{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:0 22px;border-radius:12px;background:var(--blue);color:#fff;font-weight:700;font-size:16px;text-decoration:none;border:0;cursor:pointer;font-family:inherit}
    #site-header .btn:hover{background:var(--blue-d);color:#fff}
    #site-header .btn.sm{min-height:44px;padding:0 16px;font-size:15px}
    @media (max-width:780px){#site-header .wrap{padding:0 20px}#site-header .bar{padding:12px 20px;gap:12px}#site-header .bar-r{display:contents}#site-header .logo{order:1;flex:1;font-size:22px}#site-header select{order:2;padding:0 8px;font-size:14px}#site-header .btn.sm{display:none}}
  `;
  document.head.append(style);

  const languages = {
    fi: "Suomi", sv: "Svenska", en: "English", ru: "Русский",
    et: "Eesti", ar: "العربية", so: "Soomaali", uk: "Українська"
  };
  const labels = {
    fi: { join: "Liity jonotuslistalle", about: "Tietoa meistä", faq: "Usein kysytyt kysymykset", feedback: "Anna palautetta", privacy: "Tietosuojaseloste", decision: "Päättäjille" },
    sv: { join: "Anmäl dig till väntelistan", about: "Om oss", faq: "Vanliga frågor", feedback: "Ge respons", privacy: "Dataskyddsbeskrivning", decision: "För beslutsfattare" },
    en: { join: "Join the waitlist", about: "About us", faq: "Questions", feedback: "Give feedback", privacy: "Privacy notice", decision: "For decision-makers" },
    ru: { join: "В список ожидания", about: "О нас", faq: "Частые вопросы", feedback: "Оставить отзыв", privacy: "Политика конфиденциальности", decision: "Для руководителей" },
    et: { join: "Liitu ootenimekirjaga", about: "Meist", faq: "Korduma kippuvad küsimused", feedback: "Anna tagasisidet", privacy: "Privaatsusteade", decision: "Otsustajatele" },
    ar: { join: "انضم إلى قائمة الانتظار", about: "من نحن", faq: "أسئلة شائعة", feedback: "أرسل ملاحظاتك", privacy: "إشعار الخصوصية", decision: "لصناع القرار" },
    so: { join: "Ku biir liiska sugitaanka", about: "Nagu saabsan", faq: "Su'aalaha", feedback: "Na sii ra'yi", privacy: "Ogeysiiska asturnaanta", decision: "Go'aamiyeyaasha" },
    uk: { join: "До списку очікування", about: "Про нас", faq: "Поширені запитання", feedback: "Залишити відгук", privacy: "Повідомлення про конфіденційність", decision: "Для керівників" }
  };
  const supported = (document.body.dataset.languages || "fi,sv,en,ru,et,ar,so,uk").split(",");
  const current = () => document.getElementById("lang")?.value || document.documentElement.lang || "fi";
  const copy = () => labels[current()] || labels.fi;

  const header = document.getElementById("site-header");
  if (header) {
    header.innerHTML = `<header><div class="wrap bar"><a class="logo" href="/">Polku hoitoon</a><div class="bar-r"><label for="lang" class="hidden" id="langLbl">Language</label><select id="lang" aria-labelledby="langLbl">${supported.map((code) => `<option value="${code}">${languages[code]}</option>`).join("")}</select><a class="btn sm" href="/#join" data-layout="join"></a></div></div></header>`;
    header.querySelector("[data-layout=join]").textContent = copy().join;
  }

  function renderFooter() {
    const footer = document.getElementById("site-footer");
    if (!footer) return;
    const t = copy();
    footer.innerHTML = `<footer><div class="wrap"><nav aria-label="More information" style="display:flex;flex-wrap:wrap;gap:18px"><a href="/meista">${t.about}</a><a href="/ukk">${t.faq}</a><a href="/palaute">${t.feedback}</a><a href="/tietosuoja">${t.privacy}</a><a href="/keuhkodata">${t.decision}</a></nav><div style="margin-top:14px;font-size:15px"><b style="color:var(--ink)">Polku Labs</b> · Junction 2026 · <a href="mailto:info@polkuhoitoon.fi">info@polkuhoitoon.fi</a></div></div></footer>`;
    const note = document.getElementById("site-footer-note");
    if (note) footer.querySelector(".wrap").prepend(note);
  }

  function translate() {
    const t = copy();
    const join = document.querySelector("[data-layout=join]");
    if (join) join.textContent = t.join;
    renderFooter();
  }

  document.getElementById("lang")?.addEventListener("change", translate);
  document.addEventListener("DOMContentLoaded", translate);
})();
