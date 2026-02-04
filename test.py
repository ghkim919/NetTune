import platform
import subprocess
from utils import Colors, Messenger

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
        Messenger.error("IPERF3_NOT_FOUND")
        print(f"    - macOS: brew install iperf3")
        print(f"    - Ubuntu/Debian: sudo apt install iperf3")
        print(f"    - CentOS/RHEL: sudo yum install iperf3")
        return

    print(f"\n{Colors.BOLD}{Colors.OKCYAN}📊 iperf3 네트워크 속도 측정{Colors.ENDC}")
    server_ip = input(f" {Colors.BOLD}접속할 iperf3 서버 주소를 입력하세요 (기본: iperf.he.net) > {Colors.ENDC}").strip()
    if not server_ip:
        server_ip = "iperf.he.net"
    
    print(f" {Colors.OKBLUE}🔍 {server_ip} 서버에 연결 중... (최대 10초 대기){Colors.ENDC}")
    try:
        output = subprocess.check_output(
            ["iperf3", "-c", server_ip, "-t", "5", "--connect-timeout", "5000"],
            stderr=subprocess.STDOUT,
            timeout=15
        ).decode()
        
        for line in output.splitlines():
            if "receiver" in line:
                Messenger.success("MEASURE_SUCCESS")
                print(f"    - 결과: {Messenger.highlight(line.strip())}")
                break
        else:
            print(f"\n {Colors.WARNING}⚠️ 측정은 완료되었으나 요약 정보를 파싱하지 못했습니다.{Colors.ENDC}")
            print(output)
            
    except subprocess.TimeoutExpired:
        Messenger.error(f"시간 초과: {server_ip} 서버로부터 응답이 없습니다.")
    except subprocess.CalledProcessError as e:
        Messenger.error(f"연결 실패: {server_ip} 서버로 접근할 수 없습니다.")
        error_msg = e.output.decode() if e.output else str(e)
        print(f"    - 상세 에러: {error_msg.strip()}")
    except Exception as e:
        Messenger.error(f"예상치 못한 에러 발생: {e}")

def measure_rtt(target):
    """실시간 핑 측정을 통한 평균 RTT 추출"""
    print(f" {Colors.OKBLUE}🔍 {target} 서버로 경로 품질(RTT) 측정 중...{Colors.ENDC}")
    try:
        count = 4
        if platform.system() == "Darwin":
            cmd = ["ping", "-c", str(count), "-t", "2", target]
        else:
            cmd = ["ping", "-c", str(count), "-W", "2", target]
            
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
        
        for line in output.splitlines():
            if "min/avg/max" in line:
                stats = line.split("=")[1].strip().split("/")
                avg_rtt = float(stats[1])
                return avg_rtt
    except Exception:
        return None
    return None

def run_precision_bdp_calculator():
    """정밀 BDP(Bandwidth-Delay Product) 계산기 인터페이스"""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}🗺️ 정밀 BDP(Bandwidth-Delay Product) 계산기{Colors.ENDC}")
    
    print(f"\n {Colors.BOLD}1) 측정 대상 선택{Colors.ENDC}")
    print("   [1] 직접 IP/도메인 입력 (실시간 측정)")
    print("   [2] 주요 지역 평균값 사용")
    
    while True:
        sub_choice = input(f"\n {Colors.BOLD}선택 > {Colors.ENDC}").strip()
        if sub_choice in ['1', '2']:
            break
        Messenger.error("INVALID_INPUT")
    
    rtt = 0
    if sub_choice == '1':
        target = input(f" {Colors.BOLD}대상 IP 또는 도메인 입력 (기본: 8.8.8.8) > {Colors.ENDC}").strip()
        if not target: target = "8.8.8.8"
        avg_rtt = measure_rtt(target)
        if avg_rtt:
            Messenger.success(f"측정된 평균 RTT: {avg_rtt} ms")
            rtt = avg_rtt
        else:
            Messenger.error("핑 측정에 실패했습니다. 기본값 100ms를 사용합니다.")
            rtt = 100
    else:
        print(f"\n {Colors.BOLD}지역 선택{Colors.ENDC}")
        rtt_map = {'1': 10, '2': 140, '3': 200, '4': 260}
        print("   1. 국내: ~10ms / 2. 미서부: ~140ms / 3. 미동부: ~200ms / 4. 유럽: ~260ms")
        while True:
            reg_choice = input(f" {Colors.BOLD}선택 > {Colors.ENDC}").strip()
            if reg_choice in rtt_map:
                rtt = rtt_map[reg_choice]
                break
    
    while True:
        bw_input = input(f" {Colors.BOLD}대역폭 (Gbps 단위, 기본: 10) > {Colors.ENDC}").strip()
        if not bw_input:
            bandwidth_gbps = 10.0
            break
        try:
            bandwidth_gbps = float(bw_input)
            if bandwidth_gbps > 0: break
        except ValueError:
            pass

    bdp_bytes = int((bandwidth_gbps * 10**9 * (rtt / 1000.0)) / 8)
    bdp_mb = bdp_bytes / (1024 * 1024)

    print(f"\n{Colors.BOLD}{Colors.HEADER}📊 정밀 계산 결과{Colors.ENDC}")
    print(f" ┌────────────────────────────────────────────────────────┐")
    print(f" │  목표 대역폭     : {Colors.BOLD}{bandwidth_gbps:>10} Gbps{Colors.ENDC}                    │")
    print(f" │  지연시간(RTT)   : {Colors.BOLD}{rtt:>10} ms{Colors.ENDC}                      │")
    print(f" │  {Colors.OKGREEN}최적 TCP 버퍼   : {Colors.BOLD}{bdp_mb:>10.2f} MB{Colors.ENDC} ({bdp_bytes} bytes) │")
    print(f" └────────────────────────────────────────────────────────┘")
    input("\n메뉴로 돌아가려면 [Enter]를 누르세요...")
