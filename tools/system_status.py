import time

import psutil

CPU_SAMPLE_SECONDS = 0.3
_SKIP_PARTITION_OPTS = {"cdrom"}


def _disk_usage() -> list[dict]:
    drives = []
    for part in psutil.disk_partitions():
        if not part.fstype or any(opt in part.opts for opt in _SKIP_PARTITION_OPTS):
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue
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

    try:
        battery = psutil.sensors_battery()
    except Exception:
        battery = None
    if battery is not None:
        status["battery_percent"] = battery.percent
        status["battery_plugged_in"] = battery.power_plugged

    return status
