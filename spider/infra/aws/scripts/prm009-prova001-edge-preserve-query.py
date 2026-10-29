"""Publish Monitor Edge that keeps q/execution on OIDC return. No secrets printed."""

from __future__ import annotations

import io
import json
import subprocess
import zipfile
from pathlib import Path

REGION = "us-east-1"
FUNCTION = "spider-sandbox-monitor-oidc"
DIST = "E2E4ORTD4DHI1D"

OLD_SAFE = '''function safeReturnTo(value) {
  if (!value) return "/";
  const raw = String(value);
  if (raw.charAt(0) !== "/" || raw.charAt(1) === "/") return "/";
  if (raw.indexOf("\\\\") !== -1 || raw.indexOf("://") !== -1) return "/";
  if (raw.indexOf("\\n") !== -1 || raw.indexOf("\\r") !== -1) return "/";
  return raw.split("?")[0].split("#")[0] || "/";
}'''

ALREADY_PUBLISHED = '''function safeReturnTo(value) {
  if (!value) return "/";
  const raw = String(value);
  if (raw.charAt(0) !== "/" || raw.charAt(1) === "/") return "/";
  if (raw.indexOf("\\\\") !== -1 || raw.indexOf("://") !== -1) return "/";
  if (raw.indexOf("\\n") !== -1 || raw.indexOf("\\r") !== -1) return "/";
  const cut = raw.split("#")[0];
  const qIdx = cut.indexOf("?");
  const path = (qIdx === -1 ? cut : cut.slice(0, qIdx)) || "/";
  if (path.indexOf("..") !== -1) return "/";
  if (qIdx === -1) return path;'''

NEW_SAFE = '''const RETURN_QUERY_KEYS = ["q", "execution"];
const RETURN_QUERY_VALUE = /^[A-Za-z0-9._:-]{1,128}$/;

function safeReturnTo(value) {
  if (!value) return "/";
  const raw = String(value);
  if (raw.charAt(0) !== "/" || raw.charAt(1) === "/") return "/";
  if (raw.indexOf("\\\\") !== -1 || raw.indexOf("\\n") !== -1 || raw.indexOf("\\r") !== -1) return "/";
  const cut = raw.split("#")[0];
  const qIdx = cut.indexOf("?");
  const path = (qIdx === -1 ? cut : cut.slice(0, qIdx)) || "/";
  if (path.indexOf("://") !== -1 || path.indexOf("..") !== -1) return "/";
  if (qIdx === -1) return path;
  const params = new URLSearchParams(cut.slice(qIdx + 1));
  const kept = new URLSearchParams();
  RETURN_QUERY_KEYS.forEach((key) => {
    if (!params.has(key)) return;
    const item = String(params.get(key) || "");
    if (RETURN_QUERY_VALUE.test(item)) kept.set(key, item);
  });
  const qs = kept.toString();
  return qs ? `${path}?${qs}` : path;
}

function requestReturnTo(request) {
  const uri = String((request && request.uri) || "/").split("?")[0] || "/";
  const qs = (request && request.querystring) || "";
  return qs ? `${uri}?${qs}` : uri;
}'''


def aws_json(args: list[str], region: str = REGION) -> dict:
    raw = subprocess.check_output(["aws", *args, "--region", region, "--output", "json"])
    text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8")
    return json.loads(text)


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n")


def main() -> int:
    fn = aws_json(["lambda", "get-function", "--function-name", FUNCTION])
    url = fn["Code"]["Location"]
    raw = subprocess.check_output(["curl.exe", "-sS", url])
    zin = zipfile.ZipFile(io.BytesIO(raw))
    names = zin.namelist()
    source_name = next(name for name in names if name.endswith("index.js") or name == "index.js")
    live = zin.read(source_name).decode("utf-8")
    text = normalize(live)
    if "function requestReturnTo(" in text and 'path.indexOf("://")' in text:
        print("edge_already_preserves_query")
        return 0
    old = normalize(OLD_SAFE)
    already = normalize(ALREADY_PUBLISHED)
    if old in text:
        text = text.replace(old, normalize(NEW_SAFE), 1)
    elif already in text:
        text = text.replace(
            '  if (raw.indexOf("\\\\") !== -1 || raw.indexOf("://") !== -1) return "/";\n'
            '  if (raw.indexOf("\\n") !== -1 || raw.indexOf("\\r") !== -1) return "/";\n'
            '  const cut = raw.split("#")[0];\n'
            '  const qIdx = cut.indexOf("?");\n'
            '  const path = (qIdx === -1 ? cut : cut.slice(0, qIdx)) || "/";\n'
            '  if (path.indexOf("..") !== -1) return "/";\n',
            '  if (raw.indexOf("\\\\") !== -1 || raw.indexOf("\\n") !== -1 || raw.indexOf("\\r") !== -1) return "/";\n'
            '  const cut = raw.split("#")[0];\n'
            '  const qIdx = cut.indexOf("?");\n'
            '  const path = (qIdx === -1 ? cut : cut.slice(0, qIdx)) || "/";\n'
            '  if (path.indexOf("://") !== -1 || path.indexOf("..") !== -1) return "/";\n',
            1,
        )
    else:
        raise SystemExit("safeReturnTo block not found in live edge")
    text = text.replace(
        "authorizeRedirect(request.uri)",
        "authorizeRedirect(requestReturnTo(request))",
    )
    if "requestReturnTo," not in text and "safeReturnTo," in text:
        text = text.replace("  safeReturnTo,\n", "  safeReturnTo,\n  requestReturnTo,\n", 1)
    out = Path.home() / "AppData" / "Local" / "Temp" / "prm009-prova001-edge.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            data = text.encode("utf-8") if name == source_name else zin.read(name)
            zout.writestr(name, data)
    out.write_bytes(buf.getvalue())
    aws_json(["lambda", "update-function-code", "--function-name", FUNCTION, "--zip-file", f"fileb://{out}"])
    subprocess.check_call(
        ["aws", "lambda", "wait", "function-updated", "--function-name", FUNCTION, "--region", REGION]
    )
    published = aws_json(
        ["lambda", "publish-version", "--function-name", FUNCTION, "--description", "prova001-preserve-q-execution"]
    )
    version = published["Version"]
    new_arn = published["FunctionArn"]
    print(f"edge_version={version}")
    cfg = aws_json(["cloudfront", "get-distribution-config", "--id", DIST])
    etag = cfg["ETag"]
    dist = cfg["DistributionConfig"]

    def bump(assoc: dict) -> None:
        for item in assoc.get("Items") or []:
            arn = item.get("LambdaFunctionARN") or ""
            if FUNCTION in arn:
                item["LambdaFunctionARN"] = new_arn

    bump(dist["DefaultCacheBehavior"].get("LambdaFunctionAssociations") or {})
    for behavior in (dist.get("CacheBehaviors") or {}).get("Items") or []:
        bump(behavior.get("LambdaFunctionAssociations") or {})
    path_cfg = Path.home() / "AppData" / "Local" / "Temp" / "prm009-prova001-cf.json"
    path_cfg.write_text(json.dumps(dist), encoding="utf-8")
    subprocess.check_output(
        [
            "aws",
            "cloudfront",
            "update-distribution",
            "--id",
            DIST,
            "--if-match",
            etag,
            "--distribution-config",
            f"file://{path_cfg}",
            "--region",
            REGION,
            "--query",
            "Distribution.Status",
            "--output",
            "text",
        ]
    )
    print("cloudfront_updated")
    out.unlink(missing_ok=True)
    path_cfg.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
