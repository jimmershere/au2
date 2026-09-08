/* Appearance Unlimited — shared site JS */
(function () {
  "use strict";

  /* Mobile nav toggle */
  var toggle = document.querySelector(".nav-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      document.body.classList.toggle("nav-open");
    });
  }

  /* Scroll reveal */
  var revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && revealEls.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { threshold: 0.12 });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("in"); });
  }

  /* Before/After sliders */
  document.querySelectorAll(".ba-wrap").forEach(function (wrap) {
    var after = wrap.querySelector(".ba-after");
    var handle = wrap.querySelector(".ba-handle");
    if (!after || !handle) return;
    function setPos(clientX) {
      var r = wrap.getBoundingClientRect();
      var pct = Math.min(Math.max((clientX - r.left) / r.width, 0.05), 0.95) * 100;
      after.style.clipPath = "inset(0 0 0 " + pct + "%)";
      handle.style.left = pct + "%";
    }
    var dragging = false;
    function start(e) { dragging = true; move(e); }
    function move(e) {
      if (!dragging) return;
      var x = e.touches ? e.touches[0].clientX : e.clientX;
      setPos(x);
      e.preventDefault();
    }
    function end() { dragging = false; }
    handle.addEventListener("mousedown", start);
    wrap.addEventListener("mousemove", move);
    document.addEventListener("mouseup", end);
    handle.addEventListener("touchstart", start, { passive: false });
    wrap.addEventListener("touchmove", move, { passive: false });
    document.addEventListener("touchend", end);
  });

  /* Two-step Build Inquiry form */
  var form = document.getElementById("inquiry-form");
  if (form) {
    var step1 = document.getElementById("inq-step-1");
    var step2 = document.getElementById("inq-step-2");
    var typeInput = document.getElementById("project_type");
    var budgetField = document.getElementById("budget-field");
    var insuranceField = document.getElementById("insurance-field");
    var typeLabel = document.getElementById("selected-type-label");

    document.querySelectorAll(".type-choice .tc").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".type-choice .tc").forEach(function (b) { b.classList.remove("selected"); });
        btn.classList.add("selected");
        var val = btn.getAttribute("data-type");
        typeInput.value = val;
        if (typeLabel) typeLabel.textContent = btn.querySelector("h4").textContent;

        /* Budget required only for restoration / resto-mod builds */
        var isBuild = val === "restoration" || val === "restomod";
        if (budgetField) {
          budgetField.classList.toggle("hidden", false);
          var sel = budgetField.querySelector("select");
          if (sel) sel.required = isBuild;
          var req = budgetField.querySelector(".req");
          if (req) req.style.display = isBuild ? "inline" : "none";
        }
        if (insuranceField) insuranceField.classList.toggle("hidden", val !== "collision");

        step1.classList.add("hidden");
        step2.classList.remove("hidden");
        step2.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });

    var backBtn = document.getElementById("inq-back");
    if (backBtn) {
      backBtn.addEventListener("click", function (e) {
        e.preventDefault();
        step2.classList.add("hidden");
        step1.classList.remove("hidden");
        step1.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      /* Demo site: no backend wired yet. Swap for a POST to your form handler
         (Formspree, Netlify Forms, Basin, or a CRM webhook) at launch. */
      document.getElementById("inq-success").classList.remove("hidden");
      form.classList.add("hidden");
      document.getElementById("inq-success").scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }

  /* Logo image fallback: if assets/img/logo.png is missing, show text lockup */
  document.querySelectorAll("[data-logo-img]").forEach(function (img) {
    img.addEventListener("error", function () {
      img.classList.add("hidden");
      var fb = img.parentElement.querySelector("[data-logo-fallback]");
      if (fb) fb.classList.remove("hidden");
    });
  });

  /* Current year */
  document.querySelectorAll("[data-year]").forEach(function (el) {
    el.textContent = new Date().getFullYear();
  });
})();
