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

def get_physical_speed(interface):
    """물리 속도 체크 (ethtool 또는 networksetup/ifconfig)"""
    try:
        if platform.system() == "Linux":
            try:
                output = subprocess.check_output(["ethtool", interface], stderr=subprocess.STDOUT).decode()
                for line in output.splitlines():
                    if "Speed:" in line:
                        return line.split(":")[1].strip()
            except:
                return "ethtool not available or permission denied"
        elif platform.system() == "Darwin":
            try:
                # ifconfig에서 media 확인
                output = subprocess.check_output(["ifconfig", interface]).decode()
                for line in output.splitlines():
                    if "media:" in line:
                        media_info = line.split("media:")[1].strip()
                        if "(" in media_info:
                            return media_info.split("(")[1].split(")")[0]
                        return media_info
                return "Unknown"
            except:
                return "ifconfig failed"
    except Exception as e:
        return f"Error: {e}"
    return "Unknown"

def get_tcp_buffers():
    """TCP/IP 버퍼 사이즈 추출"""
    buffers = {}
    try:
        if platform.system() == "Linux":
            # Linux는 min, default, max 3개 값이 나옴
            rmem = subprocess.check_output(["sysctl", "net.ipv4.tcp_rmem"]).decode().strip()
            wmem = subprocess.check_output(["sysctl", "net.ipv4.tcp_wmem"]).decode().strip()
            # net.core.rmem_max, wmem_max도 중요함
            rmem_max = subprocess.check_output(["sysctl", "net.core.rmem_max"]).decode().strip()
            wmem_max = subprocess.check_output(["sysctl", "net.core.wmem_max"]).decode().strip()
            
            buffers['tcp_rmem (min default max)'] = rmem.split("=")[1].strip()
            buffers['tcp_wmem (min default max)'] = wmem.split("=")[1].strip()
            buffers['core_rmem_max'] = rmem_max.split("=")[1].strip()
            buffers['core_wmem_max'] = wmem_max.split("=")[1].strip()
        elif platform.system() == "Darwin":
            send = subprocess.check_output(["sysctl", "net.inet.tcp.sendspace"]).decode().strip()
            recv = subprocess.check_output(["sysctl", "net.inet.tcp.recvspace"]).decode().strip()
            sb_max = subprocess.check_output(["sysctl", "kern.ipc.maxsockbuf"]).decode().strip()
            
            buffers['tcp_sendspace'] = send.split(":")[1].strip()
            buffers['tcp_recvspace'] = recv.split(":")[1].strip()
            buffers['kern.ipc.maxsockbuf'] = sb_max.split(":")[1].strip()
    except Exception as e:
        return {"error": str(e)}
    return buffers

def get_congestion_control():
    """혼잡제어 알고리즘 확인"""
    try:
        if platform.system() == "Linux":
            cc = subprocess.check_output(["sysctl", "net.ipv4.tcp_congestion_control"]).decode().strip()
            return cc.split("=")[1].strip()
        elif platform.system() == "Darwin":
            # macOS는 sysctl로 직접 확인이 어려울 수 있음 (버전에 따라 다름)
            # 보통 Cubic 또는 NewReno 사용
            try:
                cc = subprocess.check_output(["sysctl", "net.inet.tcp.cc_algo"]).decode().strip()
                return cc.split(":")[1].strip()
            except:
                return "Default (likely Cubic or NewReno on macOS)"
    except Exception as e:
        return f"Error: {e}"
    return "Unknown"

def get_cpu_governor():
    """CPU Governor 확인 (Linux 위주)"""
    if platform.system() != "Linux":
        return "N/A (macOS uses internal power management)"
    
    try:
        # 모든 CPU에 대해 확인
        governors = set()
        for i in range(os.cpu_count() or 1):
            path = f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor"
            if os.path.exists(path):
                with open(path, 'r') as f:
                    governors.add(f.read().strip())
        
        if not governors:
            return "Governor info not found"
        return ", ".join(governors)
    except Exception as e:
        return f"Error: {e}"

def calculate_guidelines():
    """메모리 기반 네트워크 버퍼 가이드라인 계산"""
    total_mem = psutil.virtual_memory().total
    total_mem_gb = total_mem / (1024**3)
    
    # 고속 네트워크 튜닝 가이드 (10Gbps, 100ms RTT 기준 BDP = 125MB)
    # 메모리 용량에 따른 제안:
    # 16GB 미만: 최대 64MB
    # 16GB - 64GB: 최대 128MB
    # 64GB 이상: 최대 256MB~512MB
    
    if total_mem_gb < 16:
        suggested_mb = 64
    elif total_mem_gb < 64:
        suggested_mb = 128
    else:
        suggested_mb = 512
        
    suggested_bytes = suggested_mb * 1024 * 1024
    
    # 시스템 메모리의 최대 5%를 초과하지 않도록 제한
    limit_bytes = int(total_mem * 0.05)
    if suggested_bytes > limit_bytes:
        suggested_bytes = limit_bytes
        suggested_mb = suggested_bytes / (1024 * 1024)
    
    return {
        "total_memory_gb": round(total_mem_gb, 2),
        "suggested_max_buffer_bytes": suggested_bytes,
        "suggested_max_buffer_mb": round(suggested_mb, 2)
    }

def main():
    print("\n" + "="*60)
    print("   [NetTune] 고속 네트워크 환경 진단 및 튜닝 가이드")
    print("="*60)
    
    # 1. 인터페이스 식별
    iface = get_default_interface()
    print(f" 1. 외부 인터페이스    : {iface}")
    
    if iface != "Not Found" and "Error" not in iface:
        # 2. 물리 속도
        speed = get_physical_speed(iface)
        print(f" 2. 물리 속도 (Media)  : {speed}")
        
        # 3. MTU
        mtu = get_mtu(iface)
        print(f" 3. MTU 설정값         : {mtu}")
        if mtu == "1500":
            print("    * 고속망(Jumbo Frame) 사용 시 9000 설정을 권장합니다.")
    
    # 4. TCP 버퍼 사이즈
    print(f" 4. TCP/IP 버퍼 설정  :")
    buffers = get_tcp_buffers()
    for k, v in buffers.items():
        print(f"    - {k:20}: {v}")
        
    # 5. 혼잡제어 알고리즘
    cc = get_congestion_control()
    print(f" 5. 혼잡제어 알고리즘  : {cc}")
    if platform.system() == "Linux" and "cubic" in cc.lower():
        print("    * 롱디스턴스(LFN) 환경에서는 'bbr' 또는 'htcp' 사용을 검토하세요.")
    
    # 6. 메모리 기반 가이드라인
    guide = calculate_guidelines()
    print(f" 6. 튜닝 가이드라인    :")
    print(f"    - 시스템 총 메모리 : {guide['total_memory_gb']} GB")
    print(f"    - 권장 최대 버퍼   : {guide['suggested_max_buffer_mb']} MB ({guide['suggested_max_buffer_bytes']} bytes)")
    print(f"    * 10Gbps+ 환경에서는 BDP(Bandwidth-Delay Product)를 위해 위 수준의 확장이 필요합니다.")
    
    # 7. CPU Governor
    gov = get_cpu_governor()
    print(f" 7. CPU Governor       : {gov}")
    if "powersave" in gov.lower():
        print("    ! 경고: 'powersave' 모드는 패킷 처리 지연을 유발할 수 있습니다.")
        print("    ! 권장: sudo cpupower frequency-set -g performance")

    print("="*60 + "\n")

if __name__ == "__main__":
    main()
