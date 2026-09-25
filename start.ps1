<#
单窗口运行：后台Job跑NeteaseCloudMusicApi，前台跑QQ Bot
不弹出任何新窗口
#>
$botRoot = "D:\QQ"
$apiDir = Join-Path $botRoot "netease_api"
$botMain = Join-Path $botRoot "src\main.py"
$logDir = Join-Path $botRoot "src\logs"
$port = 3000

cls

# 清理3000端口监听进程
$lines = netstat -ano | findstr ":$port" | findstr "LISTENING"
if($lines){
    $childPid = ($lines -split '\s+')[-1]
    Write-Host "检测到端口$port被进程 $childpid 占用"
}

# 后台Job启动网易云API
Write-Host "后台启动 NeteaseCloudMusicApi (3000)"
Start-Job -Name ncmApi -ScriptBlock {
    param($apiWorkingDir)
    cd $apiWorkingDir
    npx NeteaseCloudMusicApi
} -ArgumentList $apiDir | Out-Null

# 给API一点启动时间
Start-Sleep 4

# 前台运行QQ Bot（当前窗口）
Write-Host "启动 QQ Bot"
& "$botRoot\Scripts\Activate.ps1"
python -u $botMain


# bot退出后，清理后台job
Write-Host "Bot已退出，停止后台NeteaseCloudMusicApi"
Stop-Job -Name ncmApi 2>$null
Remove-Job -Name ncmApi 2>$null