(function (root) {
  function cardFitSize(measureLines, start, min, step, maxLines) {
    var size = start;
    while (measureLines(size) > maxLines && size > min) {
      size = Math.max(min, size - step);
    }
    return size;
  }

  root.cardFitSize = cardFitSize;
})(typeof window !== "undefined" ? window : globalThis);
