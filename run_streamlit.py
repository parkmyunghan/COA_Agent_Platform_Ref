# run_streamlit.py
# -*- coding: utf-8 -*-
"""
Streamlit UI 실행 스크립트
"""
import subprocess
import sys
import os
import socket
import argparse
from pathlib import Path

# 현재 디렉토리를 프로젝트 루트로 설정
BASE_DIR = Path(__file__).parent
os.chdir(BASE_DIR)

# Streamlit 실행
if __name__ == "__main__":
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(description="Streamlit UI 실행")
    parser.add_argument(
        "--app",
        type=str,
        default="dashboard",
        choices=["dashboard", "coa"],
        help="실행할 앱 선택: dashboard (기본) 또는 coa (COA Agent 데모)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="서버 포트 (기본값: 8501)"
    )
    # 🔥 NEW: 로그 파일 기록 옵션 (기본값: False)
    parser.add_argument(
        "--log-to-file",
        action="store_true",
        help="로그 파일 기록 활성화 (기본값: 비활성화)"
    )
    args = parser.parse_args()
    
    # 환경 변수 설정 (utils.py에서 사용)
    if args.log_to_file:
        os.environ["COA_LOG_TO_FILE"] = "true"
        print(">> [INFO] 파일 로깅 활성화됨")
    else:
        os.environ["COA_LOG_TO_FILE"] = "false"
        print(">> [INFO] 파일 로깅 비활성화됨 (속도 최적화)")
    
    # 앱 선택
    if args.app == "coa":
        app_file = "ui/coa_agent_app.py"
        app_name = "COA Agent 데모"
    else:
        app_file = "ui/dashboard.py"
        app_name = "통합 대시보드"
    
    # 로컬 IP 주소 가져오기
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "127.0.0.1"
    
    # 포트 사용 가능 여부 확인 함수
    def is_port_available(port):
        """포트가 사용 가능한지 확인"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('localhost', port))
            sock.close()
            return True
        except OSError:
            return False
    
    # 포트가 사용 중이면 다른 포트 시도
    actual_port = args.port
    if not is_port_available(args.port):
        print(f">> [WARN] 포트 {args.port}가 사용 중입니다. 다른 포트를 찾는 중...")
        for alt_port in range(8502, 8510):
            if is_port_available(alt_port):
                actual_port = alt_port
                print(f">> [INFO] 포트 {actual_port} 사용")
                break
        else:
            print(">> [ERROR] 사용 가능한 포트를 찾을 수 없습니다.")
            print(">> [INFO] 실행 중인 Streamlit 프로세스를 종료하세요:")
            print(">>        python scripts/kill_streamlit.py")
            sys.exit(1)
    
    print("=" * 60)
    print(f"Streamlit 서버 시작 중... ({app_name})")
    print("=" * 60)
    print(f"로컬 접속: http://localhost:{actual_port}")
    print(f"또는: http://127.0.0.1:{actual_port}")
    if local_ip != "127.0.0.1":
        print(f"네트워크 접속: http://{local_ip}:{actual_port}")
    print("=" * 60)
    print()
    
    # Streamlit 앱 실행
    # 네트워크 접근 가능하도록 설정 (파일럿 테스트용)


    # Streamlit 앱 실행
    # 네트워크 접근 가능하도록 설정 (파일럿 테스트용)
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            app_file,
            f"--server.port={actual_port}",
            "--server.address=0.0.0.0",  # 네트워크 접근 허용
            "--server.headless=true"  # 헤드리스 모드
        ])
    except KeyboardInterrupt:
        pass


# Trigger reload due to UI fix

