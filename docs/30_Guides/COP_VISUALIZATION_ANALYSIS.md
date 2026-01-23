# 전술상황도(COP) 시각화 분석 및 개선 보고서

## 1. 현황 분석 (Current Status)

현재 `ui/components/tactical_map.py` 코드를 기반으로 분석한 시스템의 시각화 구현 현황입니다.

### 1.1 기술 스택
- **기반 기술**: Streamlit Component (HTML/JS embedding)
- **지도 엔진**: Leaflet Library (v1.9.4)
- **군사 부호**: `milsymbol.js` (v2.0.0)
- **타일셋**: CartoDB Dark Matter (Palantir 스타일의 Dark Mode 구현) + Satellite

### 1.2 MIL-STD-2525D 구현 수준
현재 코드는 `milsymbol.js`를 사용하여 SIDC(Symbol ID Code) 기반의 아이콘을 생성하고 있습니다.

```javascript
// 현재 구현 코드 (ui/components/tactical_map.py)
const sym = new ms.Symbol(sidc, { size: size, icon: true, frame: false });
```

- **SIDC 지원**: ✅ 위협/아군 부대의 SIDC 코드를 받아 부호 생성 (양호)
- **프레임(Frame)**: ❌ `frame: false` 옵션으로 인해 피아식별 프레임(다이아몬드, 사각형 등)이 비활성화됨
- **수식 정보(Modifiers)**: ❌ 부호 주변의 수식 정보(부대명, 속도, 방향, 상태 등)가 시각화되지 않음
- **전술적 그래픽**: ⚠️ 단순 선/면(Polyline/Polygon)으로 구현되어 있으며, MIL-STD-2525D의 복잡한 전술 그래픽 표준(예: 화살표 머리 모양, 경계선 스타일 등)을 완전히 따르지는 않음

### 1.3 UI/UX 스타일
- **Palantir 스타일**: ✅ Glassmorphism(반투명/블러) 패널, Dark Mode 지도, 간결한 타이포그래피(Inter 폰트) 적용
- **인터랙션**: ✅ 줌/팬, 타임라인 슬라이더, 레이어 토글, 툴팁/팝업 지원

---

## 2. Palantir 등 선진 체계와의 비교 분석

Palantir Gotham 또는 최신 C4I 체계와 비교했을 때의 적절성 및 차이점입니다.

| 구분 | 현재 구현 (Current) | Palantir / 선진 C4I 스타일 | 비교 평가 |
|------|-------------------|----------------------------|-----------|
| **부호 표현** | **약식 아이콘 (Icon Only)**<br>- 프레임 없음<br>- 내부 아이콘만 표시 | **정규 전술 부호 (Full Symbol)**<br>- 피아식별 프레임(Frame) 필수<br>- 작전 상태/제원 표시 | **직관성은 높으나 표준 준수는 미흡**<br>현재 방식은 현대적이고 깔끔해 보이나, 군사 표준 관점에서는 정보량이 부족함 |
| **수식 정보** | **마우스 오버(Tooltip) 의존**<br>- 텍스트로 별도 표시 | **부호 주변 매핑 (Modifiers)**<br>- T(부대명), V(유형), H(추가정보) 등<br>- 표준 위치에 텍스트 렌더링 | **즉각적 정보 인지 제한**<br>표준 위치에 텍스트가 없어 숙련된 지휘관이 한눈에 정보를 파악하기 어려움 |
| **전술 그래픽** | **기본 도형 (Basic Shapes)**<br>- 선, 점, 면, 화살표 | **표준 그래픽 (Standard)**<br>- 기동 축선, 통제선 등 규격화<br>- 자동화된 그래픽 생성 | **표현의 한계**<br>단순 축선은 무리 없으나 복잡한 전술적 의도 표현에는 한계 존재 |
| **밀집도 처리** | **개별 표시 (Overlap)**<br>- 다수 부대 겹침 발생 | **클러스터링 (Clustering)**<br>- '3' 등으로 묶음 표시<br>- 줌 레벨별 상세화 | **대규모 부대 표현 시 가시성 저하 우려** |

---

## 3. 개선 권장사항 (Recommendations)

Palantir의 **"Data Density(데이터 밀집도)"**와 **"Analysis(분석)"** 철학을 유지하면서 MIL-STD-2525D 표준을 준수하기 위한 단계별 개선 방안입니다.

### 3.1 단기 개선 (High Priority) - "Look & Feel 강화"

**1. 프레임 활성화 및 옵션 조정**
가장 시급한 것은 표준 프레임의 복원입니다. 단, Palantir 스타일의 현대적인 느낌을 위해 선 두께나 색상을 조정할 수 있습니다.
```javascript
// 권장 변경 코드
const sym = new ms.Symbol(sidc, { 
    size: size, 
    frame: true,  // 프레임 활성화 (중요)
    fill: true,   // 내부 채움
    monoColor: props.type === 'RED' ? '#ff4d4d' : '#3498db', // Palantir 스타일 네온 컬러 적용 가능
});
```

