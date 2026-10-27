# 风电版镜像构建打包脚本 (需先安装 Docker Desktop 并启动)
# 用法: 前后端仓库位于同一父目录时, 在 reis-backend 目录下执行:
#   powershell -ExecutionPolicy Bypass -File build_wind_images.ps1
# 产出: docker-images/ 下的 4 个 tar.gz (拷贝到U盘传内网)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (-not $root) { $root = (Get-Location).Path }   # 直接右键运行时取当前目录

Write-Host "0/5 检查 Docker..." -ForegroundColor Cyan
docker version | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "Docker 未运行, 请先启动 Docker Desktop" -ForegroundColor Red; exit 1 }

Write-Host "0/5 检查前端仓库位置 (需与 reis-backend 同父目录)..." -ForegroundColor Cyan
$frontendDir = Join-Path (Split-Path $root -Parent) 'reis-frontend'
if (-not (Test-Path (Join-Path $frontendDir 'Dockerfile'))) {
    Write-Host "未找到 $frontendDir\Dockerfile, 请确认目录结构" -ForegroundColor Red; exit 1
}

Write-Host "1/5 构建镜像 (首次约10-20分钟, 需联网拉取基础镜像)..." -ForegroundColor Cyan
docker compose -f docker-compose-wind.yml build
if ($LASTEXITCODE -ne 0) { Write-Host "构建失败" -ForegroundColor Red; exit 1 }

Write-Host "2/5 创建输出目录..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force "$root\docker-images" | Out-Null
Set-Location "$root\docker-images"

Write-Host "3/5 导出镜像 tar..." -ForegroundColor Cyan
docker save fba_server_wind:latest -o fba_server_wind.tar
docker save fba_ui_wind:latest    -o fba_ui_wind.tar
docker save fba_celery_wind:latest -o fba_celery_wind.tar
docker save rabbitmq:3.13.7       -o rabbitmq.tar

Write-Host "4/5 压缩 (有7-Zip则gz压缩, 无则保留tar)..." -ForegroundColor Cyan
$sevenZip = @("$env:ProgramFiles\7-Zip\7z.exe", "D:\7Z\7-Zip\7z.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if ($sevenZip) {
    foreach ($n in 'fba_server_wind', 'fba_ui_wind', 'fba_celery_wind', 'rabbitmq') {
        & $sevenZip a -tgzip "$n.tar.gz" "$n.tar" | Out-Null
        Remove-Item "$n.tar"
    }
    Write-Host "已压缩为 .tar.gz"
} else {
    Write-Host "未找到7-Zip, 保留 .tar 原样(体积较大)" -ForegroundColor Yellow
}

Write-Host "5/5 完成! U盘需要拷贝的内容:" -ForegroundColor Green
Write-Host @"
$root\docker-images\            <- 全部 .tar.gz
$root\docker-compose-wind.yml   <- 编排文件
$root\deploy\backend\docker-compose\.env.server.wind  <- 环境配置
"@
Write-Host "服务器端操作见部署文档: 传到 /opt/packages/reis-wind/V1.0.0 后 docker load + compose up"
