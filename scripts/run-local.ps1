param(
  [string]$HostAddress = $(if ($env:HOST) { $env:HOST } else { "127.0.0.1" }),
  [int]$Port = $(if ($env:PORT) { [int]$env:PORT } else { 8080 })
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = "$root\src" + $(if ($env:PYTHONPATH) { ";$env:PYTHONPATH" } else { "" })

if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3 -m consensus_web --host $HostAddress --port $Port
} else {
  & python -m consensus_web --host $HostAddress --port $Port
}