**2. 핵심 수식 정보(Modifiers) 시각화**
모든 정보를 다 표시하면 지도가 지저분해지므로, **핵심 정보(부대명, 고유번호)**만 선별하여 부호 위/아래에 표시합니다.
```javascript
const sym = new ms.Symbol(sidc, { 
    uniqueDesignation: props.name, // field T: 부대명/호칭
    higherFormation: props.parent, // field M: 상급부대
    // direction: props.direction, // field Q: 이동방향 (화살표)
});
```

### 3.2 중기 개선 - "전술적 깊이 확보"

**3. 이동 방향 및 속도 벡터 시각화**
정적인 부호가 아니라 **"살아있는 전장(Living Battlefield)"** 느낌을 주기 위해, 이동 중인 부대에 속도 벡터(Velocity Vector)나 방향 화살표를 추가합니다. `milsymbol`의 `direction` 옵션을 활용합니다.

**4. 상태 정보(Status) 반영**
부대의 전투력 수준이나 상태를 부호 자체에 반영합니다.
- 예: 정비 필요 시 프레임 점선 처리, 피해 발생 시 Bar gauge 표시 등 (Palantir는 부호 옆에 얇은 Health Bar를 자주 사용)

### 3.3 장기 개선 - "고급 시각화"

**5. 동적 디클러터링 (Dynamic Decluttering)**
줌 레벨에 따라 부호를 통합(Aggregate)하거나 단순화하는 로직을 추가합니다.
- Zoom Out: 소대 -> 중대 -> 대대 급으로 부호 자동 변경 (SIDC의 Echelon 코드 동적 변경)

## 4. 종합 의견

현재 구현된 시각화는 **"현대적 웹 인터페이스(Modern Web UI)"** 관점에서는 매우 우수하며, 일반 사용자에게는 깔끔한 경험을 제공합니다. 특히 Glassmorphism 패널과 Dark Mode 지도는 Palantir의 미학을 잘 따르고 있습니다.

그러나 **"전문 군사 도구(Professional Military Tool)"** 관점에서는 정보 전달의 밀도(Density)가 다소 낮습니다. 지휘관은 툴팁을 찍어보지 않고도 부호의 모양과 주변 텍스트만으로 상황을 인지하는데 익숙하기 때문입니다.

따라서 **SIDC 아이콘 생성 시 `frame: true`로 변경하고 `uniqueDesignation` 등 최소한의 텍스트 수식 정보를 추가**하는 것만으로도, 표준 준수와 시각적 완성도라는 두 마리 토끼를 잡을 수 있을 것으로 판단됩니다.


## 4. 기존 데이터베이스(Excel) 적합성 상세 분석 (Database Adequacy Analysis)

현재 시스템에서 운용 중인 데이터 테이블(`아군부대현황`, `위협상황` 등)을 실제 지휘통제(C2) 시스템의 DB로 가정하고, MIL-STD-2525D 시각화 지원을 위한 적합성을 분석했습니다.

### 4.1 아군부대현황 (Friendly Units Table)
*   **현재 구조**: `[아군부대ID, 부대명, 제대, 병종, 전투력지수, 배치축선ID, 배치지형셀ID, 가용상태, 임무역할, 좌표정보]`
*   **적합성 평가**:
    *   **식별성 (Identification)**: `부대명`, `제대`, `병종` 필드가 있어 기본 부호(SIDC) 생성에는 문제가 없습니다.
    *   **계층 구조 (Hierarchy)**: `제대` 필드는 있으나, 상급 부대와의 연결 고리(`상급부대ID` 또는 `HigherFormation`)가 명시적이지 않아 지휘 체계 시각화(Command Hierarchy) 및 부호 우측 수식 정보(Field M) 표현이 제한적입니다.
    *   **동적 상태 (Dynamics)**: `전투력지수`는 있으나, `이동방향(Direction)`, `이동속도(Speed)` 필드가 부재하여 "기동 중인 부대"를 표현할 수 없습니다. 이는 정적인 상황도에 그치게 만드는 주된 요인입니다.
    *   **관계성 (Relationship)**: `배치축선ID`, `배치지형셀ID`를 통해 지형 및 작전 축선과의 외래키(Foreign Key) 관계는 잘 정의되어 있습니다.

### 4.2 위협상황 (Threats Table)
*   **현재 구조**: `[위협ID, 위협명, 발생시각, 위협유형코드, 관련축선ID, 발생위치셀ID, 관련_적부대ID, 위협수준, ...]`
*   **적합성 평가**:
    *   **연계성 (Linkage)**: `관련_적부대ID`를 통해 `적군부대현황` 테이블과 연결되는 구조는 우수합니다. 이를 통해 적 부대의 상세 정보(규모, 제대 등)를 위협 부호에 상속받을 수 있습니다.
    *   **시계열 (TimeSeries)**: `발생시각` 필드가 존재하여, 타임라인 기능을 지원할 수 있는 기반이 마련되어 있습니다.
    *   **공간 정보 (Spatial)**: `발생위치셀ID`와 `좌표정보`가 혼용되고 있어, 상황에 따라 좌표 우선순위 처리가 필요합니다. MIL-STD 부호 표시를 위해서는 명확한 좌표값이 필수적입니다.

