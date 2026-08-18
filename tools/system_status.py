import time

import psutil

# A short interval so cpu_percent() reflects a real (brief) sample rather
# than the meaningless 0.0% psutil returns on the very first call with no
# interval given — a real correctness gotcha with this specific API, not
# a style choice.
CPU_SAMPLE_SECONDS = 0.3

# Optical drives and similar report fstype "" and hang/error on disk_usage()
# — skip anything without a real filesystem rather than letting one bad
# drive break the whole status report.
_SKIP_PARTITION_OPTS = {"cdrom"}


def _disk_usage() -> list[dict]:
    drives = []
    for part in psutil.disk_partitions():
        if not part.fstype or any(opt in part.opts for opt in _SKIP_PARTITION_OPTS):
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue  # unreadable (e.g. an empty card reader slot) — skip, don't fail the whole report
        drives.append(
            {
                "drive": part.mountpoint,
                "used_gb": round(usage.used / 1e9, 1),
                "total_gb": round(usage.total / 1e9, 1),
                "percent_used": usage.percent,
            }
        )
    return drives


def get_system_status() -> dict:
    cpu_percent = psutil.cpu_percent(interval=CPU_SAMPLE_SECONDS)
    memory = psutil.virtual_memory()
    uptime_seconds = int(time.time() - psutil.boot_time())

    status = {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_used_gb": round(memory.used / 1e9, 1),
        "memory_total_gb": round(memory.total / 1e9, 1),
        "disks": _disk_usage(),
        "uptime_hours": round(uptime_seconds / 3600, 1),
    }

    battery = psutil.sensors_battery()
    if battery is not None:  # None on desktops with no battery hardware at all
        status["battery_percent"] = battery.percent
        status["battery_plugged_in"] = battery.power_plugged

    return status
