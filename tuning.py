import platform
import subprocess
from utils import Colors, Messenger, get_all_interfaces, get_default_interface
import config_manager
from diagnosis import calculate_guidelines

def run_sysctl_command(oid, value):
    """sudo sysctl -w 명령 실행"""
    cmd = ["sudo", "sysctl", "-w", f"{oid}={value}"]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"    {Colors.OKGREEN}✔{Colors.ENDC} {oid} -> {value} {Colors.OKBLUE}(성공){Colors.ENDC}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    {Colors.FAIL}✘{Colors.ENDC} {oid} 설정 실패: {e.stderr.strip()}")
        return False

def run_ethtool_command(interface, *args):
    """sudo ethtool 명령 실행"""
    cmd = ["sudo", "ethtool"] + list(args) + [interface]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"    {Colors.OKGREEN}✔{Colors.ENDC} ethtool {' '.join(args)} {interface} {Colors.OKBLUE}(성공){Colors.ENDC}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    {Colors.FAIL}✘{Colors.ENDC} ethtool 명령 실패: {e.stderr.strip()}")
        return False

def run_tc_command(*args):
    """sudo tc 명령 실행"""
    cmd = ["sudo", "tc"] + list(args)
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"    {Colors.OKGREEN}✔{Colors.ENDC} tc {' '.join(args)} {Colors.OKBLUE}(성공){Colors.ENDC}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    {Colors.FAIL}✘{Colors.ENDC} tc 명령 실패: {e.stderr.strip()}")
        return False

def run_modprobe(module):
    """sudo modprobe 명령 실행"""
    cmd = ["sudo", "modprobe", module]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"    {Colors.OKGREEN}✔{Colors.ENDC} modprobe {module} {Colors.OKBLUE}(성공){Colors.ENDC}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    {Colors.FAIL}✘{Colors.ENDC} modprobe {module} 실패: {e.stderr.strip()}")
        return False

def _select_interface():
    """튜닝 적용할 네트워크 인터페이스 선택"""
    interfaces = get_all_interfaces()
    default_iface = get_default_interface()

    print(f"\n{Colors.BOLD}{Colors.OKCYAN}📋 사용 가능한 네트워크 인터페이스:{Colors.ENDC}")
    print(f"    {'No.':<4} {'이름':<15} {'IP 주소':<15} {'상태':<6} {'비고'}")
    print("    " + "-" * 55)

    for i, iface in enumerate(interfaces, 1):
        note = f"{Colors.OKGREEN}(기본){Colors.ENDC}" if iface['name'] == default_iface else ""
        print(f"    {i:<4} {iface['name']:<15} {iface['ip']:<15} {iface['status']:<6} {note}")

    while True:
        try:
            choice = input(f"\n{Colors.BOLD}인터페이스 번호 선택 (기본값: {default_iface}) > {Colors.ENDC}").strip()
            if not choice:
                return default_iface
            idx = int(choice) - 1
            if 0 <= idx < len(interfaces):
                return interfaces[idx]['name']
            else:
                Messenger.error("OUT_OF_RANGE")
        except ValueError:
            Messenger.error("REQUIRE_NUMBER")

def _apply_sysctl_settings(settings):
    """sysctl 설정 딕셔너리를 일괄 적용"""
    config_manager.save_config("bk")
    print(f"\n{Colors.BOLD}🛠️ 설정 적용 중...{Colors.ENDC}")
    success = True
    for oid, val in settings.items():
        success &= run_sysctl_command(oid, val)
    if success:
        Messenger.success("SUCCESS_TUNING")
    Messenger.warn("설정이 즉시 반영되었으나, 재부팅 시 초기화됩니다.", bold=False)
    Messenger.info("영구 반영: /etc/sysctl.conf 에 해당 설정을 추가하세요.", bold=False)
    input("\n계속하려면 [Enter]를 누르세요...")

