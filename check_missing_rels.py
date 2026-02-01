import urllib.request
import json

KNOWN_RELATIONS = {
    'has전장축선', 'locatedIn', 'respondsTo', 'hasRelatedCOA', 'requiresResource',
    'hasConstraint', 'compatibleWith', 'has지형셀', 'appliesTo', 'assignedToMission',
    'hasMission', 'has위협상황', 'has적군부대현황', 'referencesAsset', 'relatedTo',
    'hasType', 'has임무정보', '위협유형코드', 'incompatibleWith', 'isVirtualEntity',
    'virtualEntitySource', '포함됨In', '배치된부대', '소속축선', '할당부대', '인접함',
    '협력관계', '축선연결', '작전가능지역', '위협영향지역', '임무축선', '시나리오적군',
    'sameAs', 'subPropertyOf', 'equivalentClass', 'subClassOf', 'domain', 'range'
}

def check_missing():
    url = "http://localhost:8000/api/v1/ontology/graph?mode=instances"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.load(resp)
            links = data.get("links", [])
            relsInUse = set(l.get("relation") for l in links if l.get("relation"))
            missing = relsInUse - KNOWN_RELATIONS
            return sorted(list(missing))
    except Exception as e:
        return [f"Error: {e}"]

missing = check_missing()
print("Missing relations in RELATION_STYLES:")
for m in missing:
    print(f" - {m}")
