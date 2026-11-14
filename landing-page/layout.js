(() => {
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