def _apply_linux_general():
    """일반 호스트 TCP 버퍼 최적화"""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}📡 일반 호스트 튜닝 (TCP 버퍼 최적화){Colors.ENDC}")
    print(f"  [1] 10G NIC (RTT <= 100ms)")
    print(f"  [2] 10G (RTT <= 200ms) / 40G (RTT <= 50ms)")
    print(f"  [3] 100G NIC (RTT <= 200ms)")
    print(f"  [b] 뒤로 가기")

    choice = input(f"\n{Colors.BOLD}선택 > {Colors.ENDC}").strip().lower()

    presets = {
        '1': {
            "net.core.rmem_max": 67108864,
            "net.core.wmem_max": 67108864,
            "net.ipv4.tcp_rmem": "4096 87380 33554432",
            "net.ipv4.tcp_wmem": "4096 65536 33554432",
            "net.ipv4.tcp_mtu_probing": 1,
            "net.core.default_qdisc": "fq",
        },
        '2': {
            "net.core.rmem_max": 134217728,
            "net.core.wmem_max": 134217728,
            "net.ipv4.tcp_rmem": "4096 87380 67108864",
            "net.ipv4.tcp_wmem": "4096 65536 67108864",
            "net.ipv4.tcp_mtu_probing": 1,
            "net.core.default_qdisc": "fq",
        },
        '3': {
            "net.core.rmem_max": 2147483647,
            "net.core.wmem_max": 2147483647,
            "net.ipv4.tcp_rmem": "4096 131072 1073741824",
            "net.ipv4.tcp_wmem": "4096 16384 1073741824",
            "net.ipv4.tcp_mtu_probing": 1,
            "net.core.default_qdisc": "fq",
            "net.core.optmem_max": 1048576,
        },
    }

    if choice in presets:
        Messenger.warn("CONFIRM_APPLY", bold=True)
        confirm = input(f" {Colors.BOLD}(y/n) > {Colors.ENDC}").strip().lower()
        if confirm == 'y':
            _apply_sysctl_settings(presets[choice])

def _apply_linux_test_host():
    """테스트/측정 호스트 튜닝"""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}🧪 테스트/측정 호스트 튜닝{Colors.ENDC}")
    print(f"  [1] 일반 (10G, RTT <= 100ms)")
    print(f"  [2] 고지연 경로 (10G RTT <= 200ms / 40G RTT <= 50ms)")
    print(f"  [3] 초고속 (100G, RTT <= 200ms)")
    print(f"  [b] 뒤로 가기")

    choice = input(f"\n{Colors.BOLD}선택 > {Colors.ENDC}").strip().lower()

    presets = {
        '1': {
            "net.core.rmem_max": 268435456,
            "net.core.wmem_max": 268435456,
            "net.ipv4.tcp_rmem": "4096 87380 134217728",
            "net.ipv4.tcp_wmem": "4096 65536 134217728",
            "net.ipv4.tcp_no_metrics_save": 1,
            "net.ipv4.tcp_mtu_probing": 1,
            "net.core.default_qdisc": "fq",
        },
        '2': {
            "net.core.rmem_max": 536870912,
            "net.core.wmem_max": 536870912,
            "net.ipv4.tcp_rmem": "4096 87380 268435456",
            "net.ipv4.tcp_wmem": "4096 65536 268435456",
            "net.ipv4.tcp_no_metrics_save": 1,
            "net.ipv4.tcp_mtu_probing": 1,
            "net.core.default_qdisc": "fq",
        },
        '3': {
            "net.core.rmem_max": 2147483647,
            "net.core.wmem_max": 2147483647,
            "net.ipv4.tcp_rmem": "4096 65536 1073741824",
            "net.ipv4.tcp_wmem": "4096 65536 1073741824",
            "net.ipv4.tcp_no_metrics_save": 1,
            "net.ipv4.tcp_mtu_probing": 1,
            "net.core.default_qdisc": "fq",
            "net.core.optmem_max": 1048576,
        },
    }

    if choice in presets:
        Messenger.warn("CONFIRM_APPLY", bold=True)
        confirm = input(f" {Colors.BOLD}(y/n) > {Colors.ENDC}").strip().lower()
        if confirm == 'y':
            _apply_sysctl_settings(presets[choice])

