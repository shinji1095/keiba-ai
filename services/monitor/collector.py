#!/usr/bin/env python3
"""Linux host metrics collector. Standard library only; run on the actual host OS."""
import argparse
from collections import deque
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import socket
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid

LOG = logging.getLogger("keiba.monitor")


def cpu_times(proc):
    result = {}
    for line in (proc / "stat").read_text().splitlines():
        name, *numbers = line.split()
        if name == "cpu" or (name.startswith("cpu") and name[3:].isdigit()):
            # guest/guest_nice are already included in user/nice.
            values = list(map(int, numbers[:8]))
            result[name] = (sum(values), values[3] + values[4])
    return result


def cpu_usage(current, previous):
    if previous is None:
        return None
    total, idle = current[0] - previous[0], current[1] - previous[1]
    if total <= 0 or idle < 0:
        return None
    return max(0, min(100, 100 * (total - idle) / total))


def memory_info(proc):
    return {name.rstrip(":"): int(value) * 1024
            for name, value, *_ in (line.split() for line in (proc / "meminfo").read_text().splitlines())}


def network_bytes(proc, interfaces):
    result = [0, 0]
    found = False
    for line in (proc / "net/dev").read_text().splitlines()[2:]:
        name, numbers = line.split(":", 1)
        if name.strip() not in interfaces:
            continue
        values = list(map(int, numbers.split()))
        result[0] += values[0]
        result[1] += values[8]
        found = True
    return result if found else None


def external_interfaces(sys_root):
    # Physical NICs only; virtual bridges/veth/loopback would double count traffic.
    return [p.name for p in (sys_root / "class/net").glob("*") if (p / "device").exists()]


def disk_io(proc, sys_root):
    totals = [0, 0]
    found = False
    for line in (proc / "diskstats").read_text().splitlines():
        values = line.split()
        if len(values) < 14:
            continue
        name = values[2]
        # Whole physical block devices only: omit partitions, loop, dm and md layers.
        device = sys_root / "block" / name
        if not device.exists() or not (device / "device").exists():
            continue
        totals[0] += int(values[5]) * 512
        totals[1] += int(values[9]) * 512
        found = True
    return totals if found else None


def rate(current, previous, elapsed):
    if current is None or previous is None or elapsed <= 0:
        return [None, None]
    return [(cur - prev) / elapsed if cur >= prev else None for cur, prev in zip(current, previous)]


def disks(paths):
    result, seen, errors = [], {}, []
    for label, path in paths:
        try:
            st = os.stat(path)
            fs = os.statvfs(path)
            if st.st_dev in seen:
                result[seen[st.st_dev]]["label"] += f" / {label}"
                continue
            seen[st.st_dev] = len(result)
            total = fs.f_blocks * fs.f_frsize
            used = (fs.f_blocks - fs.f_bfree) * fs.f_frsize
            available = fs.f_bavail * fs.f_frsize
            denominator = used + available
            result.append({"path": str(Path(path).resolve()), "label": label, "total_bytes": total,
                           "used_bytes": used, "available_bytes": available,
                           "percent": used * 100 / denominator if denominator else 0})
        except OSError:
            errors.append(f"ディスク取得失敗: {label} ({path})")
    return result, errors


class Collector:
    def __init__(self, host_id, scope, paths, interfaces=None, proc=Path("/proc"), sys_root=Path("/sys")):
        self.host_id, self.scope, self.paths = host_id, scope, paths
        self.proc, self.sys = proc, sys_root
        self.interfaces = interfaces if interfaces is not None else external_interfaces(sys_root)
        # Each collector session has its own sequence namespace, even across agent restarts.
        self.boot_id = (proc / "sys/kernel/random/boot_id").read_text().strip() + ":" + uuid.uuid4().hex[:12]
        self.sequence = 0
        self.previous_cpu, self.previous_net, self.previous_io = {}, None, None
        self.previous_time = None

    def sample(self):
        now = time.monotonic()
        elapsed = now - self.previous_time if self.previous_time is not None else 0
        current_cpu = cpu_times(self.proc)
        memory = memory_info(self.proc)
        total = memory["MemTotal"]
        available = min(total, memory.get("MemAvailable", memory["MemFree"]))
        disk_values, errors = disks(self.paths)
        net = io = None
        try:
            net = network_bytes(self.proc, self.interfaces)
        except OSError:
            errors.append("ネットワーク取得失敗")
        if net is None:
            errors.append("対象ネットワークなし: --interfaces で外部通信用NICを指定してください")
        try:
            io = disk_io(self.proc, self.sys)
        except OSError:
            errors.append("ディスクI/O取得失敗")
        rx, tx = rate(net, self.previous_net, elapsed)
        read, write = rate(io, self.previous_io, elapsed)
        temperature = temperature_sensor = None
        for sensor in sorted((self.sys / "class/thermal").glob("thermal_zone*")):
            try:
                kind = (sensor / "type").read_text().strip().lower()
                if any(name in kind for name in ("cpu", "pkg", "x86")):
                    temperature = float((sensor / "temp").read_text()) / 1000
                    temperature_sensor = kind
                    break
            except (OSError, ValueError):
                continue
        result = {
            "host_id": self.host_id, "hostname": socket.gethostname(), "scope": self.scope,
            "boot_id": self.boot_id, "sequence": self.sequence,
            "sampled_at": datetime.now(timezone.utc).isoformat(),
            "uptime_sec": float((self.proc / "uptime").read_text().split()[0]),
            "cpu_count": len(current_cpu) - 1,
            "cpu_percent": cpu_usage(current_cpu["cpu"], self.previous_cpu.get("cpu")),
            "cpu_per_core": [cpu_usage(current_cpu[k], self.previous_cpu.get(k))
                             for k in sorted(current_cpu, key=lambda k: int(k[3:] or -1)) if k != "cpu"],
            "memory_total_bytes": total, "memory_available_bytes": available,
            "memory_percent": (total - available) * 100 / total,
            "swap_total_bytes": memory.get("SwapTotal", 0),
            "swap_used_bytes": memory.get("SwapTotal", 0) - memory.get("SwapFree", 0),
            "disks": disk_values, "net_rx_bytes_sec": rx, "net_tx_bytes_sec": tx,
            "disk_read_bytes_sec": read, "disk_write_bytes_sec": write,
            "temperature_c": temperature, "temperature_sensor": temperature_sensor,
            "network_interfaces": self.interfaces, "errors": errors,
        }
        self.previous_cpu, self.previous_net, self.previous_io = current_cpu, net, io
        self.previous_time = now
        self.sequence += 1
        return result


