(function () {
  var button = document.getElementById("download-card");
  if (!button) return;

  function wrap(ctx, text, maxWidth) {
    var words = String(text || "").split(/\s+/).filter(Boolean);
    var lines = [];
    var line = "";
    words.forEach(function (word) {
      var trial = line ? line + " " + word : word;
      if (ctx.measureText(trial).width > maxWidth && line) {
        lines.push(line);
        line = word;
      } else {
        line = trial;
      }
    });
    if (line) lines.push(line);
    return lines;
  }

  function rounded(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  button.addEventListener("click", function () {
    var data = button.dataset;
    var senses = [];
    try {
      senses = JSON.parse(data.senses || "[]");
    } catch (err) {
      senses = [];
    }
    document.fonts.ready.then(function () {
      var canvas = document.createElement("canvas");
      canvas.width = 1080;
      canvas.height = 1350;
      var ctx = canvas.getContext("2d");
      ctx.fillStyle = "#0B3D2C";
      ctx.fillRect(0, 0, 1080, 1350);

      ctx.save();
      ctx.translate(740, 280);
      ctx.strokeStyle = "#F0A202";
      ctx.lineWidth = 8;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(40, 250);
      ctx.bezierCurveTo(40, 120, 150, 70, 280, 70);
      ctx.bezierCurveTo(420, 70, 520, 140, 520, 250);
      ctx.bezierCurveTo(520, 300, 480, 330, 430, 330);
      ctx.lineTo(130, 330);
      ctx.bezierCurveTo(80, 330, 40, 300, 40, 250);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(150, 150);
      ctx.quadraticCurveTo(180, 190, 190, 250);
      ctx.moveTo(270, 120);
      ctx.quadraticCurveTo(300, 180, 310, 270);
      ctx.moveTo(390, 150);
      ctx.quadraticCurveTo(410, 190, 420, 240);
      ctx.stroke();
      ctx.strokeStyle = "#C42F6A";
      ctx.beginPath();
      ctx.moveTo(140, 40);
      ctx.quadraticCurveTo(120, 10, 150, -10);
      ctx.moveTo(280, 20);
      ctx.quadraticCurveTo(260, -10, 290, -30);
      ctx.moveTo(420, 40);
      ctx.quadraticCurveTo(400, 10, 430, -10);
      ctx.stroke();
      ctx.restore();

      var logo = new Image();
      logo.onload = function () {
        ctx.drawImage(logo, 80, 72, 230, 230 * (logo.height / logo.width));
        paint();
      };
      logo.onerror = paint;
      logo.src = data.logo;

      function paint() {
        var chipX = 820;
        senses.forEach(function (sense) {
          ctx.font = "700 18px Syne";
          var label = String(sense.label || "").toUpperCase();
          var width = ctx.measureText(label).width + 44;
          chipX -= width;
          rounded(ctx, chipX, 86, width, 48, 24);
          ctx.fillStyle = sense.color || "#C42F6A";
          ctx.fill();
          ctx.fillStyle = sense.ink || "#ffffff";
          ctx.textBaseline = "middle";
          ctx.fillText(label, chipX + 22, 110);
          chipX -= 12;
        });

        ctx.textBaseline = "alphabetic";
        ctx.fillStyle = "#A6D84E";
        ctx.font = "48px 'Caveat Brush'";
        ctx.fillText(data.kicker || "", 80, 360);

        var size = 108;
        var lines = [];
        do {
          ctx.font = "800 " + size + "px Fraunces";
          lines = wrap(ctx, data.title || "", 820);
          if (lines.length > 4) size -= 6;
        } while (lines.length > 4 && size > 64);
        ctx.fillStyle = "#FFF8EC";
        var y = 470;
        lines.forEach(function (line) {
          ctx.fillText(line, 80, y);
          y += size * 0.96;
        });

        ctx.fillStyle = "#E4EFE5";
        ctx.font = "34px Literata";
        var summary = wrap(ctx, data.summary || "", 820);
        y += 24;
        summary.forEach(function (line) {
          ctx.fillText(line, 80, y);
          y += 50;
        });

        ctx.fillStyle = "#A6D84E";
        ctx.font = "700 18px Syne";
        ctx.fillText(data.cta || "", 80, 1180);
        ctx.fillStyle = "#FFF8EC";
        ctx.font = "26px Literata";
        ctx.fillText(data.site || "", 80, 1224);
        ctx.fillStyle = "#F0A202";
        ctx.font = "34px 'Caveat Brush'";
        var number = data.number || "";
        var numberWidth = ctx.measureText(number).width;
        ctx.fillText(number, 1000 - numberWidth, 1224);

        canvas.toBlob(function (blob) {
          if (!blob) return;
          var link = document.createElement("a");
          link.href = URL.createObjectURL(blob);
          link.download = "lepain-" + data.slug + "-" + data.lang + ".png";
          document.body.appendChild(link);
          link.click();
          link.remove();
          setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
        }, "image/png");
      }
    });
  });
})();
