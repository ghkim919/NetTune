import os
import sys
import subprocess
import platform
import psutil

def get_default_interface():
    """외부 망으로 나가는 기본 네트워크 인터페이스 식별"""
    try:
        if platform.system() == "Darwin":
            # macOS: route -n get default
            output = subprocess.check_output(["route", "-n", "get", "default"]).decode()
            for line in output.splitlines():
                if "interface:" in line:
                    return line.split(":")[1].strip()
        else:
            # Linux: ip route show default
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

# ANSI Color Codes
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

def get_physical_speed(interface):
    """물리 속도 체크 (ethtool 또는 networksetup/ifconfig)"""
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
    """TCP/IP 버퍼 사이즈 추출 (Linux 및 macOS 범용)"""
    buffers = {}
    try:
        system = platform.system()
        if system == "Linux":
            # 리눅스는 거의 모든 배포판(CentOS, Ubuntu 등)이 동일한 경로를 사용합니다.
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
                    
        elif system == "Darwin": # macOS
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
    """혼잡제어 알고리즘 확인 (에러 메세지 노출 방지)"""
    try:
        if platform.system() == "Linux":
            cc = subprocess.check_output(["sysctl", "-n", "net.ipv4.tcp_congestion_control"], stderr=subprocess.DEVNULL).decode().strip()
            return f"{Colors.OKCYAN}{cc}{Colors.ENDC}"
        elif platform.system() == "Darwin":
            # macOS에서 cc_algo OID가 없는 경우가 있으므로 여러 후보를 확인
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

def calculate_guidelines():
    """메모리 기반 네트워크 버퍼 가이드라인 계산"""
    total_mem = psutil.virtual_memory().total
    total_mem_gb = total_mem / (1024**3)
    
    if total_mem_gb < 16:
        suggested_mb = 64
    elif total_mem_gb < 64:
        suggested_mb = 128
    else:
        suggested_mb = 512
        
    suggested_bytes = suggested_mb * 1024 * 1024
    limit_bytes = int(total_mem * 0.05)
    if suggested_bytes > limit_bytes:
        suggested_bytes = limit_bytes
        suggested_mb = suggested_bytes / (1024 * 1024)
    
    return {
        "total_memory_gb": round(total_mem_gb, 2),
        "suggested_max_buffer_bytes": suggested_bytes,
        "suggested_max_buffer_mb": round(suggested_mb, 2)
    }

def show_explanations():
    """각 진단 항목에 대한 상세 설명 출력"""
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}┌────────────────── 각 항목에 대한 상세 설명 ──────────────────┐{Colors.ENDC}")
    
    explanations = [
        ("🌐 외부 인터페이스", "인터넷과 연결된 실제 통로입니다. 여러 개의 랜카드가 있을 때\n                       어떤 장치를 통해 데이터가 나가는지 확인합니다."),
        ("⚡ 물리 속도", "랜카드와 케이블이 지원하는 '최대 대역폭'입니다.\n                       1Gbps망인데 100Mbps로 잡혀있다면 케이블 등을 점검해야 합니다."),
        ("📦 MTU", "데이터를 보낼 때 한 번에 담는 상자의 크기입니다.\n                       기본은 1500이며, 고속망에서는 9000(점보 프레임)으로 키우면 효율이 좋아집니다."),
        ("🛠️ TCP/IP 버퍼", "데이터 전송 중 임시로 저장되는 장소입니다. 고속망에서 이 공간이\n                       너무 작으면 데이터 손실이 발생하여 속도가 급격히 떨어집니다."),
        ("⚖️ 혼잡제어 알고리즘", "네트워크가 혼잡할 때 전송 속도를 조절하는 '교통 경찰' 역할입니다.\n                       BBR과 같은 현대적 알고리즘은 장거리 전송 시 속도를 크게 높여줍니다."),
        ("📝 튜닝 가이드라인", "사용자의 메모리 용량에 맞춰, 시스템이 감당할 수 있으면서도\n                       최상의 속도를 낼 수 있는 최적의 버퍼 크기를 계산해 드립니다."),
        ("⚙️ CPU Governor", "CPU의 성능 모드입니다. 'PowerSave' 모드일 경우 데이터 처리가 지연될 수\n                       있으므로 'Performance' 모드 사용을 권장합니다.")
    ]
    
    for title, desc in explanations:
        print(f"  {Colors.BOLD}{title}{Colors.ENDC}")
        print(f"    {desc}\n")
    
    print(f"{Colors.BOLD}{Colors.OKBLUE}└──────────────────────────────────────────────────────────────┘{Colors.ENDC}")
    input("\n메뉴로 돌아가려면 [Enter]를 누르세요...")

