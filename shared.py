import re

builds = {"Alpha":"This is an alpha release and you might encounter BUGS. IT IS NOT INTENDED FOR PRODUCTION USE.","Beta":"This is a beta release. If you encounter bugs, please open an issue on GitHub.","Stable":"This is a stable release. While we've worked hard to ensure reliability, please let us know if you run into any issues."}
current_build = "Alpha"
build_version = "v0.0.0"

def format_bytes(size): #转换大小
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    if size < 1024:
        return f"{size} {units[0]}"

    value = float(size)
    unit_index = 0

    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1

    # 保留两位小数并去掉末尾的 0
    formatted = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{formatted} {units[unit_index]}"

def get_bytes(size):
    size = size.strip().lower()
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*([kmgtp]?b?)?', size)
    if not match:
        return 0
    num_str, unit = match.groups()
    num = float(num_str)
    if unit is None or unit == '' or unit == 'b':
        return int(num)
    unit = unit.rstrip('b')  # k → kb / k 都支持

    units = {'k': 1024,'m': 1024 ** 2,'g': 1024 ** 3,'t': 1024 ** 4,'p': 1024 ** 5}
    if unit not in units:
        return 0
    return int(num * units[unit])
