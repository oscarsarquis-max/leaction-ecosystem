"""Publish Monitor Edge that keeps the login state cookie on API 401."""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path
import zipfile

REGION = "us-east-1"
FUNCTION = "spider-sandbox-monitor-oidc"
DIST = "E2E4ORTD4DHI1D"
SOURCE = Path(__file__).resolve().parents[1] / "modules" / "frontend" / "edge" / "index.js"


def aws(args: list[str]) -> bytes:
    return subprocess.check_output(["aws", *args, "--region", REGION, "--output", "json"])


def aws_json(args: list[str]) -> dict:
    raw = aws(args)
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return json.loads(raw.decode("utf-16"))
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("utf-16"))


def main() -> None:
    local = SOURCE.read_text(encoding="utf-8")
    if "[clearCookie(COOKIE_STATE)]" in local.split("function unauthorizedApi()")[1].split("function queryMap")[0]:
        raise SystemExit("local unauthorizedApi still clears state")
    fn = aws_json(["lambda", "get-function", "--function-name", FUNCTION])
    url = fn["Code"]["Location"]
    raw = subprocess.check_output(["curl.exe", "-sS", url])
    zin = zipfile.ZipFile(io.BytesIO(raw))
    names = zin.namelist()
    source_name = next(name for name in names if name.endswith("index.js") or name == "index.js")
    live = zin.read(source_name).decode("utf-8")
    nl = "\r\n" if "\r\n" in live else "\n"
    old = (
        f"function unauthorizedApi() {{{nl}"
        f"  return response({nl}"
        f"    401,{nl}"
        f"    null,{nl}"
        f"    [clearCookie(COOKIE_STATE)],{nl}"
    )
    new = (
        f"function unauthorizedApi() {{{nl}"
        f"  return response({nl}"
        f"    401,{nl}"
        f"    null,{nl}"
        f"    null,{nl}"
    )
    if old not in live:
        if "function unauthorizedApi()" in live and "[clearCookie(COOKIE_STATE)]" not in live.split("function unauthorizedApi()")[1].split("function ")[1]:
            print("edge_already_keeps_state")
            return
        raise SystemExit("unauthorizedApi block not found in live edge")
    text = live.replace(old, new, 1)
    out = Path.home() / "AppData" / "Local" / "Temp" / "prm009-inc001-edge-keep-state.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            data = text.encode("utf-8") if name == source_name else zin.read(name)
            zout.writestr(name, data)
    out.write_bytes(buf.getvalue())
    aws_json(["lambda", "update-function-code", "--function-name", FUNCTION, "--zip-file", f"fileb://{out}"])
    subprocess.check_call(["aws", "lambda", "wait", "function-updated", "--function-name", FUNCTION, "--region", REGION])
    published = aws_json(
        ["lambda", "publish-version", "--function-name", FUNCTION, "--description", "prm009-inc001-keep-state"]
    )
    version = published["Version"]
    new_arn = published["FunctionArn"]
    print(f"edge_version={version}")
    cfg = aws_json(["cloudfront", "get-distribution-config", "--id", DIST])
    etag = cfg["ETag"]
    dist = cfg["DistributionConfig"]

    def bump(assoc: dict) -> None:
        items = assoc.get("Items") or []
        for item in items:
            arn = item.get("LambdaFunctionARN") or ""
            if FUNCTION in arn:
                item["LambdaFunctionARN"] = new_arn

    bump(dist["DefaultCacheBehavior"].get("LambdaFunctionAssociations") or {})
    for behavior in (dist.get("CacheBehaviors") or {}).get("Items") or []:
        bump(behavior.get("LambdaFunctionAssociations") or {})
    path_cfg = Path.home() / "AppData" / "Local" / "Temp" / "prm009-inc001-cf-keep-state.json"
    path_cfg.write_text(json.dumps(dist), encoding="utf-8")
    subprocess.check_call(
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
            "us-east-1",
        ]
    )
    print("cloudfront_updated")
    out.unlink(missing_ok=True)
    path_cfg.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
