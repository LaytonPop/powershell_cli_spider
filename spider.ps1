function Show-SpiderHelp {
    @"
用法:
  .\spider.ps1 -u <url> [-df <folder> ...] [-o md] [-DryRun]
  .\spider.ps1 -u <url> -f <full_path> [-o md] [-DryRun]
  .\spider.ps1 <url> [-df <folder> ...] [-o md] [-DryRun]
  .\spider.ps1 <url> -f <full_path> [-o md] [-DryRun]
  .\spider.ps1 -BatchFile <file> [-df <folder> ...] [-o md] [-DryRun]
  .\spider.ps1 -BatchFile <file> -f <full_path> [-o md] [-DryRun]
  spider -u <url> [-df <folder> ...] [-o md] [-DryRun]
  spider -u <url> -f <full_path> [-o md] [-DryRun]
  spider <url> [-df <folder> ...] [-o md] [-DryRun]
  spider <url> -f <full_path> [-o md] [-DryRun]
  spider -BatchFile <file> [-df <folder> ...] [-o md] [-DryRun]
  spider -BatchFile <file> -f <full_path> [-o md] [-DryRun]

参数:
  <url>             文章 URL（直接输入，无需 -u）
  -u <url>          文章 URL（与位置参数等价）
  -BatchFile <file> 指定包含 URL 列表的文本文件（每行一个 URL）
  -df <folder>      默认知识库根目录下的子目录段（可多次使用）
  -f <full_path>    直接输出目录路径（不走默认知识库根目录）
  -o <format>       输出格式: html 或 md (默认: html)
  -DryRun           仅解析路径和参数，不执行爬取
  -Help             显示帮助

目录别名:
  A -> 001-Current_Projects
  B -> 002-raw_resource
  C -> 003-wiki_schema
  也兼容旧写法: A-Current_Projects / B-raw_resource / C-wiki_schema

示例:
  .\spider.ps1 -u https://www.zhihu.com/question/362222222 -df A -df mathcs -o md
  spider https://mp.weixin.qq.com/s/VG5nz-mw0T_X5kvW83eGQg -df A -df IoT -o html
  spider -u https://zhuanlan.zhihu.com/p/xxxx -f "F:\workspace3\wen\temp\articles" -o md
  spider -BatchFile "F:\workspace3\wen\idea\urls.txt" -df B -o md -DryRun
"@
}

function ConvertTo-SpiderArguments {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$CliArgs
    )

    $parsed = [ordered]@{
        Help = $false
        BatchFile = $null
        Url = $null
        DefaultFolders = @()
        FullPath = $null
        Format = 'html'
        DryRun = $false
    }

    $index = 0
    while ($index -lt $CliArgs.Count) {
        $token = [string]$CliArgs[$index]
        $normalized = $token.ToLowerInvariant()

        switch ($normalized) {
            '-help' { $parsed.Help = $true; $index++; continue }
            '--help' { $parsed.Help = $true; $index++; continue }
            '-h' { $parsed.Help = $true; $index++; continue }
            '-dryrun' { $parsed.DryRun = $true; $index++; continue }
            '--dry-run' { $parsed.DryRun = $true; $index++; continue }
            '-u' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 -u 缺少 URL 值。" }
                $parsed.Url = [string]$CliArgs[$index + 1]
                $index += 2
                continue
            }
            '--u' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 --u 缺少 URL 值。" }
                $parsed.Url = [string]$CliArgs[$index + 1]
                $index += 2
                continue
            }
            '--url' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 --url 缺少 URL 值。" }
                $parsed.Url = [string]$CliArgs[$index + 1]
                $index += 2
                continue
            }
            '-batchfile' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 -BatchFile 缺少文件路径。" }
                $parsed.BatchFile = [string]$CliArgs[$index + 1]
                $index += 2
                continue
            }
            '--batchfile' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 --BatchFile 缺少文件路径。" }
                $parsed.BatchFile = [string]$CliArgs[$index + 1]
                $index += 2
                continue
            }
            '--batch-file' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 --batch-file 缺少文件路径。" }
                $parsed.BatchFile = [string]$CliArgs[$index + 1]
                $index += 2
                continue
            }
            '-df' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 -df 缺少目录段。" }
                $parsed.DefaultFolders += [string]$CliArgs[$index + 1]
                $index += 2
                continue
            }
            '--df' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 --df 缺少目录段。" }
                $parsed.DefaultFolders += [string]$CliArgs[$index + 1]
                $index += 2
                continue
            }
            '--default-folder' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 --default-folder 缺少目录段。" }
                $parsed.DefaultFolders += [string]$CliArgs[$index + 1]
                $index += 2
                continue
            }
            '-f' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 -f 缺少完整输出路径。" }
                $parsed.FullPath = [string]$CliArgs[$index + 1]
                $index += 2
                continue
            }
            '--f' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 --f 缺少完整输出路径。" }
                $parsed.FullPath = [string]$CliArgs[$index + 1]
                $index += 2
                continue
            }
            '--full-path' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 --full-path 缺少完整输出路径。" }
                $parsed.FullPath = [string]$CliArgs[$index + 1]
                $index += 2
                continue
            }
            '-o' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 -o 缺少格式值。" }
                $format = [string]$CliArgs[$index + 1]
                if ($format -notin @('html', 'md')) {
                    throw "不支持的输出格式: $format。可用值: html, md"
                }
                $parsed.Format = $format
                $index += 2
                continue
            }
            '--o' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 --o 缺少格式值。" }
                $format = [string]$CliArgs[$index + 1]
                if ($format -notin @('html', 'md')) {
                    throw "不支持的输出格式: $format。可用值: html, md"
                }
                $parsed.Format = $format
                $index += 2
                continue
            }
            '--format' {
                if ($index + 1 -ge $CliArgs.Count) { throw "参数 --format 缺少格式值。" }
                $format = [string]$CliArgs[$index + 1]
                if ($format -notin @('html', 'md')) {
                    throw "不支持的输出格式: $format。可用值: html, md"
                }
                $parsed.Format = $format
                $index += 2
                continue
            }
            default {
                if ($token.StartsWith('-')) {
                    throw "未知参数: $token"
                }
                if (-not $parsed.Url) {
                    $parsed.Url = $token
                    $index++
                    continue
                }
                throw "无法识别的额外参数: $token"
            }
        }
    }

    if ($parsed.DefaultFolders.Count -gt 0 -and $parsed.FullPath) {
        throw "不能同时使用 -df 和 -f；请选择默认知识库模式或直接路径模式。"
    }

    if (-not $parsed.Help -and -not $parsed.Url -and -not $parsed.BatchFile) {
        throw "请提供 URL 或 -BatchFile 参数。"
    }

    return [pscustomobject]$parsed
}

