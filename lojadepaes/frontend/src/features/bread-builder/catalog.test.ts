import { describe, expect, it } from "vitest";
import { FORMS, MASSES, PHOTOS, previewPhoto } from "./catalog";

describe("fotos internal da vitrine", () => {
  it("mapeia as fotografias escolhidas da introdução, do painel, do mural e da biblioteca", () => {
    expect(decodeURIComponent(PHOTOS.levainBowl.src)).toContain("internal levain 2 bread");
    expect(decodeURIComponent(PHOTOS.panelHero.src)).toContain("internal 10 bread");
    expect(decodeURIComponent(PHOTOS.textureFlour.src)).toContain("internal texture 2 bread");
    expect(decodeURIComponent(PHOTOS.workBench.src)).toContain("internal work 1 bread");
    expect(decodeURIComponent(PHOTOS.morningLoaf.src)).toContain("internal 4 bread");
    expect(decodeURIComponent(PHOTOS.textureDark.src)).toContain("internal texture 1");
    expect(decodeURIComponent(PHOTOS.doughHands.src)).toContain("internal 8 bread");
    expect(decodeURIComponent(previewPhoto(0, 0, 0, false).src)).toContain("internal levain");
    expect(decodeURIComponent(previewPhoto(1, 0, 0, false).src)).toContain("internal ingredients");
    expect(decodeURIComponent(FORMS[0].photo.src)).toContain("internal texture 2");
    expect(decodeURIComponent(MASSES[0].photo.src)).toContain("internal 1 bread");
    expect(PHOTOS.levain.src).not.toContain("lojadepaeslogo");
  });
});
