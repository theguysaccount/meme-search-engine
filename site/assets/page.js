// Small behaviours for the static pages: copy and share buttons, and a graceful fallback when an
// image that lives on Imgflip's servers is gone or blocked.
const toast = document.getElementById("toast");

function say(message) {
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("on");
  clearTimeout(say.t);
  say.t = setTimeout(() => toast.classList.remove("on"), 1800);
}

function track(name) {
  try {
    if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: "event/" + name, title: name, event: true });
  } catch (e) { /* analytics must never break the page */ }
}

for (const img of document.querySelectorAll("img[data-remote]")) {
  const fail = () => {
    const frame = img.closest(".frame, .thumb");
    if (!frame || frame.classList.contains("none")) return;
    frame.classList.add("none");
    frame.textContent = frame.classList.contains("thumb") ? "Image on Imgflip" : "The image didn't load here. Use the Imgflip link below to see it.";
    frame.style.padding = "18px";
  };
  if (img.complete && !img.naturalWidth) fail();
  else img.addEventListener("error", fail);
}

for (const button of document.querySelectorAll("[data-copy]")) {
  button.addEventListener("click", async () => {
    const text = button.dataset.copy || location.href.split("?")[0];
    try {
      await navigator.clipboard.writeText(text);
      say(button.dataset.done || "Link copied");
    } catch (e) {
      window.prompt("Copy this:", text);
    }
    track(button.dataset.event || "copy_link");
  });
}

for (const button of document.querySelectorAll("[data-share]")) {
  if (!navigator.share) { button.hidden = true; continue; }
  button.addEventListener("click", () => {
    navigator.share({ title: document.title, url: location.href.split("?")[0] }).catch(() => {});
    track("share_page");
  });
}

for (const link of document.querySelectorAll("a[data-out]")) link.addEventListener("click", () => track(link.dataset.out));

if (new URLSearchParams(location.search).has("selftest")) {
  import("./selftest.js").then((m) => m.runPage());
}