def check_iperf3_installed():
    """iperf3 설치 여부 확인"""
    try:
        subprocess.check_output(["iperf3", "--version"], stderr=subprocess.STDOUT)
        return True
    except:
        return False

def run_iperf_test():
    """iperf3 속도 측정 측정"""
    if not check_iperf3_installed():
        print(f"\n {Colors.FAIL}❌ iperf3가 설치되어 있지 않습니다.{Colors.ENDC}")
        print(f"    - macOS: brew install iperf3")
        print(f"    - Ubuntu/Debian: sudo apt install iperf3")
        print(f"    - CentOS/RHEL: sudo yum install iperf3")
        return

    print(f"\n{Colors.BOLD}{Colors.OKCYAN}📊 iperf3 네트워크 속도 측정{Colors.ENDC}")
    server_ip = input(f" {Colors.BOLD}접속할 iperf3 서버 주소를 입력하세요 (기본: iperf.he.net) > {Colors.ENDC}").strip()
    if not server_ip:
        server_ip = "iperf.he.net"
    
    print(f" {Colors.OKBLUE}🔍 {server_ip} 서버에 연결 중... (10초간 측정){Colors.ENDC}")
    try:
        # -t 10 (10초), -c (client mode)
        output = subprocess.check_output(["iperf3", "-c", server_ip, "-t", "5"], stderr=subprocess.STDOUT).decode()
        
        # 결과 요약 파싱 (간단히 마지막 전송률만 추출)
        for line in output.splitlines():
            if "receiver" in line:
                print(f"\n {Colors.BOLD}{Colors.OKGREEN}✅ 측정 완료!{Colors.ENDC}")
                print(f"    - 결과: {Colors.BOLD}{line.strip()}{Colors.ENDC}")
                break
        else:
            print(f"\n {Colors.WARNING}⚠️ 측정은 완료되었으나 요약 정보를 파싱하지 못했습니다.{Colors.ENDC}")
            print(output)
            
    except Exception as e:
        print(f"\n {Colors.FAIL}❌ 에러 발생: {e}{Colors.ENDC}")
        print(f"    - 서버 주소가 정확한지, 혹은 서버가 iperf3 -s로 실행 중인지 확인하세요.")

