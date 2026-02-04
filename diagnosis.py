import platform
import psutil
from utils import Colors, Messenger, get_default_interface, get_all_interfaces, get_physical_speed, get_mtu, get_tcp_buffers, get_congestion_control, get_cpu_governor

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
    """각 진단 항목에 대한 상세 설명 및 튜닝 가이드 정보 출력"""
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}┌──────────────────────────────────────────────────────────────┐{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}│              🌐 NetTune 네트워크 기술 가이드              │{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}└──────────────────────────────────────────────────────────────┘{Colors.ENDC}")
    
    explanations = [
        ("⚡ 물리 속도 (Link Speed)", 
         "현재 OS가 인식하는 랜카드의 물리적 연결 속도입니다.\n"
         "      - 1Gbps 환경에서 100Mbps로 표시된다면 케이블(Cat.5e 이상 필수)이나\n"
         "        스위치 포트 불량을 의심해 봐야 합니다."),
        
        ("📦 MTU (Maximum Transmission Unit)", 
         "한 번의 프레임에 담을 수 있는 최대 데이터 크기(기본 1500)입니다.\n"
         "      - 고속망(10G+)에서는 9000(Jumbo Frame)으로 설정 시 헤더 오버헤드를\n"
         "        줄여 CPU 부하를 낮추고 실제 전송 효율을 극대화합니다."),
        
        ("🛠️ TCP/IP 버퍼 (Window Size & BDP)", 
         "전송 중인 데이터를 임시 보관하는 메모리 공간입니다.\n"
         "      - BDP(대역폭 x 지연시간)만큼의 공간이 확보되어야 끊김 없는 전송이 가능합니다.\n"
         "      - macOS: sendspace/recvspace는 초기 크기, maxbuf는 최대 한계치를 의미합니다.\n"
         "      - Linux: min/default/max 3단계로 관리되며 대역폭에 맞춰 max 확장이 필수입니다."),
        
        ("⚖️ 혼잡제어 알고리즘 (Congestion Control)", 
         "네트워크 혼잡 시 전송 속도를 지능적으로 조절하는 로직입니다.\n"
         "      - Cubic: 고전적인 표준 기반 알고리즘 (대부분의 OS 기본값)\n"
         "      - BBR: Google 개발 알고리즘. 패킷 손실이 잦은 장거리(LFN) 망에서\n"
         "             압도적인 속도 향상을 보여줍니다."),
        
        ("📝 튜닝 가이드라인 (NetTune Recommendation)", 
         "현재 시스템의 RAM 용량을 분석하여 최적의 버퍼 크기를 제안합니다.\n"
         "      - 너무 작으면 속도가 제한되고, 너무 크면 시스템 메모리가 고갈될 수 있습니다.\n"
         "      - NetTune은 전체 메모리의 5% 이내에서 최적의 안정 수치를 계산합니다."),
        
        ("⚙️ CPU Governor (Power Management)", 
         "CPU의 동작 클럭 전략입니다.\n"
         "      - Performance: 성능 우선. 네트워크 패킷 처리 지연(Latency)을 최소화합니다.\n"
         "      - PowerSave: 전력 저감. 대량의 패킷 처리 시 병목이 발생할 수 있습니다.")
    ]
    
    for title, desc in explanations:
        print(f"\n  {Colors.BOLD}{Colors.OKCYAN}▶ {title}{Colors.ENDC}")
        print(f"    {desc}")
    
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}────────────────────────────────────────────────────────────────{Colors.ENDC}")
    print(f" {Colors.BOLD}💡 주의: 현재 NetTune에서 적용하는 설정은 '실시간 반영'용이며,{Colors.ENDC}")
    print(f" {Colors.BOLD}    재부팅 시 초기화됩니다. 영구 반영을 위해서는 Linux의 경우{Colors.ENDC}")
    print(f" {Colors.BOLD}    /etc/sysctl.conf 등에 해당 설정을 추가해야 합니다.{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}────────────────────────────────────────────────────────────────{Colors.ENDC}")
    
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
                Messenger.error("OUT_OF_RANGE")
        except ValueError:
            Messenger.error("REQUIRE_NUMBER")

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
