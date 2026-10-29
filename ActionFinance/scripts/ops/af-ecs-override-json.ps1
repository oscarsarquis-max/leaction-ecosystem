#Requires -Version 5.1
# JSON for ECS overrides. Non-ASCII is \uXXXX so Windows AWS CLI cannot
# misread UTF-8 file bytes as Windows-1252 (ã U+00E3 → Ã£).

function ConvertTo-AfEcsOverrideJson {
  param([Parameter(Mandatory = $true)][hashtable] $Overrides)
  $raw = $Overrides | ConvertTo-Json -Depth 8 -Compress
  $sb = New-Object System.Text.StringBuilder
  foreach ($ch in $raw.ToCharArray()) {
    $code = [int]$ch
    if ($code -ge 0x7F) {
      [void]$sb.AppendFormat('\u{0:x4}', $code)
    } else {
      [void]$sb.Append($ch)
    }
  }
  return $sb.ToString()
}

function Assert-AfEcsOverrideJsonPreservesText {
  param(
    [Parameter(Mandatory = $true)][string] $Text,
    [Parameter(Mandatory = $true)][int[]] $ExpectedCodepoints
  )
  $json = ConvertTo-AfEcsOverrideJson -Overrides @{
    containerOverrides = @(@{ name = "probe"; command = @("--company-name=$Text") })
  }
  foreach ($ch in $json.ToCharArray()) {
    if ([int]$ch -gt 127) {
      throw "Override JSON is not ASCII-safe; AWS CLI may reinterpret it as Windows-1252."
    }
  }
  $parsed = $json | ConvertFrom-Json
  $value = [string]$parsed.containerOverrides[0].command[0]
  $prefix = "--company-name="
  if (-not $value.StartsWith($prefix)) { throw "Unexpected override command." }
  $got = $value.Substring($prefix.Length)
  $codes = @($got.ToCharArray() | ForEach-Object { [int]$_ })
  foreach ($expected in $ExpectedCodepoints) {
    if ($codes -notcontains $expected) {
      throw ("Missing U+{0:X4} after JSON round-trip." -f $expected)
    }
  }
  if ($got.ToCharArray() | Where-Object { [int]$_ -eq 0x00C3 -and $got.Contains([char]0x00A3) }) {
    throw "Mojibake U+00C3 U+00A3 present after round-trip."
  }
}
