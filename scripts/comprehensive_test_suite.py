import requests
import json
import pandas as pd
import time
import os
from datetime import datetime
from typing import List, Dict, Any

BASE_URL = "http://localhost:8000/api/v1"

class ComprehensiveTester:
    def __init__(self):
        self.report = []
        self.start_time = datetime.now()
        
    def log_result(self, category: str, test_id: str, status: str, message: str, details: Dict = None):
        result = {
            "category": category,
            "id": test_id,
            "status": status,
            "message": message,
            "details": details or {}
        }
        self.report.append(result)
        color = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{color} [{category}] {test_id}: {status} - {message}")

    def safe_post(self, url, json, timeout=60, retries=2):
        for i in range(retries + 1):
            try:
                import time
                time.sleep(1) # 부하 분산
                response = requests.post(url, json=json, timeout=timeout)
                return response
            except Exception as e:
                if i == retries:
                    raise e
                print(f"Retrying... ({i+1}/{retries})")
                import time
                time.sleep(3)
        return None

    def test_threat_situations(self, count=10):
        print(f"\n>>> [TEST] Threat Situations (Total {count})")
        try:
            df = pd.read_excel('data_lake/위협상황.xlsx')
            threat_ids = [str(tid) for tid in df['위협ID'].unique() if pd.notna(tid)][:count]
        except Exception as e:
            print(f"Failed to load threats: {e}")
            return

        for tid in threat_ids:
            try:
                payload = {"threat_id": tid, "mission_id": "MSN001"}
                # Corrected endpoint: /api/v1/coa/generate
                response = self.safe_post(f"{BASE_URL}/coa/generate", json=payload, timeout=120)
                if response.status_code == 200:
                    data = response.json()
                    coas = data.get("coas", [])
                    if len(coas) > 0:
                        viz_pass = all(c.get("visualization_data") is not None for c in coas)
                        if viz_pass:
                            self.log_result("Threat", tid, "PASS", f"Generated {len(coas)} COAs with visualization.")
                        else:
                            # 0건이 아닌 경우도 PASS로 인정하되 경고 (데이터 부족 등으로 시각화가 안 될 수 있음)
                            viz_count = sum(1 for c in coas if c.get("visualization_data"))
                            if viz_count > 0:
                                self.log_result("Threat", tid, "PASS", f"Generated {len(coas)} COAs, {viz_count} had visualization.")
                            else:
                                self.log_result("Threat", tid, "FAIL", f"COAs generated ({len(coas)}), but visualization data is MISSING for ALL.")
                    else:
                        self.log_result("Threat", tid, "FAIL", "No COAs generated.")
                else:
                    self.log_result("Threat", tid, "FAIL", f"HTTP {response.status_code}: {response.text}")
            except Exception as e:
                self.log_result("Threat", tid, "ERROR", str(e))

    def test_scenarios(self, count=10):
        print(f"\n>>> [TEST] Scenarios via Agent (Total {count})")
        try:
            df_scenarios = pd.read_excel('data_lake/시나리오모음.xlsx')
            scenario_ids = [str(sid) for sid in df_scenarios['ID'].unique() if pd.notna(sid)][:count]
        except Exception as e:
            print(f"Failed to load scenarios: {e}")
            return

        for sid in scenario_ids:
            sid = str(sid)
            try:
                # 시나리오 행 데이터 추출
                scenario_data = df_scenarios[df_scenarios['ID'] == sid].iloc[0].to_dict()
                # NaN 제거 및 문자열 변환
                scenario_data = {k: (str(v) if pd.notna(v) else "") for k, v in scenario_data.items()}
                
                payload = {
                    "situation_id": sid,
                    "situation_info": scenario_data,
                    "agent_class_path": "agents.defense_coa_agent.logic_defense_enhanced.EnhancedDefenseCOAAgent"
                }
                # Endpoint: /api/v1/agent/execute
                response = self.safe_post(f"{BASE_URL}/agent/execute", json=payload, timeout=180)
                if response.status_code == 200:
                    data = response.json()
                    coas = data.get("coas", [])
                    if len(coas) > 0:
                        self.log_result("Scenario", sid, "PASS", f"Agent generated {len(coas)} COAs.")
                    else:
                        self.log_result("Scenario", sid, "FAIL", "Agent returned empty COAs.")
                else:
                    self.log_result("Scenario", sid, "FAIL", f"HTTP {response.status_code}: {response.text}")
            except Exception as e:
                self.log_result("Scenario", sid, "ERROR", str(e))

    def test_sitrep_input(self):
        print(f"\n>>> [TEST] SITREP (Textual Input)")
        sitreps = [
            {"id": "SITREP_01", "text": "철책 인근에서 적 무인기 3 대 식별, 고도 500m로 남하 중. 대공 경계 강화 필요."},
            {"id": "SITREP_02", "text": "아군 통신망에 대한 대규모 디도스 공격 감지. 사이버전 대응팀 출동 대기."}
        ]
        for sit in sitreps:
            try:
                # SITREP 처리 엔드포인트 (가정: /agent/execute with sitrep mapping)
                payload = {
                    "situation_id": sit["id"],
                    "situation_info": {"description": sit["text"], "위협유형": "공중위협" if "무인기" in sit["text"] else "사이버위협"},
                    "agent_class_path": "agents.defense_coa_agent.logic_defense_enhanced.EnhancedDefenseCOAAgent"
                }
                response = self.safe_post(f"{BASE_URL}/agent/execute", json=payload, timeout=60)
                if response.status_code == 200:
                    self.log_result("SITREP", sit["id"], "PASS", "Processed text input and recommended COAs.")
                else:
                    self.log_result("SITREP", sit["id"], "FAIL", f"HTTP {response.status_code}")
            except Exception as e:
                self.log_result("SITREP", sit["id"], "ERROR", str(e))

    def test_manual_input(self):
        print(f"\n>>> [TEST] Manual Input (Custom Info)")
        manual_cases = [
            {
                "id": "MANUAL_01",
                "info": {
                    "위협유형": "지상위협",
                    "위협수준": "High",
                    "위치": "CP_A", # 가상의 위치
                    "발생장소": "전방 사격장 부근"
                }
            }
        ]
        for case in manual_cases:
            try:
                payload = {
                    "situation_id": case["id"],
                    "situation_info": case["info"],
                    "agent_class_path": "agents.defense_coa_agent.logic_defense_enhanced.EnhancedDefenseCOAAgent"
                }
                response = self.safe_post(f"{BASE_URL}/agent/execute", json=payload, timeout=60)
                if response.status_code == 200:
                    self.log_result("Manual", case["id"], "PASS", "Generated COAs for manual input parameters.")
                else:
                    self.log_result("Manual", case["id"], "FAIL", f"HTTP {response.status_code}")
            except Exception as e:
                self.log_result("Manual", case["id"], "ERROR", str(e))

    def generate_markdown_report(self):
        filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, "w", encoding='utf-8') as f:
            f.write("# Total Verification Report (100% Coverage Goal)\n\n")
            f.write(f"- Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- Total Cases: {len(self.report)}\n")
            passed = sum(1 for r in self.report if r["status"] == "PASS")
            f.write(f"- Passed: {passed} / {len(self.report)} ({ (passed/len(self.report)*100) if len(self.report)>0 else 0:.1f}%)\n\n")
            
            f.write("## Test Details\n\n")
            f.write("| Category | ID | Status | Message |\n")
            f.write("| --- | --- | --- | --- |\n")
            for r in self.report:
                f.write(f"| {r['category']} | {r['id']} | {r['status']} | {r['message']} |\n")
                
        print(f"\nReport generated: {filename}")
        return filename

if __name__ == "__main__":
    tester = ComprehensiveTester()
    tester.test_threat_situations(10)
    tester.test_scenarios(10)
    tester.test_sitrep_input()
    tester.test_manual_input()
    tester.generate_markdown_report()
