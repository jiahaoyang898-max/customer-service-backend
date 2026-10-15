<#
================================================================
  电商小二 · 全栈一键启动脚本（Windows / PowerShell）

  做四件事：
    1. 环境自检（Docker 是否运行、.env 是否存在）
    2. 构建镜像（首次较慢，之后走缓存）
    3. 后台启动全部容器，并等待服务真正就绪
    4. 自动弹出浏览器打开 http://localhost:18080

  用法：
    powershell -ExecutionPolicy Bypass -File start.ps1
    powershell -ExecutionPolicy Bypass -File start.ps1 -NoBrowser
    powershell -ExecutionPolicy Bypass -File start.ps1 -FrontendPort 18090   # 临时覆盖入口端口
================================================================
#>
[CmdletBinding()]
param(
    # 启动后不自动打开浏览器
    [switch]$NoBrowser,
    # 等待服务就绪的最长秒数（首次构建可能需要几分钟）
    [int]$TimeoutSeconds = 600,
    # 前端入口宿主端口；默认 0 = 从 docker-compose.yml 的 ports 自动解析，改端口不用动本脚本
    [int]$FrontendPort = 0,
    # 跳过端口预检（仅在你确认冲突无害时使用，不推荐）
    [switch]$SkipPortCheck
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

# ---------- 端口解析：宿主端口只认 docker-compose.yml，脚本内不散落硬编码 ----------
# 匹配形如  - "127.0.0.1:13306:3306"  /  - "18081:18081"  的 ports 条目
function Get-ComposePortMappings {
    param([Parameter(Mandatory = $true)][string]$Path)
    $list = @()
    foreach ($line in (Get-Content -LiteralPath $Path)) {
        if ($line -match '^\s*-\s*"?(?:[0-9A-Fa-f.:]+:)?(\d+):(\d+)"?\s*$') {
            $list += [pscustomobject]@{ HostPort = [int]$Matches[1]; ContainerPort = [int]$Matches[2] }
        }
    }
    return $list
}

# 按容器侧端口反查宿主端口（容器间走服务名，宿主侧才是映射出来的数字）
function Get-HostPort($ContainerPort, $Fallback) {
    $hit = @($script:portMappings | Where-Object { $_.ContainerPort -eq $ContainerPort }) | Select-Object -First 1
    if ($hit) { return $hit.HostPort }
    return $Fallback
}

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
# 1.5 端口预检：把宿主端口冲突暴露在构建之前
#     （否则白等 3-8 分钟 build，最后只收到一句泛化的"容器启动失败"）
# ==========================================================
Write-Title "1.5 端口预检"

$composeFile = Join-Path $Root 'docker-compose.yml'
if (-not (Test-Path -LiteralPath $composeFile)) {
    Write-Err "未找到 $composeFile，无法解析端口映射。"
    exit 1
}

$script:portMappings = @(Get-ComposePortMappings -Path $composeFile)
$script:hostPorts    = @($script:portMappings | ForEach-Object { $_.HostPort } | Select-Object -Unique)

if ($script:hostPorts.Count -eq 0) {
    Write-Warn "未从 docker-compose.yml 解析出任何 ports 映射，跳过端口预检。"
    if ($FrontendPort -le 0) { $FrontendPort = 18080 }
} else {
    if ($FrontendPort -le 0) {
        $fe = @($script:portMappings | Where-Object { $_.ContainerPort -eq 80 }) | Select-Object -First 1
        $FrontendPort = if ($fe) { $fe.HostPort } else { $script:hostPorts[0] }
    }
    Write-Step ("compose 声明的宿主端口：{0}（前端入口 {1}）" -f ($script:hostPorts -join ', '), $FrontendPort)

    if ($SkipPortCheck) {
        Write-Warn "已指定 -SkipPortCheck，跳过端口占用检测。"
    } else {
        # 本项目自己已运行的容器占着同名端口，属于重复启动/重建场景，不算冲突
        $projName = ''
        $projLine = Select-String -Path $composeFile -Pattern '^\s*name:\s*(.+?)\s*$' | Select-Object -First 1
        if ($projLine) { $projName = $projLine.Matches[0].Groups[1].Value }
        $ownPorts = ''
        if ($projName) {
            $ownLines = @(docker ps --filter "label=com.docker.compose.project=$projName" --format '{{.Ports}}' 2>$null)
            if ($LASTEXITCODE -eq 0) { $ownPorts = ($ownLines -join ' ') }
        }

        $busy = @()
        foreach ($p in $script:hostPorts) {
            $listeners = @(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)
            if ($listeners.Count -eq 0) { continue }
            if ($ownPorts -match ("[:.]{0}->" -f [int]$p)) {
                Write-Ok ("端口 {0} 由本项目已运行容器占用（{1}），将复用或重建" -f $p, $projName)
                continue
            }
            foreach ($ownerPid in @($listeners | ForEach-Object { $_.OwningProcess } | Select-Object -Unique)) {
                $ownerName = try { (Get-Process -Id $ownerPid -ErrorAction Stop).ProcessName } catch { '未知进程' }
                $busy += [pscustomobject]@{ Port = $p; OwnerPid = $ownerPid; OwnerName = $ownerName }
            }
        }

        if ($busy.Count -gt 0) {
            Write-Err "端口预检未通过：以下宿主端口已被其他进程占用，Docker 启动会报 port is already allocated。"
            foreach ($b in $busy) {
                Write-Host ("    · 端口 {0}  <-  进程 {1} (PID {2})" -f $b.Port, $b.OwnerName, $b.OwnerPid) -ForegroundColor Red
            }
            Write-Host ""
            Write-Host "  解决办法（任选其一，改端口无需重建镜像）：" -ForegroundColor Yellow
            Write-Host "    1. 改 docker-compose.yml 里该端口的宿主侧数字（冒号左边那个，如 18080 -> 18090），再 docker compose up -d；" -ForegroundColor Yellow
            Write-Host "    2. 占用者若是本项目遗留的旧容器，先 docker ps 核对名字再停掉；切勿停 data-agent / deep-agent-search 等他人项目的容器；" -ForegroundColor Yellow
            Write-Host "    3. 占用者是本机 MySQL80 等 Windows 服务时，services.msc 里停止并设为手动启动；" -ForegroundColor Yellow
            Write-Host "    4. 确认冲突无害时才用 -SkipPortCheck 跳过本检查。" -ForegroundColor Yellow
            exit 1
        }
        Write-Ok ("端口预检通过：{0} 均空闲" -f ($script:hostPorts -join ', '))
    }
}

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
# 一键启动后的落地页：登录 / 注册页（端口来自 compose 解析或 -FrontendPort）
$target = "http://localhost:$FrontendPort/login"
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

# 宿主端口统一从 compose 的 ports 映射反查（容器侧端口作为 key）
$mysqlHostPort   = Get-HostPort 3306  13306
$commerceApiPort = Get-HostPort 18081 18081
$backendApiPort  = Get-HostPort 18082 18082

# ==========================================================
# 4. 打开浏览器
# ==========================================================
Write-Title "4/4 打开页面"

Write-Host ""
docker compose ps 2>&1 | Out-Host

Write-Host ""
Write-Host "  服务访问地址：" -ForegroundColor White
Write-Host ("    · 登录 / 注册页  http://localhost:{0}/login       <- 主入口" -f $FrontendPort) -ForegroundColor Green
Write-Host ("    · 客服工作台     http://localhost:{0}" -f $FrontendPort) -ForegroundColor Green
Write-Host ("    · 主客服后端API  http://localhost:{0}/docs" -f $backendApiPort) -ForegroundColor Gray
Write-Host ("    · 电商业务服务   http://localhost:{0}/docs" -f $commerceApiPort) -ForegroundColor Gray
Write-Host ("    · MySQL 数据库   127.0.0.1:{0} (itwwy，仅本机可达)" -f $mysqlHostPort) -ForegroundColor Gray
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
Write-Host ("  启动完成！登录页：http://localhost:{0}/login" -f $FrontendPort) -ForegroundColor Green
Write-Host "  停止全部服务：双击 stop.bat" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Magenta
Write-Host ""
