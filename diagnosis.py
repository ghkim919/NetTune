import platform
import psutil
from utils import Colors, get_default_interface, get_all_interfaces, get_physical_speed, get_mtu, get_tcp_buffers, get_congestion_control, get_cpu_governor

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
        ("🌐 외부 인터페이스", "분석 대상으로 선택된 네트워크 장치입니다."),
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

def select_interface():
    """사용자로부터 진단할 인터페이스 선택 받기"""
    interfaces = get_all_interfaces()
    default_iface = get_default_interface()
    
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}📋 사용 가능한 네트워크 인터페이스 목록:{Colors.ENDC}")
    print(f"    {'No.':<4} {'이름':<15} {'IP 주소':<15} {'상태':<6} {'비고'}")
    print("    " + "-" * 55)
    
    for i, iface in enumerate(interfaces, 1):
        is_default = "*" if iface['name'] == default_iface else " "
        note = f"{Colors.OKGREEN}(기본){Colors.ENDC}" if iface['name'] == default_iface else ""
        print(f"    {is_default}{i:<3} {iface['name']:<15} {iface['ip']:<15} {iface['status']:<6} {note}")
    
    while True:
        try:
            choice = input(f"\n{Colors.BOLD}진단할 인터페이스 번호를 선택하세요 (기본값: {default_iface}) > {Colors.ENDC}").strip()
            if not choice:
                return default_iface
            
            idx = int(choice) - 1
            if 0 <= idx < len(interfaces):
                return interfaces[idx]['name']
            else:
                print(f"{Colors.FAIL}❌ 범위를 벗어난 번호입니다.{Colors.ENDC}")
        except ValueError:
            print(f"{Colors.FAIL}❌ 숫자를 입력해주세요.{Colors.ENDC}")

def run_diagnosis():
    """진단 로직 실행"""
    iface = select_interface()
    
    print("\n" + f"{Colors.BOLD}{Colors.HEADER}╔════════════════════════════════════════════════════════════╗")
    print(f"║   🚀 [NetTune] {iface:^10} 인터페이스 진단 결과      ║")
    print(f"╚════════════════════════════════════════════════════════════╝{Colors.ENDC}")
    
    print(f"\n {Colors.BOLD}1. 🌐 선택된 인터페이스{Colors.ENDC}  : {Colors.OKBLUE}{iface}{Colors.ENDC}")
    
    if iface != "Not Found" and "Error" not in iface:
        speed = get_physical_speed(iface)
        print(f" {Colors.BOLD}2. ⚡ 물리 속도 (Media){Colors.ENDC}  : {speed}")
        
        mtu = get_mtu(iface)
        try:
            mtu_val = int(mtu)
            mtu_display = f"{Colors.OKGREEN}{mtu}{Colors.ENDC}" if mtu_val >= 9000 else f"{Colors.WARNING}{mtu}{Colors.ENDC}"
        except:
            mtu_display = mtu
        print(f" {Colors.BOLD}3. 📦 MTU 설정값{Colors.ENDC}         : {mtu_display}")
        if mtu == "1500":
            print(f"    {Colors.WARNING}💡 Tip: 고속망(Jumbo Frame) 사용 시 9000 설정을 권장합니다.{Colors.ENDC}")
    
    print(f"\n {Colors.BOLD}4. 🛠️ TCP/IP 버퍼 설정{Colors.ENDC}")
    buffers = get_tcp_buffers()
    for k, v in buffers.items():
        v_display = f"{v} bytes" if v != "Not found" else v
        print(f"    - {k:20}: {Colors.OKCYAN}{v_display}{Colors.ENDC}")
        
    cc = get_congestion_control()
    print(f"\n {Colors.BOLD}5. ⚖️ 혼잡제어 알고리즘{Colors.ENDC}  : {cc}")
    if platform.system() == "Linux" and cc and "cubic" in cc.lower():
        print(f"    {Colors.WARNING}💡 Tip: 장거리 고속 전송 시 'bbr' 사용을 권장합니다.{Colors.ENDC}")
    
    guide = calculate_guidelines()
    print(f"\n {Colors.BOLD}6. 📝 튜닝 가이드라인{Colors.ENDC}")
    print(f"    ┌────────────────────────────────────────────────────────┐")
    print(f"    │  시스템 총 메모리 : {Colors.BOLD}{guide['total_memory_gb']:>6} GB{Colors.ENDC}                      │")
    print(f"    │  권장 최대 버퍼   : {Colors.OKGREEN}{Colors.BOLD}{guide['suggested_max_buffer_mb']:>6} MB{Colors.ENDC} ({guide['suggested_max_buffer_bytes']} bytes)   │")
    print(f"    └────────────────────────────────────────────────────────┘")
    print(f"    * 10Gbps+ 환경에서는 BDP 확보를 위해 위 수준의 확장이 필요합니다.")
    
    gov = get_cpu_governor()
    print(f"\n {Colors.BOLD}7. ⚙️ CPU Governor{Colors.ENDC}       : {gov}")
    if "powersave" in gov.lower():
        print(f"    {Colors.FAIL}⚠️ 경고: 'powersave' 모드는 성능 저하의 원인이 됩니다.{Colors.ENDC}")
        if platform.system() == "Linux":
            print(f"    {Colors.OKGREEN}👉 권장: sudo cpupower frequency-set -g performance{Colors.ENDC}")

    print("\n" + f"{Colors.OKBLUE}============================================================{Colors.ENDC}\n")
    input("진단 결과 확인 완료 [Enter]를 누르면 메뉴에 진입합니다...")
