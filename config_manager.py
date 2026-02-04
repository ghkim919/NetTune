import os
import json
import platform
from datetime import datetime
from utils import Colors, get_tcp_buffers, get_congestion_control, get_mtu, get_default_interface

# 설정 저장 디렉토리 이름
CONFIG_DIR = "config_list"

def ensure_config_dir():
    """설정 저장 디렉토리가 없으면 생성"""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

def get_current_system_config():
    """현재 시스템의 주요 네트워크 설정을 딕셔너리로 추출"""
    iface = get_default_interface()
    config = {
        "metadata": {
            "os": platform.system(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "interface": iface
        },
        "settings": {
            "tcp_buffers": get_tcp_buffers(),
            "congestion_control": get_congestion_control(),
            "mtu": get_mtu(iface) if iface != "Not Found" else "N/A"
        }
    }
    return config

def save_config(label=""):
    """현재 설정을 파일로 저장 (백업 생성)"""
    ensure_config_dir()
    
    current_config = get_current_system_config()
    os_name = platform.system().lower()
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # {OS}_{YYYYMMDD}_{HHmmSS}_bk 포맷 대응
    suffix = f"_{label}" if label else ""
    filename = f"{os_name}_{timestamp_str}{suffix}.json"
    filepath = os.path.join(CONFIG_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, indent=4, ensure_ascii=False)
        print(f"\n{Colors.OKGREEN}✅ 설정 백업 성공!{Colors.ENDC}")
        print(f"    - 파일명: {Colors.BOLD}{filename}{Colors.ENDC}")
        return filename
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ 백업 저장 중 오류 발생: {e}{Colors.ENDC}")
        return None

def list_backups():
    """저장된 백업 파일 목록 반환 및 출력"""
    ensure_config_dir()
    files = [f for f in os.listdir(CONFIG_DIR) if f.endswith('.json')]
    files.sort(reverse=True) # 최신순
    return files

def load_config_file(filename):
    """특정 백업 파일의 내용을 읽어서 반환"""
    filepath = os.path.join(CONFIG_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ 파일 읽기 오류: {e}{Colors.ENDC}")
        return None

def delete_config_file(filename):
    """특정 백업 파일을 삭제"""
    filepath = os.path.join(CONFIG_DIR, filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"\n{Colors.OKGREEN}✅ 설정 파일이 삭제되었습니다.{Colors.ENDC}")
            return True
        else:
            print(f"\n{Colors.FAIL}❌ 파일을 찾을 수 없습니다.{Colors.ENDC}")
            return False
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ 파일 삭제 중 오류 발생: {e}{Colors.ENDC}")
        return False