def _apply_linux_100g_nic():
    """100G NIC 드라이버 최적화"""
    iface = _select_interface()

    print(f"\n{Colors.BOLD}{Colors.OKCYAN}⚙️ 100G NIC 드라이버 최적화 ({iface}){Colors.ENDC}")
    print(f"  [1] Ring Buffer 확장 (rx/tx 8192)")
    print(f"  [2] Adaptive Interrupt Coalescence 활성화")
    print(f"  [3] Flow Control 활성화 (rx/tx on)")
    print(f"  [4] CPU Governor -> performance 설정")
    print(f"  [5] SMT(Hyper-Threading) 비활성화 안내")
    print(f"  [a] 위 항목 모두 적용 (5번 제외)")
    print(f"  [b] 뒤로 가기")

    choice = input(f"\n{Colors.BOLD}선택 > {Colors.ENDC}").strip().lower()
    if choice == 'b':
        return

    Messenger.warn("SUDO_REQUIRED")
    print(f"\n{Colors.BOLD}🛠️ 설정 적용 중...{Colors.ENDC}")

    if choice in ['1', 'a']:
        run_ethtool_command(iface, "-G", "rx", "8192", "tx", "8192")
    if choice in ['2', 'a']:
        run_ethtool_command(iface, "-C", "adaptive-rx", "on", "adaptive-tx", "on")
    if choice in ['3', 'a']:
        run_ethtool_command(iface, "-A", "rx", "on", "tx", "on")
    if choice in ['4', 'a']:
        try:
            subprocess.run(
                ["sudo", "cpupower", "frequency-set", "-g", "performance"],
                check=True, capture_output=True, text=True
            )
            print(f"    {Colors.OKGREEN}✔{Colors.ENDC} CPU Governor -> performance {Colors.OKBLUE}(성공){Colors.ENDC}")
        except subprocess.CalledProcessError as e:
            print(f"    {Colors.FAIL}✘{Colors.ENDC} CPU Governor 설정 실패: {e.stderr.strip()}")
        except FileNotFoundError:
            print(f"    {Colors.FAIL}✘{Colors.ENDC} cpupower가 설치되어 있지 않습니다. (linux-tools 패키지 필요)")
    if choice == '5':
        print(f"\n{Colors.BOLD}{Colors.WARNING}📌 SMT(Hyper-Threading) 비활성화 안내:{Colors.ENDC}")
        print(f"  SMT 비활성화는 BIOS/UEFI 설정에서 수행해야 합니다.")
        print(f"  - 서버 재부팅 -> BIOS 진입 -> Processor 설정 -> Hyper-Threading 비활성화")
        print(f"  - 또는 커널 파라미터: nosmt=force (GRUB 설정)")

    input("\n계속하려면 [Enter]를 누르세요...")

def _apply_linux_packet_pacing():
    """패킷 페이싱 설정"""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}📦 패킷 페이싱 설정{Colors.ENDC}")
    print(f"  [1] fq qdisc 활성화 (sysctl)")
    print(f"  [2] 인터페이스별 maxrate 설정 (tc)")
    print(f"  [3] 현재 qdisc 설정 확인")
    print(f"  [b] 뒤로 가기")

    choice = input(f"\n{Colors.BOLD}선택 > {Colors.ENDC}").strip().lower()

    if choice == '1':
        Messenger.warn("CONFIRM_APPLY", bold=True)
        confirm = input(f" {Colors.BOLD}(y/n) > {Colors.ENDC}").strip().lower()
        if confirm == 'y':
            config_manager.save_config("bk")
            print(f"\n{Colors.BOLD}🛠️ 설정 적용 중...{Colors.ENDC}")
            run_sysctl_command("net.core.default_qdisc", "fq")
            input("\n계속하려면 [Enter]를 누르세요...")

    elif choice == '2':
        iface = _select_interface()
        rate = input(f"{Colors.BOLD}maxrate 입력 (Gbps 단위, 예: 10) > {Colors.ENDC}").strip()
        if not rate:
            Messenger.warn("CANCELLED")
            return
        try:
            float(rate)
        except ValueError:
            Messenger.error("REQUIRE_NUMBER")
            return
        Messenger.warn("CONFIRM_APPLY", bold=True)
        confirm = input(f" {Colors.BOLD}(y/n) > {Colors.ENDC}").strip().lower()
        if confirm == 'y':
            print(f"\n{Colors.BOLD}🛠️ 설정 적용 중...{Colors.ENDC}")
            run_tc_command("qdisc", "add", "dev", iface, "root", "fq", "maxrate", f"{rate}gbit")
            input("\n계속하려면 [Enter]를 누르세요...")

    elif choice == '3':
        iface = _select_interface()
        try:
            result = subprocess.run(
                ["tc", "qdisc", "show", "dev", iface],
                capture_output=True, text=True
            )
            print(f"\n{Colors.BOLD}현재 qdisc 설정 ({iface}):{Colors.ENDC}")
            print(f"  {result.stdout.strip() if result.stdout.strip() else '설정 없음'}")
        except Exception as e:
            Messenger.error(f"qdisc 확인 실패: {e}")
        input("\n계속하려면 [Enter]를 누르세요...")

