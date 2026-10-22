# spider.ps1 —— 微信/知乎文章抓取器的 PowerShell 薄封装
#
# 参数解析全部交给 Python CLI（spider_core/cli.py），本脚本只负责：
#   1) 自动定位可用的 Python 解释器（SPIDER_PYTHON → .venv → conda spider 环境 → PATH）
#   2) 把参数原样转发给 spider.py
#
# 用法：
#   .\spider.ps1 <URL> [选项]          # 直接运行脚本
#   . .\spider.ps1; spider <URL> ...   # 点源后使用 spider 函数
# 帮助：.\spider.ps1 --help

$script:SpiderRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }

function Resolve-SpiderPython {
    $candidates = @()
    if ($env:SPIDER_PYTHON) { $candidates += $env:SPIDER_PYTHON }
    $candidates += (Join-Path $script:SpiderRoot '.venv\Scripts\python.exe')
    $candidates += 'D:\workSpace\wen\Environment\Tools\miniconda3\envs\spider\python.exe'

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    return $null
}

function spider {
    $python = Resolve-SpiderPython
    if (-not $python) {
        Write-Error "找不到 Python 解释器。请设置 SPIDER_PYTHON，或在本地 .venv 中安装 requirements.txt 依赖。"
        return
    }

    $entry = Join-Path $script:SpiderRoot 'spider.py'
    if (-not (Test-Path $entry)) {
        Write-Error "找不到入口脚本: $entry"
        return
    }

    & $python $entry @args
}

if ($MyInvocation.InvocationName -ne '.') {
    spider @args
}
