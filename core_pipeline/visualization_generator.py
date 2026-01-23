# -*- coding: utf-8 -*-
"""
COP 시각화 데이터 생성 모듈
설계 문서: docs/40_Refactoring/cop_visualization_design.md 기반

업데이트: 2026-01-21 - TERR031 (동해안 휴전선) 추가 지원
"""

from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class VisualizationDataGenerator:
    """COP 시각화 데이터 생성기"""
    
    def __init__(self, data_lake_path: Optional[str] = None):
        """
        Args:
            data_lake_path: data_lake 디렉토리 경로
        """
        if data_lake_path is None:
            base_path = Path(__file__).parent.parent
            self.data_lake_path = base_path / "data_lake"
        else:
            self.data_lake_path = Path(data_lake_path)
    
    def resolve_axis_coordinates(self, axis_id: str) -> Tuple[List[List[float]], Dict[str, Any]]:
        """
        축선 좌표 해결 (3단계 조회)
        
        Args:
            axis_id: 축선 ID
            
        Returns:
            (coordinates, metadata) 튜플
            - coordinates: [[lng, lat], ...] 형식의 좌표 리스트
            - metadata: 축선 메타데이터 (name, type 등)
        """
        try:
            # URI에서 로컬 이름 추출
            if axis_id.startswith("http://") or axis_id.startswith("ns:"):
                axis_id = axis_id.split('#')[-1].split('/')[-1].replace('ns:', '').replace('전장축선_', '')
            
            # 1단계: 축선 정의 조회
            axis_file = self.data_lake_path / "전장축선.xlsx"
            if not axis_file.exists():
                logger.warning(f"Axis file not found: {axis_file}")
                return [], {}
            
            axis_df = pd.read_excel(axis_file)
            axis_row = axis_df[axis_df["축선ID"] == axis_id]
            
            if axis_row.empty:
                logger.warning(f"Axis {axis_id} not found in 전장축선.xlsx")
                return [], {}
            
            # 2단계: 지형셀 경로 파싱
            terrain_path = axis_row.iloc[0].get("주요지형셀목록") or axis_row.iloc[0].get("구성지형셀목록")
            if pd.isna(terrain_path) or not str(terrain_path).strip():
                # 시작/종단 지형셀만 사용
                start_cell_id = axis_row.iloc[0].get("시작지형셀ID")
                end_cell_id = axis_row.iloc[0].get("종단지형셀ID")
                if pd.notna(start_cell_id) and pd.notna(end_cell_id):
                    coordinates = []
                    for cell_id in [start_cell_id, end_cell_id]:
                        coords = self._get_terrain_cell_coordinates(str(cell_id))
                        if coords:
                            coordinates.append(coords)
                    if len(coordinates) >= 2:
                        metadata = {
                            "name": str(axis_row.iloc[0].get("축선명", "")),
                            "type": str(axis_row.iloc[0].get("축선유형", "SECONDARY")),
                        }
                        return coordinates, metadata
                return [], {}
            
            # 3단계: 지형셀 목록 → 좌표 변환
            terrain_ids = [t.strip() for t in str(terrain_path).split(',') if t.strip()]
            coordinates = []
            
            for cell_id in terrain_ids:
                coords = self._get_terrain_cell_coordinates(cell_id)
                if coords:
                    coordinates.append(coords)
            
            metadata = {
                "name": str(axis_row.iloc[0].get("축선명", "")),
                "type": str(axis_row.iloc[0].get("축선유형", "SECONDARY")),
            }
            
            logger.info(f"✅ Resolved axis {axis_id}: {len(coordinates)} waypoints")
            return coordinates, metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to resolve axis {axis_id}: {e}")
            import traceback
            traceback.print_exc()
            return [], {}
    
    def get_all_terrain_cells(self) -> List[Dict[str, Any]]:
        """
        모든 지형셀 정보 반환
        
        Returns:
            [{'cell_id': '...', 'coordinates': [lon, lat], 'name': '...', 'description': '...'}, ...]
        """
        # 캐시가 없으면 로드 시도 (임의의 ID로 조회하여 로드 트리거)
        if not hasattr(self, '_terrain_cache') or self._terrain_cache is None:
            self._get_terrain_cell_coordinates("DUMMY")
            
        if not hasattr(self, '_terrain_cache') or self._terrain_cache is None:
            return []
            
        cells = []
        meta_cache = getattr(self, '_terrain_metadata_cache', {})
        
        for cell_id, coords in self._terrain_cache.items():
            meta = meta_cache.get(cell_id, {})
            cells.append({
                "cell_id": cell_id,
                "coordinates": coords,
                "name": meta.get("name", cell_id),
                "description": meta.get("description", "")
            })
        
        # ID 순 정렬
        return sorted(cells, key=lambda x: x['cell_id'])

    def _get_terrain_cell_coordinates(self, cell_id: str) -> Optional[List[float]]:
        """
        지형셀 ID를 기반으로 경도, 위도 좌표를 반환
        
        Args:
            cell_id: 지형셀 ID (예: 'TERR001')
            
        Returns:
            [longitude, latitude] 또는 None
        """
        if not cell_id:
            return None
            
        # 1. 캐시 확인
        if hasattr(self, '_terrain_cache') and self._terrain_cache is not None:
            if cell_id in self._terrain_cache:
                return self._terrain_cache[cell_id]
            # 공백 제거 후 재확인
            clean_id = str(cell_id).strip().upper()
            if clean_id in self._terrain_cache:
                return self._terrain_cache[clean_id]
        
        try:
            # 2. 캐시가 없으면 지형셀 파일 로드 (최초 1회)
            if not hasattr(self, '_terrain_cache') or self._terrain_cache is None:
                terrain_file = self.data_lake_path / "지형셀.xlsx"
                
                # 경로가 존재하지 않으면 다른 후보군 시도
                if not terrain_file.exists():
                    alternative_paths = [
                        Path("./data_lake/지형셀.xlsx"),
                        Path(os.getcwd()) / "data_lake" / "지형셀.xlsx",
                        Path(__file__).parent.parent.parent / "data_lake" / "지형셀.xlsx"
                    ]
                    for alt in alternative_paths:
                        if alt.exists():
                            terrain_file = alt
                            break
                
                if not terrain_file.exists():
                    logger.warning(f"지형셀 파일을 찾을 수 없습니다: {terrain_file}")
                    return None
                
                # 파일 로드 및 캐시 구축
                terrain_df = pd.read_excel(terrain_file)
                self._terrain_cache = {}
                
                # 지형셀ID 컬럼 찾기 (대소문자 무시)
                id_col = None
                coord_col = None
                for col in terrain_df.columns:
                    col_upper = str(col).upper().replace(" ", "")
                    if col_upper in ['지형셀ID', 'TERRAINCELLID', 'CELLID', 'ID']:
                        id_col = col
                    elif col_upper in ['좌표정보', 'COORDINATES', 'POSITION']:
                        coord_col = col
                
                if id_col and coord_col:
                    if not hasattr(self, '_terrain_metadata_cache'):
                        self._terrain_metadata_cache = {}
                        
                    name_col = next((c for c in terrain_df.columns if str(c).upper().replace(" ", "") in ['지형명', 'NAME', 'TERRAINNAME']), None)
                    desc_col = next((c for c in terrain_df.columns if str(c).upper().replace(" ", "") in ['설명', 'DESCRIPTION', 'DESC']), None)

                    for _, row in terrain_df.iterrows():
                        tid = str(row[id_col]).strip().upper()
                        cinfo = row[coord_col]
                        if tid and not pd.isna(cinfo):
                            coords = self._parse_coord_string(str(cinfo))
                            if coords:
                                self._terrain_cache[tid] = coords
                                # 메타데이터 캐싱
                                self._terrain_metadata_cache[tid] = {
                                    "name": str(row[name_col]) if name_col and pd.notna(row[name_col]) else tid,
                                    "description": str(row[desc_col]) if desc_col and pd.notna(row[desc_col]) else ""
                                }
                
                logger.info(f"지형셀 데이터 로드 완료 ({len(self._terrain_cache)}개 셀)")

            # 3. 다시 캐시에서 검색
            clean_id = str(cell_id).strip().upper()
            return self._terrain_cache.get(clean_id)
            
        except Exception as e:
            logger.error(f"지형셀 좌표 조회 중 오류 발생 (cell_id={cell_id}): {e}")
            return None

    def _parse_coord_string(self, coord_str: str) -> Optional[List[float]]:
        """좌표 문자열 파싱 유틸리티"""
        try:
            parts = [p.strip() for p in str(coord_str).split(',')]
            if len(parts) < 2:
                return None
            
            v1 = float(parts[0])
            v2 = float(parts[1])
            
            # [lon, lat] 순서로 반환 (한국 지역 기준 - 위도 33-43, 경도 124-132)
            if 33 <= v1 <= 43 and 124 <= v2 <= 132:
                return [v2, v1]  # [lon, lat]
            elif 124 <= v1 <= 132 and 33 <= v2 <= 43:
                return [v1, v2]  # [lon, lat]
            
            return [v1, v2] # 기본값
        except:
            return None
    
    def _get_axis_start_position(self, axis_id: str) -> Optional[List[float]]:
        """
        축선의 시작점 좌표를 반환
        
        Args:
            axis_id: 축선 ID (예: 'AXIS01')
            
        Returns:
            [longitude, latitude] 또는 None
        """
        try:
            axis_coords, _ = self.resolve_axis_coordinates(axis_id)
            if axis_coords and len(axis_coords) > 0:
                return axis_coords[0]  # 첫 번째 좌표 (시작점)
            return None
        except Exception as e:
            logger.warning(f"축선 시작점 좌표 조회 실패 (axis_id={axis_id}): {e}")
            return None
    
    def generate_operational_path(
        self,
        coa: Dict[str, Any],
        friendly_units: List[Dict[str, Any]],
        threat_position: Optional[List[float]] = None,
        main_axis_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        방책 작전 경로 생성
        
        Args:
            coa: 방책 정보
            friendly_units: 참여 아군 부대 목록
            threat_position: 위협 위치 [lng, lat]
            main_axis_id: 주요 축선 ID
            
        Returns:
            operational_path 딕셔너리 또는 None
        """
        try:
            waypoints = []
            
            # 1. 출발지: 아군 부대 배치 위치
            start_positions = []
            for unit in friendly_units:
                # 부대 정보가 완전하지 않아도(ID만 있어도) 위치 조회 시도
                pos = self._get_unit_position(unit)
                if pos:
                    start_positions.append(pos)
            
            # 2. 경유지: 축선상의 지형셀
            axis_coords = []
            if main_axis_id:
                axis_coords, _ = self.resolve_axis_coordinates(main_axis_id)
            
            # 출발지 결정 로직 보강
            if start_positions:
                # 여러 부대가 있으면 중심점 계산
                if len(start_positions) == 1:
                    waypoints.append(start_positions[0])
                else:
                    center = self._calculate_center_point(start_positions)
                    waypoints.append(center)
            elif axis_coords and len(axis_coords) >= 1:
                # 부대 위치가 없으면 축선의 시작점을 출발지로 사용 (임의 데이터 아님)
                logger.info(f"No unit positions for {coa.get('coa_id')}, using axis {main_axis_id} start point.")
                waypoints.append(axis_coords[0])
            
            # 축선 경유지 추가
            if axis_coords and len(axis_coords) >= 2:
                # 중간점 추가
                mid_idx = len(axis_coords) // 2
                # 출발지와 너무 가깝지 않은 경우만 추가
                if not waypoints or axis_coords[mid_idx] != waypoints[0]:
                    waypoints.append(axis_coords[mid_idx])
            
            # 3. 목표지: 위협 위치 또는 작전 목표
            if threat_position:
                # 마지막 경유지와 겹치지 않을 때만 추가
                if not waypoints or threat_position != waypoints[-1]:
                    waypoints.append(threat_position)
            
            # 방공(DETERRENCE) 등 비기동 방책을 위해 최소 2개 포인트 보장
            # 출발지 -> 목표지만 있어도 경로 생성
            if len(waypoints) < 2 and len(waypoints) == 1 and axis_coords and len(axis_coords) >= 2:
                # 포인트가 1개뿐이고 축선 정보가 있다면 축선의 종단점 추가
                waypoints.append(axis_coords[-1])
            
            if len(waypoints) < 2:
                logger.warning(f"Could not generate waypoints for {coa.get('coa_id')}: waypoints={waypoints}")
                return None
            
            # 4. 경로 타입 결정
            path_type = self._determine_path_type(coa)
            
            return {
                "waypoints": waypoints,  # [[lng, lat], ...]
                "path_type": path_type,
            }
            
        except Exception as e:
            logger.warning(f"Failed to generate operational path: {e}")
            return None
    
    def generate_operational_area(
        self,
        friendly_units: List[Dict[str, Any]],
        threat_position: Optional[List[float]] = None,
        path_points: Optional[List[List[float]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        방책 작전 영역 생성 (Convex Hull 기반 동적 영역)
        
        Args:
            friendly_units: 참여 아군 부대 목록
            threat_position: 위협 위치 [lng, lat]
            path_points: 기동 경로 포인트들 [[lng, lat], ...]
            
        Returns:
            operational_area 딕셔너리 또는 None
        """
        try:
            all_points = []
            
            # 1. 부대 위치 수집
            unit_positions = []
            for unit in friendly_units:
                pos = self._get_unit_position(unit)
                if pos:
                    unit_positions.append(pos)
                    all_points.append(pos)
            
            # 2. 위협 위치 수집
            if threat_position:
                all_points.append(threat_position)
            
            # 3. 경로 포인트 수집
            if path_points:
                all_points.extend(path_points)
                
            if not all_points:
                return None
                
            # [Dynamic AO] 모든 핵심 요소를 포함하는 전술적 영역(Polygon) 생성
            # 4. Convex Hull (볼록 껍질) 계산
            hull_points = self._calculate_convex_hull(all_points)
            
            # 5. 영역 확장을 위한 버퍼 적용 (전술적 여유 공간)
            # 단순화를 위해 각 점을 일정 거리(약 2km)만큼 확장한 효과를 주기 위해 버퍼 적용
            tactical_polygon = self._create_buffered_polygon(hull_points, buffer_km=2.5)
            
            result = {
                "deployment_area": {
                    "polygon": tactical_polygon,
                    "description": "전술적 작전 영역 (모든 요소 포함)"
                }
            }
            
            # 하위 호환성을 위해 개별 영역 정보도 유지 (필요 시)
            if threat_position and unit_positions:
                engagement_polygon = self._create_buffer_between_points(
                    unit_positions,
                    threat_position,
                    buffer_distance_km=3.0
                )
                if engagement_polygon:
                    result["engagement_area"] = {
                        "polygon": engagement_polygon,
                        "description": "예상 교전 중심 영역"
                    }
            
            # 단일 다각형으로도 제공
            result["polygon"] = tactical_polygon
            
            return result
            
        except Exception as e:
            logger.warning(f"Failed to generate operational area: {e}")
            return None

    def _calculate_convex_hull(self, points: List[List[float]]) -> List[List[float]]:
        """
        Monotone Chain 알고리즘을 사용한 볼록 껍질(Convex Hull) 계산
        
        Args:
            points: [[x, y], ...] 형식의 좌표 리스트
            
        Returns:
            볼록 껍질을 구성하는 점들의 리스트 (시계 반대 방향)
        """
        if len(points) <= 2:
            return points
            
        # 중복 제거 및 정렬
        sorted_points = sorted(list(set(tuple(p) for p in points)))
        
        def cross_product(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        # Lower hull
        lower = []
        for p in sorted_points:
            while len(lower) >= 2 and cross_product(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
            
        # Upper hull
        upper = []
        for p in reversed(sorted_points):
            while len(upper) >= 2 and cross_product(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
            
        return [list(p) for p in lower[:-1] + upper[:-1]]

    def _create_buffered_polygon(self, points: List[List[float]], buffer_km: int = 2) -> List[List[float]]:
        """
        다각형 주위에 일정한 버퍼(여유 공간)를 둔 확장된 다각형 생성
        (간소화된 알고리즘: 중심에서 각 점 방향으로 확장)
        """
        if not points:
            return []
            
        center = self._calculate_center_point(points)
        buffer_deg = buffer_km / 111.0 # 대략적인 도 단위 변환
        
        expanded = []
        import math
        
        for p in points:
            dx = p[0] - center[0]
            dy = p[1] - center[1]
            dist = math.sqrt(dx**2 + dy**2)
            
            if dist > 0:
                # 중심에서 바깥쪽으로 확장
                new_x = p[0] + (dx / dist) * buffer_deg
                new_y = p[1] + (dy / dist) * buffer_deg
                expanded.append([new_x, new_y])
            else:
                # 점이 하나뿐인 경우 사각형 버퍼 생성
                expanded.extend([
                    [p[0] - buffer_deg, p[1] - buffer_deg],
                    [p[0] + buffer_deg, p[1] - buffer_deg],
                    [p[0] + buffer_deg, p[1] + buffer_deg],
                    [p[0] - buffer_deg, p[1] + buffer_deg]
                ])
                break
                
        if expanded:
            expanded.append(expanded[0]) # 닫기
            
        return expanded
    
    def generate_unit_positions_geojson(
        self,
        friendly_units: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        아군 부대 위치 GeoJSON 생성
        
        Args:
            friendly_units: 참여 아군 부대 목록
            
        Returns:
            GeoJSON FeatureCollection 또는 None
        """
        try:
            features = []
            
            for unit in friendly_units:
                # 부대 위치 조회
                position = self._get_unit_position(unit)
                if not position:
                    continue
                
                # GeoJSON Feature 생성
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": position  # [lng, lat]
                    },
                    "properties": {
                        "unit_id": unit.get("unit_id", ""),
                        "unit_name": unit.get("부대명", unit.get("unit_name", "")),
                        "제대": unit.get("제대", unit.get("unit_level", "")),
                        "병종": unit.get("병종", unit.get("unit_type", "")),
                        "전투력지수": unit.get("전투력지수", unit.get("combat_power", 0)),
                        "배치지형셀ID": unit.get("배치지형셀ID", ""),
                        "배치축선ID": unit.get("배치축선ID", ""),
                        "전술적역할": unit.get("tactical_role", unit.get("전술적역할", "")),
                        "할당수량": unit.get("allocated_quantity", unit.get("할당수량", 1)),
                        "계획상태": unit.get("plan_status", unit.get("계획상태", "사용가능")),
                    }
                }
                features.append(feature)
            
            if not features:
                return None
            
            return {
                "type": "FeatureCollection",
                "features": features
            }
            
        except Exception as e:
            logger.warning(f"Failed to generate unit positions GeoJSON: {e}")
            return None
    
    def _get_unit_position(self, unit: Dict[str, Any]) -> Optional[List[float]]:
        """부대 위치 조회 [lng, lat]"""
        # 좌표정보 필드 확인
        coord_str = unit.get("좌표정보")
        if coord_str:
            try:
                parts = str(coord_str).strip().split(',')
                if len(parts) == 2:
                    # Excel: "lat, lon" -> GeoJSON: [lon, lat]
                    return [float(parts[1].strip()), float(parts[0].strip())]
            except:
                pass
        
        # 배치지형셀ID 확인
        cell_id = unit.get("배치지형셀ID")
        if cell_id:
            return self._get_terrain_cell_coordinates(str(cell_id))
        
        return None
    
    def _calculate_center_point(self, positions: List[List[float]]) -> List[float]:
        """여러 위치의 중심점 계산"""
        if not positions:
            return [0.0, 0.0]
        
        avg_lng = sum(p[0] for p in positions) / len(positions)
        avg_lat = sum(p[1] for p in positions) / len(positions)
        return [avg_lng, avg_lat]
    
    def _create_circle_polygon(self, center: List[float], radius_km: float, num_points: int = 32) -> List[List[float]]:
        """
        원형 폴리곤 생성
        
        Args:
            center: 중심점 [lng, lat]
            radius_km: 반경 (km)
            num_points: 폴리곤 점 개수
            
        Returns:
            폴리곤 좌표 리스트 [[lng, lat], ...]
        """
        import math
        
        # km를 도(degree)로 변환 (대략적)
        # 1도 ≈ 111km
        radius_deg = radius_km / 111.0
        
        polygon = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            lng = center[0] + radius_deg * math.cos(angle) / math.cos(math.radians(center[1]))
            lat = center[1] + radius_deg * math.sin(angle)
            polygon.append([lng, lat])
        
        # 폴리곤 닫기
        polygon.append(polygon[0])
        return polygon
    
    def _create_buffer_between_points(
        self,
        start_positions: List[List[float]],
        end_position: List[float],
        buffer_distance_km: float = 3.0
    ) -> Optional[List[List[float]]]:
        """
        두 지점 사이의 버퍼 영역 생성
        
        Args:
            start_positions: 시작 지점들 [[lng, lat], ...]
            end_position: 종료 지점 [lng, lat]
            buffer_distance_km: 버퍼 거리 (km)
            
        Returns:
            폴리곤 좌표 리스트 또는 None
        """
        if not start_positions:
            return None
        
        # 시작점 중심 계산
        start_center = self._calculate_center_point(start_positions)
        
        # 간단한 사각형 버퍼 생성 (실제로는 더 정교한 알고리즘 사용 가능)
        buffer_deg = buffer_distance_km / 111.0
        
        # 시작점과 종료점 사이의 방향 계산
        import math
        dx = end_position[0] - start_center[0]
        dy = end_position[1] - start_center[1]
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance < 0.001:
            return None
        
        # 수직 방향 벡터
        perp_x = -dy / distance
        perp_y = dx / distance
        
        # 버퍼 폴리곤 생성
        polygon = [
            [start_center[0] + perp_x * buffer_deg, start_center[1] + perp_y * buffer_deg],
            [end_position[0] + perp_x * buffer_deg, end_position[1] + perp_y * buffer_deg],
            [end_position[0] - perp_x * buffer_deg, end_position[1] - perp_y * buffer_deg],
            [start_center[0] - perp_x * buffer_deg, start_center[1] - perp_y * buffer_deg],
            [start_center[0] + perp_x * buffer_deg, start_center[1] + perp_y * buffer_deg],  # 닫기
        ]
        
        return polygon
    
    def _determine_path_type(self, coa: Dict[str, Any]) -> str:
        """방책 유형에 따른 경로 타입 결정"""
        coa_type = str(coa.get("coa_type", "")).lower()
        coa_name = str(coa.get("coa_name", coa.get("명칭", ""))).lower()
        
        if "공격" in coa_name or "offensive" in coa_type or "attack" in coa_type:
            return "ATTACK"
        elif "방어" in coa_name or "defense" in coa_type or "defensive" in coa_type:
            return "DEFENSE"
        elif "지원" in coa_name or "support" in coa_type:
            return "SUPPORT"
        else:
            return "MOVEMENT"
    
    def enrich_axis_states_with_coordinates(self, axis_states: List[Any]) -> List[Dict[str, Any]]:
        """
        axis_states에 좌표 정보 추가
        
        Args:
            axis_states: AxisState 객체 리스트
            
        Returns:
            좌표 정보가 추가된 딕셔너리 리스트
        """
        enriched = []
        for axis_state in axis_states:
            try:
                # AxisState 객체를 딕셔너리로 변환
                if hasattr(axis_state, 'to_dict'):
                    axis_dict = axis_state.to_dict()
                elif hasattr(axis_state, '__dict__'):
                    axis_dict = axis_state.__dict__.copy()
                else:
                    axis_dict = dict(axis_state) if isinstance(axis_state, dict) else {}
                
                axis_id = axis_dict.get('axis_id')
                if axis_id:
                    # 축선 좌표 해결
                    coordinates, metadata = self.resolve_axis_coordinates(axis_id)
                    if coordinates:
                        # [lng, lat] 형식을 [lat, lng]로 변환 (Leaflet 형식)
                        axis_dict['coordinates'] = [[coord[1], coord[0]] for coord in coordinates]
                        axis_dict['geojson'] = {
                            'type': 'LineString',
                            'coordinates': coordinates  # GeoJSON 형식 [lng, lat]
                        }
                    
                    # 메타데이터 추가
                    if metadata:
                        if 'name' in metadata and not axis_dict.get('axis_name'):
                            axis_dict['axis_name'] = metadata['name']
                        if 'type' in metadata:
                            axis_type = str(metadata['type']).upper()
                            if axis_type in ['PRIMARY', 'SECONDARY', 'SUPPORT']:
                                axis_dict['axis_type'] = axis_type
                
                enriched.append(axis_dict)
                
            except Exception as e:
                logger.warning(f"Failed to enrich axis state: {e}")
                # 실패해도 원본 추가
                if hasattr(axis_state, 'to_dict'):
                    enriched.append(axis_state.to_dict())
                else:
                    enriched.append(axis_state)
        
        return enriched
