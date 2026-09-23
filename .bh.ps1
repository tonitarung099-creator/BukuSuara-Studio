param(
    [string]$HostName = '127.0.0.1',
    [int]$Port = 7860,
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'SilentlyContinue'
$deadline = (Get-Date).AddSeconds([Math]::Max(5, $TimeoutSeconds))
$url = "http://${HostName}:${Port}"

while ((Get-Date) -lt $deadline) {
    $client = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $task = $client.ConnectAsync($HostName, $Port)
        if ($task.Wait(500) -and $client.Connected) {
            $client.Dispose()
            Start-Process $url
            exit 0
        }
    }
    catch {
        # Server is not ready yet.
    }
    finally {
        if ($null -ne $client) {
            $client.Dispose()
        }
    }
    Start-Sleep -Milliseconds 500
}

Write-Error "BukuSuara Studio tidak membuka port ${HostName}:${Port} dalam ${TimeoutSeconds} detik."
exit 1
