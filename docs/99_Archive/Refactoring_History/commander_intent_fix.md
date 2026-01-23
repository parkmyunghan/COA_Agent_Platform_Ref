# ACTIVE MISSION 지휘관 의도 정보 표시 문제 수정

## 문제점 분석

### 현재 상태
- ACTIVE MISSION 영역에 MSN001이 표시됨
- "지휘관 의도 정보가 없습니다." 메시지가 표시됨

### 원인
1. **백엔드 데이터 반환 누락**:
   - `coa_service.py`의 `get_available_missions()` 메서드에서 `commander_intent` 필드를 반환하지 않음
   - 현재: `mission_id`, `mission_name`, `description`만 반환
   - 누락: `commander_intent`, `mission_type`, `primary_axis_id` 필드

2. **Excel 데이터는 존재**:
   - Excel 파일(`임무정보.xlsx`)에는 '지휘관의도' 컬럼이 존재함
   - `excel_columns.json`과 `schema_registry.yaml`에서 확인됨

3. **API 엔드포인트는 필드를 기대**:
   - `api/routers/data.py`의 `get_missions()` 엔드포인트는 `m.get('commander_intent')`를 사용
   - 하지만 `get_available_missions()`에서 반환하는 딕셔너리에 `commander_intent`가 없어 항상 `None`이 됨

## 수정 내용

### 1. pandas import 추가

**파일**: `core_pipeline/coa_service.py`

**변경 사항**:
- pandas import 추가 (NaN 값 처리용)

```python
import pandas as pd
```

### 2. get_available_missions() 메서드 개선

**파일**: `core_pipeline/coa_service.py`

**변경 사항**:
- `commander_intent` 필드 추가
- `mission_type`, `primary_axis_id` 필드 추가
- NaN 및 빈 값 처리 로직 추가

```python
def get_available_missions(self) -> List[Dict]:
    """
    사용 가능한 임무 목록 조회
    
    Returns:
        임무 정보 리스트 [{"mission_id": "...", "mission_name": "...", ...}]
    """
    try:
        missions_df = self.data_manager.load_table('임무정보')
        if missions_df is None or missions_df.empty:
            return []
        
        missions = []
        for _, row in missions_df.iterrows():
            # 지휘관의도 컬럼에서 값을 가져옴
            commander_intent_val = row.get('지휘관의도', '')
            # NaN 또는 빈 값 처리
            if pd.isna(commander_intent_val) or (isinstance(commander_intent_val, str) and commander_intent_val.strip() == ''):
                commander_intent = None
            else:
                commander_intent = str(commander_intent_val).strip()
            
            # 임무종류 처리
            mission_type_val = row.get('임무종류', '')
            mission_type = None
            if not pd.isna(mission_type_val) and str(mission_type_val).strip():
                mission_type = str(mission_type_val).strip()
            
            # 주공축선ID 처리
            primary_axis_id_val = row.get('주공축선ID', '')
            primary_axis_id = None
            if not pd.isna(primary_axis_id_val) and str(primary_axis_id_val).strip():
                primary_axis_id = str(primary_axis_id_val).strip()
            
            # 임무설명 처리
            description_val = row.get('임무설명', '')
            description = None
            if not pd.isna(description_val) and str(description_val).strip():
                description = str(description_val).strip()
            
            missions.append({
                "mission_id": str(row.get('임무ID', '')),
                "mission_name": str(row.get('임무명', '')),
                "mission_type": mission_type,
                "commander_intent": commander_intent,
                "primary_axis_id": primary_axis_id,
                "description": description
            })
        return missions
    except Exception as e:
        print(f"[ERROR] Failed to load missions: {e}")
        return []
```

## 데이터 필드 매핑

### Excel 컬럼 → API 필드

| Excel 컬럼 | API 필드 | 처리 방식 |
|-----------|---------|----------|
| `임무ID` | `mission_id` | 문자열 변환 |
| `임무명` | `mission_name` | 문자열 변환 |
| `임무종류` | `mission_type` | NaN/빈 값 처리 후 문자열 변환 |
| `지휘관의도` | `commander_intent` | NaN/빈 값 처리 후 문자열 변환 |
| `주공축선ID` | `primary_axis_id` | NaN/빈 값 처리 후 문자열 변환 |
| `임무설명` | `description` | NaN/빈 값 처리 후 문자열 변환 |

## 수정된 파일

1. `core_pipeline/coa_service.py`
   - pandas import 추가
   - `get_available_missions()` 메서드에 `commander_intent` 필드 추가
   - `mission_type`, `primary_axis_id` 필드 추가
   - NaN 및 빈 값 처리 로직 추가

## 테스트 방법

### 1. 백엔드 API 테스트
1. 백엔드 서버 재시작
2. `/api/v1/data/missions` 엔드포인트 호출
3. 응답에서 `commander_intent` 필드 확인:
   ```json
   {
     "missions": [
       {
         "mission_id": "MSN001",
         "mission_name": "...",
         "commander_intent": "실제 지휘관 의도 내용",
         ...
       }
     ]
   }
   ```

### 2. 프론트엔드 표시 테스트
1. 프론트엔드 새로고침
2. ACTIVE MISSION 영역 확인
3. MSN001 아래에 실제 지휘관 의도 내용이 표시되는지 확인:
   - ✅ "실제 지휘관 의도 내용"
   - ❌ "지휘관 의도 정보가 없습니다."

### 3. 데이터 검증
1. Excel 파일(`임무정보.xlsx`)에서 MSN001 행 확인
2. '지휘관의도' 컬럼에 값이 있는지 확인
3. 값이 있으면 프론트엔드에 표시되어야 함

## 예상 결과

- ✅ ACTIVE MISSION 영역에 실제 지휘관 의도 내용 표시
- ✅ "지휘관 의도 정보가 없습니다." 메시지가 표시되지 않음 (데이터가 있는 경우)
- ✅ Excel 파일에 지휘관 의도 정보가 없으면 여전히 "지휘관 의도 정보가 없습니다." 표시 (정상 동작)
- ✅ NaN 및 빈 값 처리로 안정적인 데이터 반환

## 참고 사항

- Excel 파일에 '지휘관의도' 컬럼이 있고 값이 있어야 프론트엔드에 표시됨
- Excel 파일에 값이 없거나 NaN이면 "지휘관 의도 정보가 없습니다."가 표시됨 (의도된 동작)
- `api/routers/data.py`의 `get_missions()` 엔드포인트는 이미 `commander_intent` 필드를 처리하도록 구현되어 있음
