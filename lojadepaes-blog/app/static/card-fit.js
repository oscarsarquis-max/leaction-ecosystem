(function (root) {
  function cardFitSize(measureLines, start, min, step, maxLines) {
    var size = start;
    while (measureLines(size) > maxLines && size > min) {
      size = Math.max(min, size - step);
    }
    return size;
  }

  function cardFileName(slug, lang, modelo) {
    if (!slug || (lang !== "pt" && lang !== "en")) return "";
    if (modelo !== "tipografico" && modelo !== "foto") return "";
    return "lepain-" + slug + "-" + lang + "-" + modelo + ".png";
  }

  root.cardFitSize = cardFitSize;
  root.cardFileName = cardFileName;
})(typeof window !== "undefined" ? window : globalThis);
