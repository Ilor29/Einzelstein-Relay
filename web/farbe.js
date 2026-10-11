/* Hell oder dunkel: Der LEIT//PULS hängt ?farbe=hell oder ?farbe=dunkel an die Adresse,
   wenn er die Relay einbettet (Roli 11.10.2026 „57. Ja“). Gemerkt wird es nur für diesen
   Reiter (sessionStorage), allein geöffnet bleibt die Relay dunkel. */
(function () {
  var f = new URLSearchParams(location.search).get("farbe");
  try {
    if (f === "hell" || f === "dunkel") sessionStorage.setItem("relay-farbe", f);
    else f = sessionStorage.getItem("relay-farbe");
  } catch (e) {}
  if (f === "hell" && window.parent !== window) {
    document.documentElement.classList.add("hell");
    document.querySelector('meta[name="theme-color"]').content = "#F5F6FA";
  }
})();