def _apply_linux_udp():
    """UDP 튜닝"""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}📡 UDP 튜닝{Colors.ENDC}")
    print(f"  [1] UDP 소켓 버퍼 확장 (rmem_max/wmem_max -> 4MB)")
    print(f"  [2] Jumbo Frame (MTU 9000) 설정")
    print(f"  [b] 뒤로 가기")

    choice = input(f"\n{Colors.BOLD}선택 > {Colors.ENDC}").strip().lower()

    if choice == '1':
        Messenger.warn("CONFIRM_APPLY", bold=True)
        confirm = input(f" {Colors.BOLD}(y/n) > {Colors.ENDC}").strip().lower()
        if confirm == 'y':
            _apply_sysctl_settings({
                "net.core.rmem_max": 4194304,
                "net.core.wmem_max": 4194304,
            })

    elif choice == '2':
        iface = _select_interface()
        print(f"\n{Colors.WARNING}⚠️ Jumbo Frame 설정 전 확인 사항:{Colors.ENDC}")
        print(f"  - 경로 상의 모든 스위치/라우터가 MTU 9000을 지원해야 합니다.")
        print(f"  - 미지원 장비가 있으면 패킷이 분할되거나 통신 장애가 발생할 수 있습니다.")
        Messenger.warn("CONFIRM_APPLY", bold=True)
        confirm = input(f" {Colors.BOLD}(y/n) > {Colors.ENDC}").strip().lower()
        if confirm == 'y':
            try:
                subprocess.run(
                    ["sudo", "ip", "link", "set", "dev", iface, "mtu", "9000"],
                    check=True, capture_output=True, text=True
                )
                print(f"    {Colors.OKGREEN}✔{Colors.ENDC} {iface} MTU -> 9000 {Colors.OKBLUE}(성공){Colors.ENDC}")
            except subprocess.CalledProcessError as e:
                print(f"    {Colors.FAIL}✘{Colors.ENDC} MTU 설정 실패: {e.stderr.strip()}")
            input("\n계속하려면 [Enter]를 누르세요...")

