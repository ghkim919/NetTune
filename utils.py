import os
import platform
import subprocess
import psutil

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_all_interfaces():
    """시스템의 모든 유효한 네트워크 인터페이스 목록 반환"""
    interfaces = []
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    
    for name, stat in stats.items():
        # 루프백 제외 및 활성화된 인터페이스만 필터링
        if name == 'lo' or name.startswith('lo0'):
            continue
            
        ip = "N/A"
        if name in addrs:
            for addr in addrs[name]:
                if addr.family == 2: # AF_INET (IPv4)
                    ip = addr.address
                    break
        
        status = "Up" if stat.isup else "Down"
        interfaces.append({
            "name": name,
            "ip": ip,
            "status": status,
            "speed": stat.speed
        })
    return interfaces

def get_default_interface():
    """외부 망으로 나가는 기본 네트워크 인터페이스 식별"""
    try:
        if platform.system() == "Darwin":
            output = subprocess.check_output(["route", "-n", "get", "default"]).decode()
            for line in output.splitlines():
                if "interface:" in line:
                    return line.split(":")[1].strip()
        else:
            output = subprocess.check_output(["ip", "route", "show", "default"]).decode()
            parts = output.split()
            if "dev" in parts:
                return parts[parts.index("dev") + 1]
    except Exception as e:
        return f"Error detecting interface: {e}"
    return "Not Found"

def get_mtu(interface):
    """MTU 값 확인"""
    try:
        if platform.system() == "Darwin":
            output = subprocess.check_output(["ifconfig", interface]).decode()
            for line in output.splitlines():
                if "mtu" in line.lower():
                    return line.split("mtu")[1].strip()
        else:
            output = subprocess.check_output(["ip", "link", "show", interface]).decode()
            for line in output.splitlines():
                if "mtu" in line:
                    return line.split("mtu")[1].split()[0]
    except Exception as e:
        return f"Error: {e}"
    return "Unknown"

def get_physical_speed(interface):
    """물리 속도 체크"""
    try:
        if platform.system() == "Linux":
            try:
                output = subprocess.check_output(["ethtool", interface], stderr=subprocess.STDOUT).decode()
                for line in output.splitlines():
                    if "Speed:" in line:
                        speed = line.split(":")[1].strip()
                        return f"{Colors.OKGREEN}{speed}{Colors.ENDC}"
            except:
                return f"{Colors.FAIL}ethtool not available or permission denied{Colors.ENDC}"
        elif platform.system() == "Darwin":
            try:
                output = subprocess.check_output(["ifconfig", interface]).decode()
                for line in output.splitlines():
                    if "media:" in line:
                        media_info = line.split("media:")[1].strip()
                        speed = media_info.split("(")[1].split(")")[0] if "(" in media_info else media_info
                        return f"{Colors.OKGREEN}{speed}{Colors.ENDC}"
                return "Unknown"
            except:
                return f"{Colors.FAIL}ifconfig failed{Colors.ENDC}"
    except Exception as e:
        return f"{Colors.FAIL}Error: {e}{Colors.ENDC}"
    return "Unknown"

def get_tcp_buffers():
    """TCP/IP 버퍼 사이즈 추출"""
    buffers = {}
    try:
        system = platform.system()
        if system == "Linux":
            targets = {
                'tcp_rmem (min default max)': "net.ipv4.tcp_rmem",
                'tcp_wmem (min default max)': "net.ipv4.tcp_wmem",
                'core_rmem_max': "net.core.rmem_max",
                'core_wmem_max': "net.core.wmem_max"
            }
            for label, oid in targets.items():
                try:
                    val = subprocess.check_output(["sysctl", "-n", oid], stderr=subprocess.DEVNULL).decode().strip()
                    buffers[label] = val
                except:
                    buffers[label] = "Not found"
        elif system == "Darwin":
            targets = {
                'tcp_sendspace': "net.inet.tcp.sendspace",
                'tcp_recvspace': "net.inet.tcp.recvspace",
                'maxsockbuf': "kern.ipc.maxsockbuf"
            }
            for label, oid in targets.items():
                try:
                    val = subprocess.check_output(["sysctl", "-n", oid], stderr=subprocess.DEVNULL).decode().strip()
                    buffers[label] = val
                except:
                    buffers[label] = "Not found"
    except Exception as e:
        return {"error": str(e)}
    return buffers

def get_congestion_control():
    """혼잡제어 알고리즘 확인"""
    try:
        if platform.system() == "Linux":
            cc = subprocess.check_output(["sysctl", "-n", "net.ipv4.tcp_congestion_control"], stderr=subprocess.DEVNULL).decode().strip()
            return f"{Colors.OKCYAN}{cc}{Colors.ENDC}"
        elif platform.system() == "Darwin":
            for oid in ["net.inet.tcp.cc_algo", "net.inet.tcp.available_congestion_control"]:
                try:
                    cc = subprocess.check_output(["sysctl", "-n", oid], stderr=subprocess.DEVNULL).decode().strip()
                    if cc: return f"{Colors.OKCYAN}{cc}{Colors.ENDC}"
                except:
                    continue
            return f"{Colors.OKCYAN}Default (Cubic/NewReno){Colors.ENDC}"
    except Exception:
        return f"{Colors.OKCYAN}Unknown{Colors.ENDC}"
    return "Unknown"

def get_cpu_governor():
    """CPU Governor 확인 (Linux 위주)"""
    if platform.system() != "Linux":
        return f"{Colors.OKBLUE}N/A (macOS Power Management){Colors.ENDC}"
    try:
        governors = set()
        for i in range(os.cpu_count() or 1):
            path = f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor"
            if os.path.exists(path):
                with open(path, 'r') as f:
                    governors.add(f.read().strip())
        if not governors:
            return "Governor info not found"
        res = ", ".join(governors)
        if "performance" in res:
            return f"{Colors.OKGREEN}{res}{Colors.ENDC}"
        return f"{Colors.WARNING}{res}{Colors.ENDC}"
    except Exception as e:
        return f"Error: {e}"
