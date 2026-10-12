<#
================================================================
  电商小二 · 全栈一键启动脚本（Windows / PowerShell）

  做四件事：
    1. 环境自检（Docker 是否运行、.env 是否存在）
    2. 构建镜像（首次较慢，之后走缓存）
    3. 后台启动全部容器，并等待服务真正就绪
    4. 自动弹出浏览器打开 http://localhost:8080

  用法：
    powershell -ExecutionPolicy Bypass -File start.ps1
    powershell -ExecutionPolicy Bypass -File start.ps1 -NoBrowser
================================================================
#>
[CmdletBinding()]
param(
    # 启动后不自动打开浏览器
    [switch]$NoBrowser,
    # 等待服务就绪的最长秒数（首次构建可能需要几分钟）
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = 'Continue'
# 抑制 Invoke-WebRequest 进度条（既避免刷屏，也显著加快请求）
$ProgressPreference = 'SilentlyContinue'

# ---------- 输出小工具 ----------
function Write-Title($t) { Write-Host ""; Write-Host "===== $t =====" -ForegroundColor Magenta }
function Write-Step($m)  { Write-Host "  [*] $m" -ForegroundColor Cyan }
function Write-Ok($m)    { Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn($m)  { Write-Host "  [!] $m" -ForegroundColor Yellow }
function Write-Err($m)   { Write-Host "  [X] $m" -ForegroundColor Red }

# ---------- 定位到脚本所在目录（项目根） ----------
$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -LiteralPath $Root

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Magenta
Write-Host "        电商小二 · Docker 一键启动全栈服务" -ForegroundColor Magenta
Write-Host "==========================================================" -ForegroundColor Magenta

# ==========================================================
# 1. 环境自检
# ==========================================================
Write-Title "1/4 环境自检"

# 1.1 docker 命令
$dockerCmd = $null
foreach ($cand in @('docker')) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) { $dockerCmd = $cand; break }
}
if (-not $dockerCmd) {
    Write-Err "未找到 docker 命令。请先安装并启动 Docker Desktop。"
    exit 1
}
Write-Ok "docker 命令可用"

# 1.2 docker daemon
$null = docker info --format '{{.ServerVersion}}' 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker 守护进程未运行。请先启动 Docker Desktop，等它变为 Running 后再试。"
    exit 1
}
$dockerVer = (docker version --format '{{.Server.Version}}' 2>$null)
Write-Ok "Docker 守护进程运行中（Server $dockerVer）"

# 1.3 compose 子命令
docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Err "未找到 docker compose 子命令，请升级 Docker Desktop（需 v2.0+）。"
    exit 1
}
Write-Ok "docker compose 可用"

# 1.4 .env 配置（LLM 密钥等，由 compose 插值注入容器）
$envFile = Join-Path $Root '.env'
if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Err "缺少项目根目录的 .env 文件（存放 LLM_API_KEY 等配置），无法启动主客服后端。"
    exit 1
}
Write-Ok ".env 配置已就位"

# ==========================================================
# 2. 构建镜像
# ==========================================================
Write-Title "2/4 构建镜像（首次约 3-8 分钟，请耐心等待）"

docker compose build 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Err "镜像构建失败，请查看上方日志。"
    exit 1
}
Write-Ok "镜像构建完成"

# ==========================================================
# 3. 启动容器并等待就绪
# ==========================================================
Write-Title "3/4 启动容器"
docker compose up -d 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Err "容器启动失败，请查看上方日志。"
    exit 1
}

Write-Host ""
Write-Host "  正在等待全部服务就绪..." -ForegroundColor Cyan
# 一键启动后的落地页：登录 / 注册页
$target = 'http://localhost:8080/login'
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$ready = $false
$elapsed = 0

while ((Get-Date) -lt $deadline) {
    try {
        $resp = Invoke-WebRequest -Uri $target -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {
        # 服务还没起来，继续等
    }
    Start-Sleep -Seconds 3
    $elapsed += 3
    Write-Host ("      ... 等待中 {0}s" -f $elapsed) -ForegroundColor DarkGray
}

if (-not $ready) {
    Write-Warn "等待超时（$TimeoutSeconds 秒），页面仍未就绪。当前容器状态："
    docker compose ps 2>&1 | Out-Host
    Write-Warn "可执行  docker compose logs -f  查看日志定位问题。"
    exit 1
}
Write-Ok "全部服务已就绪"

# ==========================================================
# 4. 打开浏览器
# ==========================================================
Write-Title "4/4 打开页面"

Write-Host ""
docker compose ps 2>&1 | Out-Host

Write-Host ""
Write-Host "  服务访问地址：" -ForegroundColor White
Write-Host "    · 登录 / 注册页  http://localhost:8080/login       <- 主入口" -ForegroundColor Green
Write-Host "    · 客服工作台     http://localhost:8080" -ForegroundColor Green
Write-Host "    · 主客服后端API  http://localhost:18082/docs" -ForegroundColor Gray
Write-Host "    · 电商业务服务   http://localhost:18081/docs" -ForegroundColor Gray
Write-Host "    · MySQL 数据库   localhost:3306 (itwwy / 123456)" -ForegroundColor Gray
Write-Host ""

if (-not $NoBrowser) {
    Write-Step "正在打开浏览器..."
    Start-Process $target
    Write-Ok "浏览器已弹出"
} else {
    Write-Step "已跳过打开浏览器（-NoBrowser）"
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Magenta
Write-Host "  启动完成！登录页：http://localhost:8080/login" -ForegroundColor Green
Write-Host "  停止全部服务：双击 stop.bat" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Magenta
Write-Host ""
