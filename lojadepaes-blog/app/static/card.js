(function () {
  var button = document.getElementById("download-card");
  var sheet = document.getElementById("card-sheet");
  var scale = document.getElementById("card-scale");
  var fit = document.querySelector(".card-fit");
  if (!button || !sheet || !scale || !fit) return;

  function linesAt(el, size) {
    el.style.fontSize = size + "px";
    var lineHeight = parseFloat(window.getComputedStyle(el).lineHeight);
    var height = el.getBoundingClientRect().height;
    if (!lineHeight) return 1;
    return Math.max(1, Math.round(height / lineHeight));
  }

  function fitText(el) {
    if (!el) return;
    var size = window.cardFitSize(
      function (px) { return linesAt(el, px); },
      Number(el.dataset.start),
      Number(el.dataset.min),
      Number(el.dataset.step),
      Number(el.dataset.lines)
    );
    el.style.fontSize = size + "px";
  }

  function layout() {
    var ratio = Math.min(1, fit.clientWidth / 1080);
    scale.style.transform = "scale(" + ratio + ")";
    scale.style.height = Math.round(1350 * ratio) + "px";
  }

  function imageReady() {
    var img = sheet.querySelector(".photo img");
    if (!img) return Promise.resolve();
    if (img.complete && img.naturalWidth > 0) return Promise.resolve();
    return new Promise(function (resolve) {
      img.addEventListener("load", function () { resolve(); }, { once: true });
      img.addEventListener("error", function () { resolve(); }, { once: true });
    });
  }

  function prepare() {
    layout();
    fitText(sheet.querySelector(".title"));
    fitText(sheet.querySelector(".summary"));
    return imageReady();
  }

  window.addEventListener("resize", layout);

  document.fonts.ready.then(prepare);

  button.addEventListener("click", function () {
    document.fonts.ready.then(prepare).then(function () {
      return window.htmlToImage.toPng(sheet, {
        pixelRatio: 1,
        width: 1080,
        height: 1350,
        canvasWidth: 1080,
        canvasHeight: 1350,
      });
    }).then(function (dataUrl) {
      var link = document.createElement("a");
      link.href = dataUrl;
      link.download = (button.dataset.slug || "card") + "-" + (button.dataset.modelo || "tipografico") + ".png";
      link.click();
    });
  });
})();
