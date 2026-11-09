(function () {
  var button = document.getElementById("download-card");
  var sheet = document.getElementById("card-sheet");
  var scale = document.getElementById("card-scale");
  var fit = document.querySelector(".card-fit");
  var error = document.getElementById("card-error");
  if (!button || !sheet || !scale || !fit) return;

  var faces = [
    ["Fraunces", "/static/fonts/Fraunces.woff2", "100 900", "normal"],
    ["Literata", "/static/fonts/Literata.woff2", "400 700", "normal"],
    ["'Caveat Brush'", "/static/fonts/CaveatBrush-Regular.woff2", "400", "normal"],
    ["Syne", "/static/fonts/Syne.woff2", "500 800", "normal"]
  ];

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

  function decodeImage(img) {
    if (!img || typeof img.decode !== "function") return Promise.resolve();
    return img.decode().catch(function () { return null; });
  }

  function imagesReady() {
    var logo = sheet.querySelector(".top img");
    var photo = sheet.querySelector(".photo img");
    return Promise.all([decodeImage(logo), decodeImage(photo)]);
  }

  function frames() {
    return new Promise(function (resolve) {
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () { resolve(); });
      });
    });
  }

  function missingPiece() {
    var logo = sheet.querySelector(".top img");
    var title = sheet.querySelector(".title");
    var foot = sheet.querySelector(".foot");
    if (!logo || !logo.getAttribute("src") || !logo.naturalWidth) return "logo";
    if (!title || !title.textContent.trim()) return "título";
    if (!foot || !foot.querySelector(".cta") || !foot.querySelector(".site") || !foot.querySelector(".number")) return "rodapé";
    return "";
  }

  function showError(detail) {
    if (!error) return;
    var text = button.dataset.lang === "en"
      ? "Could not generate the PNG."
      : "Não foi possível gerar o PNG.";
    error.textContent = detail ? text + " " + detail : text;
    error.hidden = false;
  }

  function toBase64(buffer) {
    var bytes = new Uint8Array(buffer);
    var binary = "";
    var size = 0x8000;
    for (var index = 0; index < bytes.length; index += size) {
      binary += String.fromCharCode.apply(null, bytes.subarray(index, index + size));
    }
    return window.btoa(binary);
  }

  function fontEmbedCSS() {
    var version = button.dataset.assetV || "";
    var suffix = version ? "?v=" + encodeURIComponent(version) : "";
    return Promise.all(faces.map(function (face) {
      return window.fetch(face[1] + suffix).then(function (res) {
        if (!res.ok) throw new Error(face[0]);
        return res.arrayBuffer().then(function (buffer) {
          return "@font-face{font-family:" + face[0] + ";src:url(data:font/woff2;base64," +
            toBase64(buffer) + ") format('woff2');font-weight:" + face[2] + ";font-style:" + face[3] + ";}";
        });
      });
    })).then(function (rules) { return rules.join(""); });
  }

  function prepare() {
    layout();
    fitText(sheet.querySelector(".title"));
    fitText(sheet.querySelector(".summary"));
    return document.fonts.ready.then(imagesReady).then(frames);
  }

  window.addEventListener("resize", layout);
  document.fonts.ready.then(function () { return prepare(); });

  button.addEventListener("click", function () {
    if (error) error.hidden = true;
    var name = window.cardFileName(button.dataset.slug, button.dataset.lang, button.dataset.modelo);
    if (!name || !window.htmlToImage) {
      showError();
      return;
    }
    var previous = scale.style.transform;
    prepare().then(function () {
      var gap = missingPiece();
      if (gap) throw new Error(gap);
      scale.style.transform = "none";
      return fontEmbedCSS();
    }).then(function (css) {
      return window.htmlToImage.toPng(sheet, {
        pixelRatio: 1,
        width: 1080,
        height: 1350,
        canvasWidth: 1080,
        canvasHeight: 1350,
        cacheBust: true,
        fontEmbedCSS: css,
      });
    }).then(function (dataUrl) {
      var link = document.createElement("a");
      link.href = dataUrl;
      link.download = name;
      link.click();
    }).catch(function (err) {
      showError(err && err.message ? err.message : "");
    }).then(function () {
      scale.style.transform = previous;
      layout();
    });
  });
})();