class Sender:
    def __init__(self, base_url, client_id, client_secret):
        self.base_url, self.client_id, self.client_secret = base_url.rstrip("/"), client_id, client_secret
        self.token = None

    def request(self, path, body, token=None):
        request = Request(self.base_url + path, json.dumps(body).encode(),
                          {"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
        with urlopen(request, timeout=3) as response:
            return json.load(response)

    def send(self, sample):
        if not self.token:
            self.token = self.request("/auth/token", {"grant_type": "client_credentials", "client_id": self.client_id,
                                                     "client_secret": self.client_secret, "scope": "monitor:write"})["access_token"]
        try:
            self.request("/system/metrics", sample, self.token)
        except HTTPError as error:
            if error.code == 401:
                self.token = None
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="print one local sample without sending")
    scope = "host"
    if Path("/.dockerenv").exists():
        scope = "container"
    elif "microsoft" in Path("/proc/sys/kernel/osrelease").read_text().lower() or "hypervisor" in Path("/proc/cpuinfo").read_text():
        scope = "vm"
    parser.add_argument("--scope", choices=["host", "vm", "container"], default=os.getenv("MONITOR_SCOPE", scope))
    parser.add_argument("--host-id", default=os.getenv("MONITOR_HOST_ID", socket.gethostname()))
    parser.add_argument("--disk", action="append", help="label=/absolute/path; repeat for data and DB storage")
    parser.add_argument("--interfaces", default=os.getenv("MONITOR_INTERFACES"), help="comma-separated physical NICs")
    args = parser.parse_args()
    configured = args.disk or os.getenv("MONITOR_DISKS", "OS=/").split(";")
    paths = []
    for item in configured:
        label, separator, path = item.partition("=")
        if not separator or not Path(path).is_absolute():
            parser.error("--disk must be label=/absolute/path")
        paths.append((label, path))
    collector = Collector(args.host_id, args.scope, paths,
                          args.interfaces.split(",") if args.interfaces else None)
    if args.once:
        collector.sample()
        time.sleep(1)
        print(json.dumps(collector.sample(), ensure_ascii=False, indent=2))
        return
    client_id, secret = os.getenv("MONITOR_CLIENT_ID"), os.getenv("MONITOR_CLIENT_SECRET")
    if not client_id or not secret:
        parser.error("MONITOR_CLIENT_ID and MONITOR_CLIENT_SECRET are required")
    sender = Sender(os.getenv("MONITOR_API_URL", "http://localhost/api"), client_id, secret)
    pending = deque(maxlen=60)
    logging.basicConfig(level=logging.INFO)
    while True:
        started = time.monotonic()
        try:
            pending.append(collector.sample())
        except (OSError, ValueError, KeyError):
            LOG.exception("host metrics collection failed")
        # Never spend longer than a sampling interval draining buffered samples.
        while pending and time.monotonic() - started < 7:
            if (datetime.now(timezone.utc) - datetime.fromisoformat(pending[0]["sampled_at"])).total_seconds() > 600:
                pending.popleft()
                continue
            try:
                sender.send(pending[0])
                pending.popleft()
            except Exception as error:
                # Do not log request bodies or client secrets.
                LOG.warning("metrics send failed (%s); buffered=%s", type(error).__name__, len(pending))
                break
        time.sleep(max(0, 10 - (time.monotonic() - started)))


if __name__ == "__main__":
    main()
