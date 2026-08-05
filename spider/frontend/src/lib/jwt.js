function b64UrlToUtf8(segment) {
  const padded = segment.replace(/-/g, "+").replace(/_/g, "/");
  const pad = padded.length % 4 === 0 ? "" : "=".repeat(4 - (padded.length % 4));
  try {
    return decodeURIComponent(
      atob(padded + pad)
        .split("")
        .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join(""),
    );
  } catch {
    return atob(padded + pad);
  }
}

export function decodeJwt(token) {
  if (!token || typeof token !== "string" || token.split(".").length < 2) {
    return { header: null, payload: null, signature: null, validStructure: false };
  }
  const [h, p, s = ""] = token.split(".");
  try {
    return {
      header: JSON.parse(b64UrlToUtf8(h)),
      payload: JSON.parse(b64UrlToUtf8(p)),
      signature: s,
      validStructure: Boolean(s),
      raw: { header: h, payload: p, signature: s },
    };
  } catch {
    return { header: null, payload: null, signature: s, validStructure: false };
  }
}
