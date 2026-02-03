import platform
import subprocess
from utils import Colors
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
        print(f"{Colors.WARNING}취소되었습니다.{Colors.ENDC}")
        return

    target_val = esnet_val if choice == '1' else nettune_val
    
    confirm = input(f"\n{Colors.WARNING}⚠️ 설정을 적용하시겠습니까? (y/n) > {Colors.ENDC}").strip().lower()
    if confirm == 'y':
        config_manager.save_config("bk")
        print(f"\n{Colors.BOLD}🛠️ 설정 적용 중...{Colors.ENDC}")
        success = True
        success &= run_sysctl_command("net.inet.tcp.win_scale_factor", 8)
        success &= run_sysctl_command("net.inet.tcp.autorcvbufmax", target_val)
        success &= run_sysctl_command("net.inet.tcp.autosndbufmax", target_val)
        
        if success:
            print(f"\n{Colors.BOLD}{Colors.OKGREEN}🎉 최적화 설정이 완료되었습니다!{Colors.ENDC}")
        input("\n계속하려면 [Enter]를 누르세요...")

def apply_highspeed_tuning():
    """OS를 자동 판별하여 고속망 튜닝 적용"""
    system = platform.system()
    if system == "Darwin":
        _apply_mac_tuning()
    elif system == "Linux":
        print(f"\n{Colors.WARNING}ℹ️ Linux용 고속망 튜닝은 현재 준비 중입니다.{Colors.ENDC}")
        input("\n[Enter]를 누르면 돌아갑니다...")
    else:
        print(f"\n{Colors.FAIL}❌ 지원하지 않는 OS입니다: {system}{Colors.ENDC}")

def _reset_mac_defaults():
    """macOS 기본값 복원 로직"""
    print(f"\n{Colors.WARNING}⚠️ macOS 네트워크 설정을 표준 기본값으로 초기화합니다.{Colors.ENDC}")
    confirm = input(" 계속하시겠습니까? (y/n) > ").strip().lower()
    
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
            print(f"\n{Colors.BOLD}{Colors.OKGREEN}🎉 기본값으로 복원되었습니다!{Colors.ENDC}")
        input("\n계속하려면 [Enter]를 누르세요...")

def reset_to_defaults():
    """OS를 자동 판별하여 네트워크 설정 초기화"""
    system = platform.system()
    if system == "Darwin":
        _reset_mac_defaults()
    elif system == "Linux":
        print(f"\n{Colors.WARNING}ℹ️ Linux용 초기화 기능은 현재 준비 중입니다.{Colors.ENDC}")
        input("\n[Enter]를 누르면 돌아갑니다...")
    else:
        print(f"\n{Colors.FAIL}❌ 지원하지 않는 OS입니다: {system}{Colors.ENDC}")

def restore_config(content):
    """백업 데이터로부터 시스템 설정을 복원/적용"""
    print(f"\n{Colors.WARNING}⚠️ 백업 설정을 시스템에 적용합니다. (sudo 권한 필요){Colors.ENDC}")
    confirm = input(" 이 설정을 적용하시겠습니까? (y/n) > ").strip().lower()
    
    if confirm != 'y':
        print(f"{Colors.WARNING}적용이 취소되었습니다.{Colors.ENDC}")
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
        print(f"\n{Colors.BOLD}{Colors.OKGREEN}🎉 설정 복원이 완료되었습니다!{Colors.ENDC}")
    else:
        print(f"\n{Colors.FAIL}⚠️ 일부 설정 복원에 실패했습니다.{Colors.ENDC}")
    
    input("\n계속하려면 [Enter]를 누르세요...")

def show_backup_list():
    """저장된 백업 목록 표시 및 상세 보기 / 적용"""
    backups = config_manager.list_backups()
    
    if not backups:
        print(f"\n{Colors.WARNING}ℹ️ 저장된 백업 파일이 없습니다.{Colors.ENDC}")
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
                    
                    sub_choice = input(f"\n{Colors.OKGREEN}[a] 이 설정을 지금 적용(Restore){Colors.ENDC} / [Enter] 목록으로 : ").strip().lower()
                    if sub_choice == 'a':
                        restore_config(content)
                        break
            else:
                print(f"{Colors.FAIL}❌ 잘못된 번호입니다.{Colors.ENDC}")

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