def run_diagnosis():
    """기존 진단 로직 실행"""
    print("\n" + f"{Colors.BOLD}{Colors.HEADER}╔════════════════════════════════════════════════════════════╗")
    print(f"║   🚀 [NetTune] 고속 네트워크 환경 진단 및 튜닝 가이드    ║")
    print(f"╚════════════════════════════════════════════════════════════╝{Colors.ENDC}")
    
    # 1. 인터페이스 식별
    iface = get_default_interface()
    print(f"\n {Colors.BOLD}1. 🌐 외부 인터페이스{Colors.ENDC}    : {Colors.OKBLUE}{iface}{Colors.ENDC}")
    
    if iface != "Not Found" and "Error" not in iface:
        # 2. 물리 속도
        speed = get_physical_speed(iface)
        print(f" {Colors.BOLD}2. ⚡ 물리 속도 (Media){Colors.ENDC}  : {speed}")
        
        # 3. MTU
        mtu = get_mtu(iface)
        try:
            mtu_val = int(mtu)
            mtu_display = f"{Colors.OKGREEN}{mtu}{Colors.ENDC}" if mtu_val >= 9000 else f"{Colors.WARNING}{mtu}{Colors.ENDC}"
        except:
            mtu_display = mtu
        print(f" {Colors.BOLD}3. 📦 MTU 설정값{Colors.ENDC}         : {mtu_display}")
        if mtu == "1500":
            print(f"    {Colors.WARNING}💡 Tip: 고속망(Jumbo Frame) 사용 시 9000 설정을 권장합니다.{Colors.ENDC}")
    
    # 4. TCP 버퍼 사이즈
    print(f"\n {Colors.BOLD}4. 🛠️ TCP/IP 버퍼 설정{Colors.ENDC}")
    buffers = get_tcp_buffers()
    for k, v in buffers.items():
        print(f"    - {k:20}: {Colors.OKCYAN}{v}{Colors.ENDC}")
        
    # 5. 혼잡제어 알고리즘
    cc = get_congestion_control()
    print(f"\n {Colors.BOLD}5. ⚖️ 혼잡제어 알고리즘{Colors.ENDC}  : {cc}")
    if platform.system() == "Linux" and cc and "cubic" in cc.lower():
        print(f"    {Colors.WARNING}💡 Tip: 장거리 고속 전송 시 'bbr' 사용을 권장합니다.{Colors.ENDC}")
    
    # 6. 메모리 기반 가이드라인
    guide = calculate_guidelines()
    print(f"\n {Colors.BOLD}6. 📝 튜닝 가이드라인{Colors.ENDC}")
    print(f"    ┌────────────────────────────────────────────────────────┐")
    print(f"    │  시스템 총 메모리 : {Colors.BOLD}{guide['total_memory_gb']:>6} GB{Colors.ENDC}                      │")
    print(f"    │  권장 최대 버퍼   : {Colors.OKGREEN}{Colors.BOLD}{guide['suggested_max_buffer_mb']:>6} MB{Colors.ENDC} ({guide['suggested_max_buffer_bytes']} bytes)   │")
    print(f"    └────────────────────────────────────────────────────────┘")
    print(f"    * 10Gbps+ 환경에서는 BDP 확보를 위해 위 수준의 확장이 필요합니다.")
    
    # 7. CPU Governor
    gov = get_cpu_governor()
    print(f"\n {Colors.BOLD}7. ⚙️ CPU Governor{Colors.ENDC}       : {gov}")
    if "powersave" in gov.lower():
        print(f"    {Colors.FAIL}⚠️ 경고: 'powersave' 모드는 성능 저하의 원인이 됩니다.{Colors.ENDC}")
        print(f"    {Colors.OKGREEN}👉 권장: sudo cpupower frequency-set -g performance{Colors.ENDC}")

    # iperf3 속도 테스트 수행 여부 확인
    print(f"\n {Colors.BOLD}8. 📊 실시간 속도 측정 (Optional){Colors.ENDC}")
    do_iperf = input(f"    iperf3를 사용하여 속도 측정을 수행하시겠습니까? (y/n) > ").strip().lower()
    if do_iperf == 'y':
        run_iperf_test()

    print("\n" + f"{Colors.OKBLUE}============================================================{Colors.ENDC}\n")
    input("메뉴로 돌아가려면 [Enter]를 누르세요...")

def main():
    while True:
        # OS 터미널 클리어 (선택 사항이나 깔끔하게 보이기 위해 사용)
        # os.system('cls' if os.name == 'nt' else 'clear')
        
        print(f"\n{Colors.BOLD}{Colors.HEADER}   [ NetTune: 네트워크 최적화 도구 ]{Colors.ENDC}")
        print(f"   1. {Colors.OKGREEN}네트워크 진단 시작{Colors.ENDC}")
        print(f"   2. {Colors.OKCYAN}각 진단 항목에 대한 설명 보기{Colors.ENDC}")
        print(f"   q. 종료")
        
        choice = input(f"\n {Colors.BOLD}입력하세요 > {Colors.ENDC}").strip().lower()
        
        if choice == '1':
            run_diagnosis()
        elif choice == '2':
            show_explanations()
        elif choice == 'q':
            print(f"\n{Colors.OKBLUE}프로그램을 종료합니다. 감사합니다!{Colors.ENDC}\n")
            break
        else:
            print(f"{Colors.FAIL}잘못된 입력입니다. 다시 시도해 주세요.{Colors.ENDC}")

if __name__ == "__main__":
    main()