### 4.3 종합 결론 및 제언
현재 DB 구조는 **"정적인 작전 계획(Static Planning)"** 수립에는 적합하게 설계되어 있으나, 시간에 따라 변화하는 **"동적인 전장 상황(Dynamic COP)"**을 표현하기에는 일부 필드가 부족합니다.

특히 MIL-STD-2525D의 핵심인 **"상태 정보(Status)"**와 **"기동 정보(Mobility)"**를 표현하기 위해, 5장에서 제안하는 데이터 구조 확장이 필수적입니다. 기존 테이블의 관계(FK)는 유지하되, 속성 컬럼만 추가하는 방식이므로 기존 시스템에 대한 영향은 최소화할 수 있습니다.


위의 시각화 개선이 실질적인 효과를 거두기 위해서는 **"데이터가 존재해야"** 합니다. 현재 테이터셋에는 부대명(Name)과 위치(Lat/Lon) 외에 MIL-STD-2525D 수식 정보(Modifiers)를 표현할 필드가 부족합니다.

다음과 같이 데이터 구조 개선을 제안합니다.

### 5.1 Excel 메타데이터 필드 확장
`아군부대.xlsx` 및 `위협상황.xlsx` (또는 해당 정보를 생성하는 `Prompt Template`)에 다음 컬럼을 추가해야 합니다.

| MIL-STD 필드 | 컬럼명 (Excel) | 데이터 타입 | 예시 값 | 용도 |
|:---:|---|---|---|---|
| **T** | **UniqueDesignation** (고유명칭) | String | `1-2-A` | 부호 좌측 하단 표시 (소대-중대-대대 식별) |
| **M** | **HigherFormation** (상급부대) | String | `72 Bde` | 부호 우측 표시 (소속 부대) |
| **Q** | **Direction** (이동방향) | Float | `270.0` | 부호 중앙 화살표 (이동 방향, Degree) |
| **Z** | **Speed** (이동속도) | Float | `45.0` | 부호 측면 속도 벡터 (km/h) |
| **L** | **Status** (상태) | String | `Operational` | 프레임 점선 처리 (Operational, Damaged 등) |
| **K** | **CombatEffectiveness** (전투력) | Float | `0.85` | 부호 측면 Bar Gauge (0.0~1.0) |

### 5.2 온톨로지 스키마(Ontology Schema) 업데이트
`Unit` 및 `Threat` 클래스에 대한 Property 확장이 필요합니다.

```ttl
# Unit/Threat Properties
ns:uniqueDesignation a owl:DatatypeProperty ;
    rdfs:domain ns:Unit ;
    rdfs:range xsd:string .

ns:higherFormation a owl:DatatypeProperty ;
    rdfs:domain ns:Unit ;
    rdfs:range xsd:string .

ns:moveDirection a owl:DatatypeProperty ; # Field Q
    rdfs:domain ns:Unit ;
    rdfs:range xsd:float .

ns:combatEffectiveness a owl:DatatypeProperty ; # Field K
    rdfs:domain ns:Unit ;
    rdfs:range xsd:float .
```

### 5.3 Backend Mapper 로직 보강
`ScenarioMapper.py`에서 위 필드들을 GeoJSON `properties`로 매핑하도록 수정합니다.

```python
# ui/components/scenario_mapper.py 예시

feature = {
    "type": "Feature",
    "properties": {
        # 기존 필드 ...
        "sidc": sidc,
        
        # [NEW] MIL-STD-2525D Modifiers
        "uniqueDesignation": unit.get("unique_designation") or unit.get("고유명칭"), # Field T
        "higherFormation": unit.get("higher_formation") or unit.get("상급부대"), # Field M
        "direction": unit.get("direction") or unit.get("이동방향"), # Field Q
        "speed": unit.get("speed") or unit.get("이동속도"), # Field Z
        # ...
    }
}
```

### 5.4 기대 효과
이러한 데이터 구조 개선이 선행되면, 프론트엔드(`tactical_map.py`)에서 다음과 같은 고급 시각화가 가능해집니다.

1.  **자동화된 부호 생성**: `milsymbol.js`가 T, M 필드를 읽어 자동으로 표준 위치에 텍스트 배치
2.  **동적 상황판**: 정지된 아이콘이 아니라, 방향(Q)과 속도(Z)를 가진 "움직이는 상황판" 구현 가능
3.  **상세 정보 인지**: 툴팁 클릭 없이도 "72여단 소속 1대대(손실율 20%)"와 같은 정보를 직관적으로 파악 가능
