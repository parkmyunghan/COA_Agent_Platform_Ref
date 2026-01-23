# scripts/kill_streamlit.py
# -*- coding: utf-8 -*-
"""
실행 중인 Streamlit 프로세스 종료 스크립트
"""
import subprocess
import sys
import os

def kill_streamlit_processes():
    """포트 8501을 사용하는 프로세스 종료"""
    try:
        # Windows에서 포트를 사용하는 프로세스 찾기
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            shell=True
        )
        
        lines = result.stdout.split('\n')
        pids_to_kill = []
        
        for line in lines:
            if ':8501' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    pids_to_kill.append(pid)
        
        if pids_to_kill:
            print(f"포트 8501을 사용하는 프로세스 발견: {', '.join(pids_to_kill)}")
            for pid in pids_to_kill:
                try:
                    subprocess.run(["taskkill", "/F", "/PID", pid], check=True)
                    print(f"  ✅ 프로세스 {pid} 종료됨")
                except subprocess.CalledProcessError as e:
                    print(f"  ⚠️  프로세스 {pid} 종료 실패: {e}")
            return True
        else:
            print("포트 8501을 사용하는 프로세스가 없습니다.")
            return False
            
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

def kill_python_streamlit():
    """Python Streamlit 프로세스 종료 (더 안전한 방법)"""
    try:
        # streamlit 프로세스 찾기
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe"],
            capture_output=True,
            text=True,
            shell=True
        )
        
        if "python.exe" in result.stdout:
            print("Python 프로세스가 실행 중입니다.")
            print("\n수동으로 종료하려면:")
            print("  1. 작업 관리자에서 python.exe 프로세스 종료")
            print("  2. 또는 다음 명령 실행: taskkill /F /IM python.exe")
            
            response = input("\n모든 Python 프로세스를 종료하시겠습니까? (y/n): ").strip().lower()
            if response == 'y':
                subprocess.run(["taskkill", "/F", "/IM", "python.exe"], check=True)
                print("✅ 모든 Python 프로세스 종료됨")
                return True
        else:
            print("실행 중인 Python 프로세스가 없습니다.")
            return False
            
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Streamlit 프로세스 종료")
    print("=" * 60)
    print()
    
    # 방법 1: 포트 기반 종료
    print("방법 1: 포트 8501 사용 프로세스 종료")
    if kill_streamlit_processes():
        print("\n✅ 완료!")
    else:
        print("\n방법 2: Python 프로세스 확인")
        kill_python_streamlit()























