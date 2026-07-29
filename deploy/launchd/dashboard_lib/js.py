"""The dashboard's single inline script. Progressive enhancement only: with
JS disabled the page renders identically minus tooltips/sort/filter — no
content is carried by script. Self-containment is asserted by tests."""

SCRIPT = r"""
(function () {
  "use strict";
  // --- shared tooltip -------------------------------------------------
  var tip = document.createElement("div");
  tip.className = "jstip";
  document.body.appendChild(tip);
  function showTip(evt, text) {
    tip.textContent = text;
    tip.style.display = "block";
    tip.style.left = (evt.pageX + 12) + "px";
    tip.style.top = (evt.pageY - 10) + "px";
  }
  function hideTip() { tip.style.display = "none"; }
  document.querySelectorAll(".strip rect, .sspark rect, .tspark rect, .spark circle").forEach(function (el) {
    var t = el.querySelector("title");
    if (!t) return;
    var text = t.textContent;
    el.addEventListener("mousemove", function (e) { showTip(e, text); });
    el.addEventListener("mouseleave", hideTip);
  });
  // --- sortable tables ------------------------------------------------
  document.querySelectorAll("table thead th").forEach(function (th, _, all) {
    th.addEventListener("click", function () {
      var table = th.closest("table");
      var tbody = table.querySelector("tbody");
      if (!tbody) return;
      var idx = Array.prototype.indexOf.call(th.parentNode.children, th);
      var numeric = th.hasAttribute("data-num");
      var dir = th.dataset.dir === "asc" ? -1 : 1;
      th.dataset.dir = dir === 1 ? "asc" : "desc";
      var rows = Array.prototype.slice.call(tbody.rows);
      rows.sort(function (a, b) {
        var av = a.cells[idx] ? a.cells[idx].textContent.trim() : "";
        var bv = b.cells[idx] ? b.cells[idx].textContent.trim() : "";
        if (numeric) {
          var an = parseFloat(av.replace(/[^0-9+\-.]/g, ""));
          var bn = parseFloat(bv.replace(/[^0-9+\-.]/g, ""));
          if (isNaN(an)) return 1;
          if (isNaN(bn)) return -1;
          return (an - bn) * dir;
        }
        return av.localeCompare(bv) * dir;
      });
      rows.forEach(function (r) { tbody.appendChild(r); });
    });
  });
  // --- ticker filter --------------------------------------------------
  var box = document.getElementById("tickfilter");
  if (box) {
    box.addEventListener("input", function () {
      var q = box.value.trim().toUpperCase();
      document.querySelectorAll("#scorecard tbody tr").forEach(function (tr) {
        var sym = tr.cells[0] ? tr.cells[0].textContent.trim().toUpperCase() : "";
        tr.style.display = !q || sym.indexOf(q) !== -1 ? "" : "none";
      });
    });
  }
})();
"""
