"""Measured with `odvm fetch-recovery --all --check` (GitHub Action, real official TWRP images).

verdict: no = cannot boot on QEMU 'virt'; unknown = kernel could not be read.
"""
MEASURED = {
    'pixel': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Qualcomm'},
    'pixel2': {'verdict': 'unknown', 'reason': 'unreadable', 'arch': 'unknown', 'soc': 'Qualcomm'},
    'pixel3': {'verdict': 'unknown', 'reason': 'unreadable', 'arch': 'unknown', 'soc': 'Qualcomm'},
    'nexus5': {'verdict': 'no', 'reason': 'no_virt', 'arch': 'arm32', 'soc': 'Qualcomm'},
    'nexus5x': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Qualcomm'},
    'nexus6p': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Qualcomm'},
    's4': {'verdict': 'no', 'reason': 'no_virt', 'arch': 'arm32', 'soc': 'Qualcomm'},
    's5': {'verdict': 'no', 'reason': 'no_virt', 'arch': 'arm32', 'soc': 'Qualcomm'},
    's7': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Samsung Exynos'},
    's8': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Samsung Exynos'},
    's9': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Samsung Exynos'},
    's10': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Samsung Exynos'},
    'note4': {'verdict': 'no', 'reason': 'no_virt', 'arch': 'arm32', 'soc': 'Qualcomm'},
    'oneplus3': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Qualcomm'},
    'oneplus5': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Qualcomm'},
    'oneplus6': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Qualcomm'},
    'oneplus7pro': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'unknown', 'soc': 'Qualcomm'},
    'pocof1': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Qualcomm'},
    'mia2': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Qualcomm'},
    'redminote7': {'verdict': 'no', 'reason': 'no_uart', 'arch': 'arm64', 'soc': 'Qualcomm'},
}
