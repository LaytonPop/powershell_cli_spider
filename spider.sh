#!/usr/bin/env bash
# spider.sh — bash/zsh wrapper for the article spider (Linux/macOS replacement for spider.ps1)
#
# Usage:
#   ./spider.sh -u <url> [-df <folder> ...] [-o md|html] [--dry-run]
#   ./spider.sh <url> [-df <folder> ...] [-o md|html] [--dry-run]
#   ./spider.sh -u <url> -f <full_path> [-o md|html] [--dry-run]
#   ./spider.sh <url> -f <full_path> [-o md|html] [--dry-run]
#   ./spider.sh -B|--batch-file <file> [-df <folder> ...] [-o md|html] [--dry-run]
#   ./spider.sh -B|--batch-file <file> -f <full_path> [-o md|html] [--dry-run]
#
# Source this file to get the `spider` shell function, or run directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SPIDER_PY="${SCRIPT_DIR}/spider.py"

# --- helpers ----------------------------------------------------------------

show_help() {
    cat <<'EOF'
用法:
  spider -u <url> [-df <folder> ...] [-o md|html] [--dry-run]
  spider <url> [-df <folder> ...] [-o md|html] [--dry-run]
  spider -u <url> -f <full_path> [-o md|html] [--dry-run]
  spider <url> -f <full_path> [-o md|html] [--dry-run]
  spider -B|--batch-file <file> [-df <folder> ...] [-o md|html] [--dry-run]
  spider -B|--batch-file <file> -f <full_path> [-o md|html] [--dry-run]

参数:
  <url>             文章 URL（直接输入，无需 -u）
  -u <url>          文章 URL（与位置参数等价）
  -B, --batch-file  指定包含 URL 列表的文本文件（每行一个 URL）
  -df <folder>      默认知识库根目录下的子目录段（可多次使用）
  -f <full_path>    直接输出目录路径（不走默认知识库根目录）
  -o <format>       输出格式: html 或 md (默认: html)
  --dry-run         仅解析路径和参数，不执行爬取
  -h, --help        显示帮助

目录别名:
  A -> 001-Current_Projects
  B -> 002-raw_resource
  C -> 003-wiki_schema
  也兼容旧写法: A-Current_Projects / B-raw_resource / C-wiki_schema

环境变量:
  SPIDER_PYTHON     指定 Python 解释器 (默认: python3)
  SPIDER_BASE       覆盖默认知识库根目录 (默认: config.py 中的 BASES[default])

示例:
  spider -u https://www.zhihu.com/question/362222222 -df A -df mathcs -o md
  spider https://mp.weixin.qq.com/s/VG5nz-mw0T_X5kvW83eGQg -df A -df IoT -o html
  spider -u https://zhuanlan.zhihu.com/p/xxxx -f /home/user/articles -o md
  spider -B /home/user/urls.txt -df B -o md --dry-run
EOF
}

# --- argument parsing -------------------------------------------------------

spider() {
    local url=""
    local batch_file=""
    local default_folders=()
    local full_path=""
    local format="html"
    local dry_run=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help|help)
                show_help
                return 0
                ;;
            --dry-run|--DryRun|-DryRun)
                dry_run="--dry-run"
                shift
                ;;
            -u|-U|--url|--u)
                if [[ $# -lt 2 ]]; then
                    echo "错误: $1 缺少 URL 值。" >&2
                    return 1
                fi
                url="$2"
                shift 2
                ;;
            -B|--batch-file|-BatchFile|--BatchFile|--batchfile|-batchfile)
                if [[ $# -lt 2 ]]; then
                    echo "错误: $1 缺少文件路径。" >&2
                    return 1
                fi
                batch_file="$2"
                shift 2
                ;;
            -df|--df|--default-folder|--DefaultFolder|-DefaultFolder)
                if [[ $# -lt 2 ]]; then
                    echo "错误: $1 缺少目录段。" >&2
                    return 1
                fi
                default_folders+=("$2")
                shift 2
                ;;
            -f|--f|--full-path|--FullPath|-FullPath)
                if [[ $# -lt 2 ]]; then
                    echo "错误: $1 缺少完整输出路径。" >&2
                    return 1
                fi
                full_path="$2"
                shift 2
                ;;
            -o|--o|--format|--Format|-Format)
                if [[ $# -lt 2 ]]; then
                    echo "错误: $1 缺少格式值。" >&2
                    return 1
                fi
                case "$2" in
                    html|md) format="$2" ;;
                    *)
                        echo "错误: 不支持的输出格式: $2。可用值: html, md" >&2
                        return 1
                        ;;
                esac
                shift 2
                ;;
            -*)
                echo "错误: 未知参数 $1" >&2
                return 1
                ;;
            *)
                # Positional argument -> URL
                if [[ -z "$url" ]]; then
                    url="$1"
                else
                    echo "错误: 多余的参数: $1" >&2
                    return 1
                fi
                shift
                ;;
        esac
    done

    # --- validation ---------------------------------------------------------

    if [[ -n "$full_path" ]] && [[ ${#default_folders[@]} -gt 0 ]]; then
        echo "错误: 不能同时使用 -df 和 -f；请选择默认知识库模式或直接路径模式。" >&2
        return 1
    fi

    if [[ -z "$url" ]] && [[ -z "$batch_file" ]]; then
        echo "错误: 请提供 URL 或 -B/--batch-file 参数。使用 -h 查看帮助。" >&2
        return 1
    fi

    # --- pick Python --------------------------------------------------------

    local python_exe="${SPIDER_PYTHON:-python3}"
    if ! command -v "$python_exe" &>/dev/null; then
        echo "错误: 找不到 Python 解释器: $python_exe（可用 SPIDER_PYTHON 环境变量指定）" >&2
        return 1
    fi

    if [[ ! -f "$SPIDER_PY" ]]; then
        echo "错误: 找不到 spider.py: $SPIDER_PY" >&2
        return 1
    fi

    # --- build Python args --------------------------------------------------

    build_python_args() {
        local _args=("$SPIDER_PY" -o "$format")
        if [[ -n "$batch_file" ]]; then
            _args+=(--batch-file "$batch_file")
        else
            _args+=(-u "$url")
        fi
        for _df in "${default_folders[@]}"; do
            _args+=(-df "$_df")
        done
        if [[ -n "$full_path" ]]; then
            _args+=(-f "$full_path")
        fi
        if [[ -n "$dry_run" ]]; then
            _args+=(--dry-run)
        fi
        printf '%s\n' "${_args[@]}"
    }

    # --- batch mode ---------------------------------------------------------

    if [[ -n "$batch_file" ]]; then
        if [[ ! -f "$batch_file" ]]; then
            echo "错误: Batch file 不存在: $batch_file" >&2
            return 1
        fi
        local _pyargs
        mapfile -t _pyargs < <(build_python_args)
        "$python_exe" "${_pyargs[@]}"
        return $?
    fi

    # --- single URL mode ----------------------------------------------------

    local _pyargs
    mapfile -t _pyargs < <(build_python_args)
    "$python_exe" "${_pyargs[@]}"
}

# If executed directly (not sourced), run spider with all arguments.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    spider "$@"
fi
