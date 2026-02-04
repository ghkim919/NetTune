import sys
from utils import Colors, Messenger
from diagnosis import run_diagnosis, show_explanations
from test import run_iperf_test, run_precision_bdp_calculator
import tuning

def main_menu_diagnosis():
    """진단 기능 서브메뉴"""
    while True:
        print(f"\n{Colors.BOLD}{Colors.HEADER}   [ 1. 진단 기능 ]{Colors.ENDC}")
        print(f"   1. {Colors.OKGREEN}네트워크 상세 진단 시작{Colors.ENDC}")
        print(f"   2. {Colors.OKCYAN}각 진단 항목에 대한 설명 보기{Colors.ENDC}")
        print(f"   b. {Colors.BOLD}뒤로 가기{Colors.ENDC}")
        
        choice = input(f"\n {Colors.BOLD}선택 > {Colors.ENDC}").strip().lower()
        if choice == '1':
            run_diagnosis()
        elif choice == '2':
            show_explanations()
        elif choice == 'b':
            break

def main_menu_test():
    """테스트 기능 서브메뉴"""
    while True:
        print(f"\n{Colors.BOLD}{Colors.HEADER}   [ 2. 테스트 기능 ]{Colors.ENDC}")
        print(f"   1. {Colors.WARNING}실시간 속도 측정 (iperf3){Colors.ENDC}")
        print(f"   2. {Colors.OKBLUE}정밀 BDP(대역폭-지연) 계산기{Colors.ENDC}")
        print(f"   b. {Colors.BOLD}뒤로 가기{Colors.ENDC}")
        
        choice = input(f"\n {Colors.BOLD}선택 > {Colors.ENDC}").strip().lower()
        if choice == '1':
            run_iperf_test()
            input("\n측정 완료 [Enter]를 누르면 메뉴로 이동합니다...")
        elif choice == '2':
            run_precision_bdp_calculator()
        elif choice == 'b':
            break

def main_menu_tuning():
    """튜닝 및 설정 관리 서브메뉴"""
    tuning.apply_tuning_placeholder()

def main():
    while True:
        print(f"\n{Colors.BOLD}{Colors.HEADER}   [ NetTune: 네트워크 최적화 도구 ]{Colors.ENDC}")
        print(f"   1. {Colors.OKGREEN}진단 기능{Colors.ENDC}")
        print(f"   2. {Colors.OKCYAN}테스트 기능{Colors.ENDC}")
        print(f"   3. {Colors.OKBLUE}튜닝 기능{Colors.ENDC}")
        print(f"   q. {Colors.BOLD}종료{Colors.ENDC}")
        
        choice = input(f"\n {Colors.BOLD}입력하세요 > {Colors.ENDC}").strip().lower()
        if choice == '1':
            main_menu_diagnosis()
        elif choice == '2':
            main_menu_test()
        elif choice == '3':
            main_menu_tuning()
        elif choice == 'q':
            Messenger.success("EXIT_APP", bold=False)
            break
        else:
            Messenger.error("INVALID_INPUT")

if __name__ == "__main__":
    main()
