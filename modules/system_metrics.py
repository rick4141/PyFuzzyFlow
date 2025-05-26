import psutil
import platform
import os
import time
import subprocess
import socket

class SystemMetrics:
    @staticmethod
    def cpu_percent():
        return psutil.cpu_percent(interval=None)
    @staticmethod
    def ram_percent():
        return psutil.virtual_memory().percent
    @staticmethod
    def disk_percent(path="/"):
        return psutil.disk_usage(path).percent
    @staticmethod
    def swap_percent():
        return psutil.swap_memory().percent
    @staticmethod
    def uptime():
        return time.time() - psutil.boot_time()
    @staticmethod
    def network_stats():
        stats = psutil.net_io_counters()
        return {k: getattr(stats, k) for k in stats._fields}
    @staticmethod
    def disk_io():
        io = psutil.disk_io_counters()
        return {k: getattr(io, k) for k in io._fields}
    @staticmethod
    def load_avg():
        if hasattr(os, "getloadavg"):
            return os.getloadavg()
        return (-1, -1, -1)
    @staticmethod
    def processes():
        return len(psutil.pids())
    @staticmethod
    def system_info():
        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "cpu": platform.processor(),
            "python": platform.python_version()
        }

    _custom_metrics = {}
    @classmethod
    def register_metric(cls, name, func):
        cls._custom_metrics[name] = func
    @classmethod
    def get_metric_func(cls, name):
        if hasattr(cls, name):
            return getattr(cls, name)
        if name in cls._custom_metrics:
            return cls._custom_metrics[name]
        raise KeyError(f"Metric '{name}' not found in SystemMetrics.")
    @classmethod
    def list_metrics(cls):
        base_metrics = [m for m in dir(cls) if not m.startswith("_") and callable(getattr(cls, m))]
        custom_metrics = list(cls._custom_metrics.keys())
        return base_metrics + custom_metrics

def get_extended_system_info():
    info = {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cpu_count_logical": psutil.cpu_count(),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_freq": psutil.cpu_freq()._asdict() if hasattr(psutil.cpu_freq(), '_asdict') else {},
        "memory_total_gb": round(psutil.virtual_memory().total / 1e9, 2),
        "memory_avail_gb": round(psutil.virtual_memory().available / 1e9, 2),
        "swap_total_gb": round(psutil.swap_memory().total / 1e9, 2),
        "hostname": socket.gethostname(),
        "disk_info": {
            d.mountpoint: dict(
                total=psutil.disk_usage(d.mountpoint).total,
                used=psutil.disk_usage(d.mountpoint).used,
                free=psutil.disk_usage(d.mountpoint).free,
                percent=psutil.disk_usage(d.mountpoint).percent
            )
            for d in psutil.disk_partitions(all=False) if d.mountpoint
        },
        "net_if_addrs": {iface: [x.address for x in psutil.net_if_addrs().get(iface, [])] for iface in psutil.net_if_addrs()},
        "pip_freeze": subprocess.getoutput("pip freeze").splitlines()
    }
    return info