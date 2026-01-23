"""
성능 메트릭 수집 시스템
Phase 3.3: 성능 메트릭 수집
"""
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class PerformanceMetric:
    """성능 메트릭 데이터 클래스"""
    timestamp: str
    operation: str
    duration_ms: float
    success: bool
    details: Dict = None
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'timestamp': self.timestamp,
            'operation': self.operation,
            'duration_ms': round(self.duration_ms, 2),
            'success': self.success,
            'details': self.details or {}
        }


class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(self, log_dir: str = "logs/metrics"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.metrics: List[PerformanceMetric] = []
        self.logger = logging.getLogger(__name__)
    
    def measure(self, operation: str):
        """데코레이터: 함수 실행 시간 측정"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = False
                error = None
                result = None
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                except Exception as e:
                    error = str(e)
                    raise
                finally:
                    duration = (time.time() - start_time) * 1000  # ms
                    
                    metric = PerformanceMetric(
                        timestamp=datetime.now().isoformat(),
                        operation=operation,
                        duration_ms=duration,
                        success=success,
                        details={'error': error} if error else {}
                    )
                    
                    self.record(metric)
                    
                    # 로깅
                    if success:
                        self.logger.info(f"✅ {operation}: {duration:.2f}ms")
                    else:
                        self.logger.error(f"❌ {operation}: {duration:.2f}ms (실패: {error})")
                
                return result
            return wrapper
        return decorator
    
    def record(self, metric: PerformanceMetric):
        """메트릭 기록"""
        self.metrics.append(metric)
    
    def record_manual(self, operation: str, duration_ms: float, success: bool = True, details: Dict = None):
        """수동 메트릭 기록"""
        metric = PerformanceMetric(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            details=details
        )
        self.record(metric)
    
    def save_metrics(self, filename: str = None):
        """메트릭을 JSON 파일로 저장"""
        if not filename:
            filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.log_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(
                [m.to_dict() for m in self.metrics],
                f,
                indent=2,
                ensure_ascii=False
            )
        
        self.logger.info(f"📊 메트릭 저장: {filepath}")
        return str(filepath)
    
    def get_summary(self) -> Dict:
        """성능 요약 통계"""
        if not self.metrics:
            return {'message': '수집된 메트릭 없음'}
        
        # 작업별 그룹화
        ops = {}
        for m in self.metrics:
            if m.operation not in ops:
                ops[m.operation] = {
                    'count': 0,
                    'total_duration': 0,
                    'success_count': 0,
                    'durations': []
                }
            
            ops[m.operation]['count'] += 1
            ops[m.operation]['total_duration'] += m.duration_ms
            if m.success:
                ops[m.operation]['success_count'] += 1
            ops[m.operation]['durations'].append(m.duration_ms)
        
        # 통계 계산
        summary = {}
        for op, data in ops.items():
            durations = sorted(data['durations'])
            avg = data['total_duration'] / data['count']
            
            summary[op] = {
                '호출_횟수': data['count'],
                '성공률': f"{data['success_count'] / data['count'] * 100:.1f}%",
                '평균_시간_ms': round(avg, 2),
                '최소_시간_ms': round(min(durations), 2),
                '최대_시간_ms': round(max(durations), 2),
                'p50_ms': round(durations[len(durations)//2], 2),
                'p95_ms': round(durations[int(len(durations)*0.95)], 2) if len(durations) > 1 else round(durations[0], 2)
            }
        
        return summary
    
    def print_summary(self):
        """요약 출력"""
        summary = self.get_summary()
        
        print("\n" + "=" * 80)
        print("성능 메트릭 요약")
        print("=" * 80)
        
        if 'message' in summary:
            print(summary['message'])
            return
        
        for op, stats in summary.items():
            print(f"\n📊 {op}:")
            for key, value in stats.items():
                print(f"  - {key}: {value}")
        
        print("\n" + "=" * 80)


# 사용 예시 및 테스트
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] %(message)s')
    
    monitor = PerformanceMonitor()
    
    print("=" * 80)
    print("성능 모니터링 시스템 테스트")
    print("=" * 80)
    
    # COA 평가 시스템 성능 측정
    try:
        from core_pipeline.coa_scorer import COAScorer
        from core_pipeline.relevance_mapper import RelevanceMapper
        from core_pipeline.resource_priority_parser import ResourcePriorityParser
        
        # 1. RelevanceMapper 초기화 측정
        start = time.time()
        mapper = RelevanceMapper()
        duration = (time.time() - start) * 1000
        monitor.record_manual("RelevanceMapper 초기화", duration)
        
        # 2. ResourcePriorityParser 초기화 측정
        start = time.time()
        parser = ResourcePriorityParser()
        duration = (time.time() - start) * 1000
        monitor.record_manual("ResourcePriorityParser 초기화", duration)
        
        # 3. COAScorer 초기화 측정
        start = time.time()
        scorer = COAScorer(coa_type="defense")
        duration = (time.time() - start) * 1000
        monitor.record_manual("COAScorer 초기화", duration)
        
        # 4. 관련성 점수 계산 측정 (10회)
        for i in range(10):
            start = time.time()
            score = mapper.get_relevance_score(
                coa_id=f"COA_DEF_{i:03d}",
                coa_type="Defense",
                threat_id=f"THR{i:03d}",
                threat_type="침투"
            )
            duration = (time.time() - start) * 1000
            monitor.record_manual("관련성 점수 계산", duration, details={'score': score})
        
        # 5. 자원 우선순위 파싱 측정 (10회)
        test_strings = [
            "포병대대(필수), 보병여단(권장)",
            "전차대대(필수), 공병대대(선택)",
            "특수전팀(필수), 사이버전팀(권장), 정보부대(선택)",
        ]
        for i in range(10):
            test_str = test_strings[i % len(test_strings)]
            start = time.time()
            result = parser.parse_resource_priority(test_str)
            duration = (time.time() - start) * 1000
            monitor.record_manual("자원 우선순위 파싱", duration, details={'parsed_count': len(result)})
        
        # 6. COA 점수 계산 측정 (5회)
        for i in range(5):
            context = {
                'coa_uri': f'http://example.org#COA_DEF_{i:03d}',
                'coa_id': f'COA_DEF_{i:03d}',
                'coa_type': 'Defense',
                'threat_type': '침투',
                'threat_level': 0.8,
                'environment_fit': 0.9,
                'expected_success_rate': 0.65,
                'chain_info': {'chains': [{'path': 'c1', 'avg_confidence': 0.7}]},
                'resource_priority_string': '포병대대(필수), 보병여단(권장)',
                'available_resources': [
                    {'resource_name': '포병대대', 'available_quantity': 18, 'status': '사용가능'},
                ],
                'is_first_coa': i == 0
            }
            
            start = time.time()
            result = scorer.calculate_score(context)
            duration = (time.time() - start) * 1000
            monitor.record_manual(
                "COA 종합 점수 계산", 
                duration, 
                details={'total_score': result['total']}
            )
        
        # 요약 출력
        monitor.print_summary()
        
        # 저장
        filepath = monitor.save_metrics()
        print(f"\n✅ 메트릭 파일 저장: {filepath}")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
