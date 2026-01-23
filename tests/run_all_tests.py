# tests/run_all_tests.py
# -*- coding: utf-8 -*-
"""
전체 테스트 실행 스크립트
모든 테스트를 순차적으로 실행하고 결과를 종합
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))


def run_test_file(test_file: str) -> Tuple[bool, str, str]:
    """
    테스트 파일 실행
    
    Returns:
        (success, output, error)
    """
    test_path = BASE_DIR / "tests" / test_file
    if not test_path.exists():
        return False, "", f"테스트 파일이 없습니다: {test_file}"
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=600  # 10분 타임아웃
        )
        
        success = result.returncode == 0
        return success, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"테스트 타임아웃: {test_file}"
    except Exception as e:
        return False, "", f"테스트 실행 오류: {e}"


def parse_test_results(output: str) -> Dict:
    """테스트 출력에서 결과 파싱"""
    result = {
        "total": 0,
        "success": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0
    }
    
    lines = output.split('\n')
    for line in lines:
        if "총 테스트 수" in line or "Ran" in line:
            # "총 테스트 수: 9" 또는 "Ran 9 tests"
            parts = line.split()
            for i, part in enumerate(parts):
                if part.isdigit():
                    result["total"] = int(part)
                    break
        elif "성공" in line or "ok" in line.lower():
            if "성공:" in line:
                parts = line.split("성공:")
                if len(parts) > 1:
                    try:
                        result["success"] = int(parts[1].strip().split()[0])
                    except:
                        pass
        elif "실패" in line or "failures" in line.lower():
            if "실패:" in line:
                parts = line.split("실패:")
                if len(parts) > 1:
                    try:
                        result["failures"] = int(parts[1].strip().split()[0])
                    except:
                        pass
        elif "오류" in line or "errors" in line.lower():
            if "오류:" in line:
                parts = line.split("오류:")
                if len(parts) > 1:
                    try:
                        result["errors"] = int(parts[1].strip().split()[0])
                    except:
                        pass
    
    # success가 없으면 total에서 failures와 errors를 빼서 계산
    if result["success"] == 0 and result["total"] > 0:
        result["success"] = result["total"] - result["failures"] - result["errors"]
    
    return result


def main():
    """전체 테스트 실행"""
    print("="*70)
    print("전체 테스트 실행")
    print("="*70)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 테스트 파일 목록
    test_files = [
        ("test_situation_input.py", "상황정보 입력 테스트"),
        ("test_coa_recommendation_integration.py", "방책 추천 통합 테스트"),
        ("test_situation_input_to_coa_recommendation.py", "상황정보 입력 → 방책 추천 통합 테스트"),
        ("test_coa_recommendation_validation.py", "방책 추천 결과 검증 테스트"),
        ("test_coa_appropriateness.py", "위협상황별 적절한 방책 추천 검증 테스트"),
    ]
    
    results = []
    total_stats = {
        "total": 0,
        "success": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0
    }
    
    for test_file, description in test_files:
        print(f"\n{'='*70}")
        print(f"실행 중: {description}")
        print(f"파일: {test_file}")
        print(f"{'='*70}\n")
        
        success, output, error = run_test_file(test_file)
        
        # 결과 파싱
        parsed = parse_test_results(output)
        parsed["file"] = test_file
        parsed["description"] = description
        parsed["success"] = success
        parsed["output"] = output[-500:] if len(output) > 500 else output  # 마지막 500자만
        parsed["error"] = error[-500:] if len(error) > 500 else error
        
        results.append(parsed)
        
        # 통계 누적
        total_stats["total"] += parsed["total"]
        total_stats["success"] += parsed["success"]
        total_stats["failures"] += parsed["failures"]
        total_stats["errors"] += parsed["errors"]
        total_stats["skipped"] += parsed["skipped"]
        
        # 결과 출력
        if success:
            print(f"[PASS] {description}: 통과")
            print(f"   테스트 수: {parsed['total']}, 성공: {parsed['success']}")
        else:
            print(f"[FAIL] {description}: 실패")
            print(f"   테스트 수: {parsed['total']}, 실패: {parsed['failures']}, 오류: {parsed['errors']}")
            if error:
                print(f"   오류 메시지: {error[:200]}...")
    
    # 최종 결과 출력
    print(f"\n{'='*70}")
    print("전체 테스트 결과 요약")
    print(f"{'='*70}\n")
    
    print(f"총 테스트 수: {total_stats['total']}")
    print(f"성공: {total_stats['success']}")
    print(f"실패: {total_stats['failures']}")
    print(f"오류: {total_stats['errors']}")
    print(f"스킵: {total_stats['skipped']}")
    
    if total_stats['total'] > 0:
        success_rate = (total_stats['success'] / total_stats['total']) * 100
        print(f"\n통과율: {success_rate:.1f}%")
    
    print(f"\n종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # 상세 결과
    print("\n상세 결과:")
    for result in results:
        status = "[PASS]" if result["success"] else "[FAIL]"
        print(f"{status} {result['description']}: {result['total']}개 테스트")
        if result["failures"] > 0 or result["errors"] > 0:
            print(f"   실패: {result['failures']}, 오류: {result['errors']}")
    
    # 실패한 테스트가 있으면 종료 코드 1
    if total_stats['failures'] > 0 or total_stats['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