def _apply_linux_bbr():
    """BBR 혼잡제어 활성화"""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}🚀 BBR 혼잡제어 활성화{Colors.ENDC}")

    try:
        cc = subprocess.check_output(
            ["sysctl", "-n", "net.ipv4.tcp_congestion_control"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        print(f"  현재 혼잡제어: {Colors.BOLD}{cc}{Colors.ENDC}")
    except:
        cc = "unknown"
        print(f"  현재 혼잡제어: 확인 불가")

    if cc == "bbr":
        Messenger.info("이미 BBR이 활성화되어 있습니다.")
        input("\n계속하려면 [Enter]를 누르세요...")
        return

    Messenger.warn("CONFIRM_APPLY", bold=True)
    confirm = input(f" {Colors.BOLD}(y/n) > {Colors.ENDC}").strip().lower()
    if confirm == 'y':
        config_manager.save_config("bk")
        print(f"\n{Colors.BOLD}🛠️ 설정 적용 중...{Colors.ENDC}")
        run_modprobe("tcp_bbr")
        run_sysctl_command("net.ipv4.tcp_congestion_control", "bbr")

        try:
            result = subprocess.check_output(
                ["sysctl", "-n", "net.ipv4.tcp_congestion_control"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            print(f"\n  적용 결과: {Colors.OKGREEN}{Colors.BOLD}{result}{Colors.ENDC}")
        except:
            pass
        input("\n계속하려면 [Enter]를 누르세요...")

def _apply_linux_tuning():
    """Linux 네트워크 최적화 서브메뉴"""
    while True:
        print(f"\n{Colors.BOLD}{Colors.HEADER}   [ Linux 네트워크 최적화 ]{Colors.ENDC}")
        print(f"   1. {Colors.OKGREEN}일반 호스트 튜닝 (TCP 버퍼 최적화){Colors.ENDC}")
        print(f"   2. {Colors.OKCYAN}테스트/측정 호스트 튜닝{Colors.ENDC}")
        print(f"   3. {Colors.OKBLUE}100G NIC 드라이버 최적화{Colors.ENDC}")
        print(f"   4. {Colors.WARNING}패킷 페이싱 설정{Colors.ENDC}")
        print(f"   5. {Colors.OKCYAN}UDP 튜닝{Colors.ENDC}")
        print(f"   6. {Colors.OKGREEN}BBR 혼잡제어 활성화{Colors.ENDC}")
        print(f"   b. {Colors.BOLD}뒤로 가기{Colors.ENDC}")

        choice = input(f"\n {Colors.BOLD}선택 > {Colors.ENDC}").strip().lower()

        if choice == '1':
            _apply_linux_general()
        elif choice == '2':
            _apply_linux_test_host()
        elif choice == '3':
            _apply_linux_100g_nic()
        elif choice == '4':
            _apply_linux_packet_pacing()
        elif choice == '5':
            _apply_linux_udp()
        elif choice == '6':
            _apply_linux_bbr()
        elif choice == 'b':
            break

def _reset_linux_defaults():
    """Linux 기본값 복원"""
    Messenger.warn("CONFIRM_RESET", bold=True)
    confirm = input(f" {Colors.BOLD}(y/n) > {Colors.ENDC}").strip().lower()

    if confirm == 'y':
        config_manager.save_config("bk")
        defaults = {
            "net.core.rmem_max": 212992,
            "net.core.wmem_max": 212992,
            "net.ipv4.tcp_rmem": "4096 131072 6291456",
            "net.ipv4.tcp_wmem": "4096 16384 4194304",
            "net.core.default_qdisc": "fq_codel",
            "net.ipv4.tcp_congestion_control": "cubic",
            "net.ipv4.tcp_mtu_probing": 0,
            "net.ipv4.tcp_no_metrics_save": 0,
            "net.core.optmem_max": 20480,
        }
        print(f"\n{Colors.BOLD}🛠️ 기본값 복원 중...{Colors.ENDC}")
        success = True
        for oid, val in defaults.items():
            success &= run_sysctl_command(oid, val)
        if success:
            Messenger.success("SUCCESS_RESTORE")
        input("\n계속하려면 [Enter]를 누르세요...")

def _apply_mac_tuning():
    """macOS 전용 네트워크 튜닝 로직"""
    guide = calculate_guidelines()
    esnet_val = 33554432
    nettune_val = int(guide['suggested_max_buffer_bytes'])
    
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}🚀 macOS 네트워크 최적화 설정{Colors.ENDC}")
    print(f" [옵션 1] ESNet Fasterdata 권장값 (32 MB)")
    print(f" [옵션 2] NetTune RAM 기반 권장값 ({guide['suggested_max_buffer_mb']} MB)")
    
    choice = input(f"\n{Colors.BOLD}선택 (1 또는 2) > {Colors.ENDC}").strip()
    if choice not in ['1', '2']:
        Messenger.warn("CANCELLED")
        return

    target_val = esnet_val if choice == '1' else nettune_val
    
    Messenger.warn("CONFIRM_APPLY", bold=True)
    confirm = input(f" {Colors.BOLD}(y/n) > {Colors.ENDC}").strip().lower()
    if confirm == 'y':
        config_manager.save_config("bk")
        print(f"\n{Colors.BOLD}🛠️ 설정 적용 중...{Colors.ENDC}")
        success = True
        success &= run_sysctl_command("net.inet.tcp.win_scale_factor", 8)
        success &= run_sysctl_command("net.inet.tcp.autorcvbufmax", target_val)
        success &= run_sysctl_command("net.inet.tcp.autosndbufmax", target_val)
        
        if success:
            Messenger.success("SUCCESS_TUNING")
            Messenger.warn("설정이 즉시 반영되었으나, 재부팅 시 초기화될 수 있습니다.", bold=False)
        input("\n계속하려면 [Enter]를 누르세요...")

def apply_highspeed_tuning():
    """OS를 자동 판별하여 고속망 튜닝 적용"""
    system = platform.system()
    if system == "Darwin":
        _apply_mac_tuning()
    elif system == "Linux":
        _apply_linux_tuning()
    else:
        Messenger.error(f"OS_NOT_SUPPORTED: {system}")

def _reset_mac_defaults():
    """macOS 기본값 복원 로직"""
    Messenger.warn("CONFIRM_RESET", bold=True)
    confirm = input(f" {Colors.BOLD}(y/n) > {Colors.ENDC}").strip().lower()
    
    if confirm == 'y':
        config_manager.save_config("bk")
        defaults = {
            "net.inet.tcp.autorcvbufmax": 1048576,
            "net.inet.tcp.autosndbufmax": 1048576,
            "net.inet.tcp.sendspace": 131072,
            "net.inet.tcp.recvspace": 131072,
            "net.inet.tcp.win_scale_factor": 3,
            "kern.ipc.maxsockbuf": 4194304
        }
        success = True
        for oid, val in defaults.items():
            success &= run_sysctl_command(oid, val)
        if success:
            Messenger.success("SUCCESS_RESTORE")
        input("\n계속하려면 [Enter]를 누르세요...")

def reset_to_defaults():
    """OS를 자동 판별하여 네트워크 설정 초기화"""
    system = platform.system()
    if system == "Darwin":
        _reset_mac_defaults()
    elif system == "Linux":
        _reset_linux_defaults()
    else:
        Messenger.error(f"OS_NOT_SUPPORTED: {system}")

def restore_config(content):
    """백업 데이터로부터 시스템 설정을 복원/적용"""
    Messenger.warn("SUDO_REQUIRED")
    Messenger.warn("CONFIRM_APPLY", bold=True)
    confirm = input(f" {Colors.BOLD}(y/n) > {Colors.ENDC}").strip().lower()
    
    if confirm != 'y':
        Messenger.warn("CANCELLED")
        return

    success = True
    print(f"\n{Colors.BOLD}🛠️ 설정을 복원 중...{Colors.ENDC}")

    targets = {
        'tcp_sendspace': "net.inet.tcp.sendspace",
        'tcp_recvspace': "net.inet.tcp.recvspace",
        'maxsockbuf': "kern.ipc.maxsockbuf",
        'autorcvbufmax': "net.inet.tcp.autorcvbufmax",
        'autosndbufmax': "net.inet.tcp.autosndbufmax",
        'win_scale_factor': "net.inet.tcp.win_scale_factor"
    }

    if 'tcp_buffers' in content['settings']:
        for label, value in content['settings']['tcp_buffers'].items():
            if label in targets and value != "Not found":
                success &= run_sysctl_command(targets[label], value)

    if 'mtu' in content['settings'] and content['settings']['mtu'] != "Unknown":
        iface = content['metadata']['interface']
        if iface and iface != "Not Found":
            try:
                print(f"    🛠️ MTU 설정 적용 중 ({iface} -> {content['settings']['mtu']})...")
                subprocess.run(["sudo", "ifconfig", iface, "mtu", str(content['settings']['mtu'])], check=True)
                print(f"    {Colors.OKGREEN}✔{Colors.ENDC} MTU 설정 성공")
            except:
                print(f"    {Colors.FAIL}✘{Colors.ENDC} MTU 설정 실패")
                success = False

    if success:
        Messenger.success("SUCCESS_RESTORE")
        Messenger.warn("설정이 복원되었으나, 영구 반영을 위해서는 별도 설정 파일 작업이 필요합니다.", bold=False)
    else:
        Messenger.error("ERROR_RESTORE")
    
    input("\n계속하려면 [Enter]를 누르세요...")

def show_backup_list():
    """저장된 백업 목록 표시 및 상세 보기 / 적용"""
    backups = config_manager.list_backups()
    
    if not backups:
        Messenger.info("FILE_NOT_FOUND")
        return

    while True:
        print(f"\n{Colors.BOLD}{Colors.OKCYAN}📂 시스템 설정 백업 목록:{Colors.ENDC}")
        for i, file in enumerate(backups, 1):
            print(f"   {i}. {file}")
        
        choice = input(f"\n{Colors.BOLD}상세보기 및 적용할 번호 입력 (나가려면 Enter) > {Colors.ENDC}").strip()
        if not choice:
            break

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(backups):
                content = config_manager.load_config_file(backups[idx])
                if content:
                    print(f"\n{Colors.BOLD}┌────────────────── [ 백업 상세 정보 ] ──────────────────┐{Colors.ENDC}")
                    print(f" │ 파일명: {backups[idx]:<45} │")
                    print(f" │ 인터페이스: {content['metadata']['interface']:<41} │")
                    print(f" │ 백업 시간: {content['metadata']['timestamp']:<41} │")
                    print(f" ├───────────────────────────────────────────────────────┤")
                    print(f" │ [설정 내용]                                           │")
                    for k, v in content['settings']['tcp_buffers'].items():
                        print(f" │ - {k:16}: {v:<36} │")
                    print(f" │ - MTU             : {content['settings']['mtu']:<36} │")
                    print(f" └───────────────────────────────────────────────────────┘")
                    
                    print(f"\n {Colors.OKGREEN}[a] 이 설정을 지금 적용(Restore){Colors.ENDC}")
                    print(f" {Colors.FAIL}[d] 이 백업 파일 삭제{Colors.ENDC}")
                    print(f" [Enter] 목록으로")
                    
                    sub_choice = input(f"\n{Colors.BOLD}선택 > {Colors.ENDC}").strip().lower()
                    if sub_choice == 'a':
                        restore_config(content)
                        break
                    elif sub_choice == 'd':
                        Messenger.warn("CONFIRM_DELETE", bold=True)
                        confirm = input(f" {Colors.BOLD}(y/n) > {Colors.ENDC}").strip().lower()
                        if confirm == 'y':
                            if config_manager.delete_config_file(backups[idx]):
                                backups = config_manager.list_backups() # 목록 갱신
                                if not backups:
                                    Messenger.info("FILE_NOT_FOUND")
                                    break
            else:
                Messenger.error("INVALID_INPUT")

def apply_tuning_placeholder():
    """튜닝 메뉴 메인 루프"""
    while True:
        print(f"\n{Colors.BOLD}{Colors.HEADER}   [ 3. 튜닝 및 설정 관리 ]{Colors.ENDC}")
        print(f"   1. {Colors.OKGREEN}현재 시스템 설정 백업 생성{Colors.ENDC}")
        print(f"   2. {Colors.OKCYAN}백업 목록 보기 및 상세 정보{Colors.ENDC}")
        print(f"   3. {Colors.OKBLUE}전송 고속망 최적화 설정 적용{Colors.ENDC}")
        print(f"   4. {Colors.WARNING}네트워크 설정 초기화 (Default 복원){Colors.ENDC}")
        print(f"   b. {Colors.BOLD}뒤로 가기{Colors.ENDC}")
        
        choice = input(f"\n {Colors.BOLD}선택 > {Colors.ENDC}").strip().lower()
        
        if choice == '1':
            config_manager.save_config()
            input("\n백업 완료 [Enter]를 누르면 돌아갑니다...")
        elif choice == '2':
            show_backup_list()
        elif choice == '3':
            apply_highspeed_tuning()
        elif choice == '4':
            reset_to_defaults()
        elif choice == 'b':
            break
