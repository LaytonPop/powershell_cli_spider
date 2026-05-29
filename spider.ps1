[CmdletBinding(DefaultParameterSetName = 'url')]
param (
    [switch]$Help,

    [Parameter(ParameterSetName = 'batch')]
    [string]$BatchFile,

    [Alias('u')]
    [Parameter(Position = 0, ParameterSetName = 'url')]
    [string]$Url,

    [Alias('f')]
    [string[]]$Folder = @(),

    [Alias('o')]
    [ValidateSet('html', 'md')]
    [string]$Format = 'html'
)

function spider {
    [CmdletBinding(DefaultParameterSetName = 'url')]
    param (
        [switch]$Help,

        [Parameter(ParameterSetName = 'batch')]
        [string]$BatchFile,

        [Alias('u')]
        [Parameter(Position = 0, ParameterSetName = 'url')]
        [string]$Url,

        [Alias('f')]
        [string[]]$Folder = @(),

        [Alias('o')]
        [ValidateSet('html', 'md')]
        [string]$Format = 'html'
    )

    if ($Help) {
        @"
用法:
  .\spider.ps1 -u <url> [-o md] [-f <folder> ...]
  .\spider.ps1 <url> [-o md] [-f <folder> ...]
  .\spider.ps1 -BatchFile <file> [-o md] [-f <folder> ...]
  spider -u <url> [-o md] [-f <folder> ...]
  spider <url> [-o md] [-f <folder> ...]
  spider -BatchFile <file> [-o md] [-f <folder> ...]

参数:
  <url>             文章 URL（直接输入，无需 -Url）
  -u <url>          文章 URL（与位置参数等价）
  -BatchFile <file> 指定包含 URL 列表的文本文件（每行一个 URL）
  -o <format>       输出格式: html 或 md (默认: html)
  -f <folder>       子目录段（可多次使用）

目录别名:
  A -> 001-Current_Projects
  B -> 002-raw_resource
  C -> 003-wiki_schema
  也兼容旧写法: A-Current_Projects / B-raw_resource / C-wiki_schema

示例:
  .\spider.ps1 -u https://www.zhihu.com/question/362222222 -f A -o md
  spider https://mp.weixin.qq.com/s/VG5nz-mw0T_X5kvW83eGQg
  spider -u https://zhuanlan.zhihu.com/p/xxxx -o md
  spider https://... -f A -f IoT -o md
  spider -BatchFile "F:\workspace3\wen\idea\urls.txt" -f B
"@
        return
    }

    # 直接使用 spider conda 环境的 Python（避免 conda activate 在 PowerShell 中的兼容问题）
    $pythonExe = "C:\Users\morganWen\.conda\envs\spider\python.exe"
    if (-not (Test-Path $pythonExe)) {
        Write-Error "找不到 spider conda 环境的 Python，请确认环境存在: $pythonExe"
        return
    }

    $spiderPy = "F:\workspace3\cmd_utils\spider\spider.py"

    if ($BatchFile) {
        if (-Not (Test-Path $BatchFile)) {
            Write-Error "Batch file 不存在: $BatchFile"
            return
        }
        Get-Content -Path $BatchFile | ForEach-Object {
            $line = $_.Trim()
            if ($line) {
                Write-Host "正在处理: $line"
                $batchArgs = @($spiderPy, "default", "-u", $line, "-o", $Format)
                foreach ($f in $Folder) { $batchArgs += "-f"; $batchArgs += $f }
                & $pythonExe $batchArgs
            }
        }
        return
    }

    if ($Url) {
        $fmtArgs = @($spiderPy, "default", "-u", $Url, "-o", $Format)
        foreach ($f in $Folder) { $fmtArgs += "-f"; $fmtArgs += $f }
        & $pythonExe $fmtArgs
        return
    }

    Write-Host "请提供 -Url 或 -BatchFile 参数，或使用 -Help 查看用法。"
}

if ($MyInvocation.InvocationName -ne '.') {
    $invokeArgs = @{
        Help = $Help
        Folder = $Folder
        Format = $Format
    }

    if ($PSBoundParameters.ContainsKey('BatchFile')) {
        $invokeArgs.BatchFile = $BatchFile
    }

    if ($PSBoundParameters.ContainsKey('Url')) {
        $invokeArgs.Url = $Url
    }

    spider @invokeArgs
}
