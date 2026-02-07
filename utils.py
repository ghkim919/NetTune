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

class Messenger:
    """메시지 출력 관리 클래스"""
    
    # 공통 메시지 정의
    MESSAGES = {
        "INVALID_INPUT": "잘못된 입력입니다. 다시 시도해 주세요.",
        "EXIT_APP": "프로그램을 종료합니다. 감사합니다!",
        "CANCELLED": "취소되었습니다.",
        "FILE_NOT_FOUND": "파일을 찾을 수 없습니다.",
        "SUCCESS_BACKUP": "설정 백업 성공!",
        "SUCCESS_DELETE": "설정 파일이 삭제되었습니다.",
        "SUCCESS_RESTORE": "설정 복원이 완료되었습니다!",
        "SUCCESS_TUNING": "최적화 설정이 완료되었습니다!",
        "ERROR_SAVE": "저장 중 오류 발생",
        "ERROR_READ": "파일 읽기 오류",
        "ERROR_DELETE": "파일 삭제 중 오류 발생",
        "ERROR_RESTORE": "일부 설정 복원에 실패했습니다.",
        "OS_NOT_SUPPORTED": "지원하지 않는 OS입니다",
        "FEATURE_COMING_SOON": "해당 기능은 현재 준비 중입니다.",
        "SUDO_REQUIRED": "이 명령은 sudo 권한이 필요할 수 있습니다.",
        "CONFIRM_APPLY": "설정을 적용하시겠습니까?",
        "CONFIRM_DELETE": "정말로 삭제하시겠습니까?",
        "CONFIRM_RESET": "표준 기본값으로 초기화하시겠습니까?",
        "OUT_OF_RANGE": "범위를 벗어난 번호입니다.",
        "REQUIRE_NUMBER": "숫자를 입력해주세요.",
        "IPERF3_NOT_FOUND": "iperf3가 설치되어 있지 않습니다.",
        "MEASURE_SUCCESS": "측정 완료!"
    }

    @staticmethod
    def _print(icon, msg, color, bold=False):
        style = color + (Colors.BOLD if bold else "")
        print(f"{style}{icon} {msg}{Colors.ENDC}")

    @staticmethod
    def success(key_or_msg, bold=True):
        msg = Messenger.MESSAGES.get(key_or_msg, key_or_msg)
        Messenger._print("✅", msg, Colors.OKGREEN, bold)

    @staticmethod
    def error(key_or_msg, bold=True):
        msg = Messenger.MESSAGES.get(key_or_msg, key_or_msg)
        Messenger._print("❌", msg, Colors.FAIL, bold)

    @staticmethod
    def warn(key_or_msg, bold=False):
        msg = Messenger.MESSAGES.get(key_or_msg, key_or_msg)
        Messenger._print("⚠️", msg, Colors.WARNING, bold)

    @staticmethod
    def info(key_or_msg, bold=False):
        msg = Messenger.MESSAGES.get(key_or_msg, key_or_msg)
        Messenger._print("ℹ️", msg, Colors.OKCYAN, bold)

    @staticmethod
    def highlight(msg):
        return f"{Colors.BOLD}{msg}{Colors.ENDC}"

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
                'core_wmem_max': "net.core.wmem_max",
                'tcp_mtu_probing': "net.ipv4.tcp_mtu_probing",
                'default_qdisc': "net.core.default_qdisc",
                'optmem_max': "net.core.optmem_max",
                'tcp_no_metrics_save': "net.ipv4.tcp_no_metrics_save",
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
                'maxsockbuf': "kern.ipc.maxsockbuf",
                'autorcvbufmax': "net.inet.tcp.autorcvbufmax",
                'autosndbufmax': "net.inet.tcp.autosndbufmax",
                'win_scale_factor': "net.inet.tcp.win_scale_factor"
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
