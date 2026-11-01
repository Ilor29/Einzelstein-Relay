// Textliste der Oberfläche in Deutsch und Englisch.
// t("schluessel") schlägt in der gemerkten Sprache nach (localStorage "sprache",
// Vorgabe "de"). Fehlt ein Eintrag, kommt der deutsche Text, nie ein leerer Knopf.
// Texte mit Einsetzern nutzen {name}: t("vor_min", { n: 5 }).
(function () {
  "use strict";
  const TEXTE = {
    de: {
      einst_titel: "Einstellungen",
      sprache_marke: "Sprache",
      sprache_hinweis: "In welcher Sprache die Oberfläche erscheint. Die Wahl gilt für dieses Gerät.",
      stimme_marke: "Stimme zum Vorlesen",
      stimme_hinweis: "Antippen zum Anhören. Die gewählte Stimme liest dir künftig alles vor.",
      diktat_marke: "Diktat",
      diktat_hinweis: "Womit das Mikrofon zuhört. „Google“ schreibt beim Sprechen mit, kann aber aussetzen oder sich verhören. „Eigener Server“ nimmt auf, bis du nochmal tippst, und schreibt dann den ganzen Text auf, besonders bei Fachwörtern genauer. Das dauert ein paar Sekunden.",
      tempo_marke: "Sprechtempo",
      tempo_hinweis: "Wie schnell vorgelesen wird. Beim Wählen hörst du gleich eine Probe. Gilt für die eingebauten und die Google-Stimmen.",
      geraete_marke: "Angemeldete Geräte",
    },
    en: {
      einst_titel: "Settings",
      sprache_marke: "Language",
      sprache_hinweis: "The language of the interface. The choice applies to this device.",
      stimme_marke: "Reading voice",
      stimme_hinweis: "Tap to listen. The voice you pick reads everything aloud from now on.",
      diktat_marke: "Dictation",
      diktat_hinweis: "What the microphone listens with. “Google” types while you speak, but can drop out or mishear. “Own server” records until you tap again, then writes the whole text, more accurately for technical words. This takes a few seconds.",
      tempo_marke: "Speaking speed",
      tempo_hinweis: "How fast text is read aloud. You hear a sample when you pick one. Applies to the built-in and Google voices.",
      geraete_marke: "Signed-in devices",
    },
  };
  const SPRACHEN = ["de", "en"];

  function sprache() {
    try {
      const s = localStorage.getItem("sprache");
      return SPRACHEN.includes(s) ? s : "de";
    } catch { return "de"; }
  }

  function t(schluessel, werte) {
    let text = (TEXTE[sprache()] || {})[schluessel];
    if (text === undefined) text = TEXTE.de[schluessel];
    if (text === undefined) return schluessel;
    if (werte) text = text.replace(/\{(\w+)\}/g, (m, k) => (k in werte ? werte[k] : m));
    return text;
  }

  // Setzt alle Elemente mit data-t (Text) und data-t-attr="attribut:schluessel;…".
  function texteAnwenden(wurzel) {
    const w = wurzel || document;
    document.documentElement.lang = sprache();
    w.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });
    w.querySelectorAll("[data-t-attr]").forEach((el) => {
      for (const paar of el.dataset.tAttr.split(";")) {
        const [attr, key] = paar.split(":");
        if (attr && key) el.setAttribute(attr.trim(), t(key.trim()));
      }
    });
  }

  function spracheSetzen(s) {
    if (!SPRACHEN.includes(s)) return;
    try { localStorage.setItem("sprache", s); } catch { /* nur für diese Sitzung */ }
    texteAnwenden();
    document.dispatchEvent(new CustomEvent("sprache-geaendert", { detail: s }));
  }

  window.t = t;
  window.sprache = sprache;
  window.texteAnwenden = texteAnwenden;
  window.spracheSetzen = spracheSetzen;
  window.SPRACHEN = SPRACHEN;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => texteAnwenden());
  else texteAnwenden();
})();
