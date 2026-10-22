#!/usr/bin/env bash
# spider.sh — Linux/macOS 包装层（Windows 用 spider.ps1）
#
# 只做两件事：定位 Python 解释器、把参数原样转发给 spider.py。
# 参数解析的唯一来源是 spider_core/cli.py，本脚本不重复实现。
#
# 用法:
#   ./spider.sh URL [选项]          # 直接运行
#   . ./spider.sh; spider URL [选项] # 点源后使用 spider 函数
#
# 解释器查找顺序: $SPIDER_PYTHON → .venv/bin/python → python3 → python

set -u

SPIDER_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SPIDER_ENTRY="${SPIDER_ROOT}/spider.py"

resolve_spider_python() {
    if [ -n "${SPIDER_PYTHON:-}" ]; then
        printf '%s\n' "$SPIDER_PYTHON"
        return 0
    fi
    if [ -x "${SPIDER_ROOT}/.venv/bin/python" ]; then
        printf '%s\n' "${SPIDER_ROOT}/.venv/bin/python"
        return 0
    fi
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

spider() {
    local python_bin
    python_bin="$(resolve_spider_python)" || {
        printf 'spider: 未找到 Python 解释器；请安装 Python 3.10+ 或设置 SPIDER_PYTHON\n' >&2
        return 127
    }
    "$python_bin" "$SPIDER_ENTRY" "$@"
}

# 直接执行（非 source）时转发参数；source 时只注册函数
if [ "${BASH_SOURCE[0]:-$0}" = "$0" ]; then
    spider "$@"
fi
