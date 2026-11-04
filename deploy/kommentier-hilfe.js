// Kommentiermodus: markiert beim Überfahren, meldet beim Anklicken an die Relay-App.
(function () {
  if (window.__relayKommentar) return; window.__relayKommentar = true;
  var rahmen = document.createElement("div");
  rahmen.style.cssText = "position:fixed;pointer-events:none;z-index:2147483647;border:2px solid #e8825a;background:rgba(232,130,90,.12);border-radius:3px;display:none";
  document.documentElement.appendChild(rahmen);
  function selektor(el) {
    var teile = [];
    while (el && el.nodeType === 1 && el !== document.body && teile.length < 6) {
      var s = el.tagName.toLowerCase();
      if (el.id) { teile.unshift(s + "#" + el.id); break; }
      var k = (el.className && typeof el.className === "string") ? el.className.trim().split(/\s+/).slice(0, 2).join(".") : "";
      if (k) s += "." + k;
      var p = el.parentElement;
      if (p) { var g = Array.prototype.filter.call(p.children, function (c) { return c.tagName === el.tagName; }); if (g.length > 1) s += ":nth-of-type(" + (g.indexOf(el) + 1) + ")"; }
      teile.unshift(s); el = p;
    }
    return teile.join(" > ");
  }
  function ziel(e) { var t = e.target; return t && t.nodeType === 1 && t !== rahmen ? t : null; }
  document.addEventListener("mouseover", function (e) {
    var t = ziel(e); if (!t || t === document.documentElement || t === document.body) { rahmen.style.display = "none"; return; }
    var r = t.getBoundingClientRect();
    rahmen.style.cssText += ";display:block;left:" + r.left + "px;top:" + r.top + "px;width:" + r.width + "px;height:" + r.height + "px";
  }, true);
  document.addEventListener("click", function (e) {
    var t = ziel(e); if (!t) return;
    e.preventDefault(); e.stopPropagation();
    var herkunft = (location.ancestorOrigins && location.ancestorOrigins[0]) || "*";
    var text = (t.innerText || t.alt || t.value || "").replace(/\s+/g, " ").trim().slice(0, 200);
    parent.postMessage({ typ: "relay-kommentar", seite: location.pathname, selektor: selektor(t), tag: t.tagName.toLowerCase(), text: text }, herkunft);
  }, true);
})();