function Invoke-SpiderPython {
    param(
        [string]$PythonExe,
        [string]$SpiderPy,
        [string]$Url,
        [string[]]$DefaultFolders,
        [string]$FullPath,
        [string]$Format,
        [bool]$DryRun
    )

    $pythonArgs = @($SpiderPy, "-u", $Url, "-o", $Format)
    foreach ($df in $DefaultFolders) {
        $pythonArgs += "-df"
        $pythonArgs += $df
    }
    if ($FullPath) {
        $pythonArgs += "-f"
        $pythonArgs += $FullPath
    }
    if ($DryRun) {
        $pythonArgs += "--dry-run"
    }

    & $PythonExe $pythonArgs
}

function spider {
    $CliArgs = @($args)

    try {
        $parsed = ConvertTo-SpiderArguments -CliArgs $CliArgs
    } catch {
        Write-Error $_
        return
    }

    if ($parsed.Help) {
        Show-SpiderHelp
        return
    }

    # 直接使用 spider conda 环境的 Python（避免 conda activate 在 PowerShell 中的兼容问题）
    $pythonExe = "C:\Users\morganWen\.conda\envs\spider\python.exe"
    if (-not (Test-Path $pythonExe)) {
        Write-Error "找不到 spider conda 环境的 Python，请确认环境存在: $pythonExe"
        return
    }

    $spiderPy = "F:\workspace3\cmd_utils\spider\spider.py"

    if ($parsed.BatchFile) {
        if (-not (Test-Path $parsed.BatchFile)) {
            Write-Error "Batch file 不存在: $($parsed.BatchFile)"
            return
        }

        Get-Content -Path $parsed.BatchFile | ForEach-Object {
            $line = $_.Trim()
            if ($line) {
                Write-Host "正在处理: $line"
                Invoke-SpiderPython `
                    -PythonExe $pythonExe `
                    -SpiderPy $spiderPy `
                    -Url $line `
                    -DefaultFolders $parsed.DefaultFolders `
                    -FullPath $parsed.FullPath `
                    -Format $parsed.Format `
                    -DryRun $parsed.DryRun
            }
        }
        return
    }

    Invoke-SpiderPython `
        -PythonExe $pythonExe `
        -SpiderPy $spiderPy `
        -Url $parsed.Url `
        -DefaultFolders $parsed.DefaultFolders `
        -FullPath $parsed.FullPath `
        -Format $parsed.Format `
        -DryRun $parsed.DryRun
}

if ($MyInvocation.InvocationName -ne '.') {
    spider @args
}
