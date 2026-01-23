# api/routers/data_management.py
"""
데이터 관리 관련 API 엔드포인트
- 데이터 테이블 조회
- 데이터 품질 검증
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from core_pipeline.orchestrator import Orchestrator
import logging
import pandas as pd

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data-management", tags=["data-management"])

# Global orchestrator instance (injected from main.py)
_orchestrator: Optional[Orchestrator] = None


def set_orchestrator(orchestrator: Orchestrator):
    """Set the global orchestrator instance."""
    global _orchestrator
    _orchestrator = orchestrator


def get_orchestrator() -> Orchestrator:
    """Get the global orchestrator instance."""
    if _orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    return _orchestrator


# Request/Response Models
class TableInfo(BaseModel):
    name: str
    display_name: str
    row_count: int


class TableListResponse(BaseModel):
    tables: List[TableInfo]


class TableDataResponse(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_count: int


class QualityIssue(BaseModel):
    severity: str  # "error", "warning", "info"
    type: str  # "missing_field", "type_error", "duplicate", etc.
    field: Optional[str] = None
    row_index: Optional[int] = None
    message: str


class TableQuality(BaseModel):
    name: str
    display_name: str
    quality_score: float  # 0-100
    issues: List[QualityIssue]


class DataQualityResponse(BaseModel):
    tables: List[TableQuality]


# API Endpoints
@router.get("/tables", response_model=TableListResponse)
async def get_table_list():
    """
    데이터 테이블 목록을 조회합니다.
    """
    try:
        orchestrator = get_orchestrator()
        data_manager = orchestrator.core.data_manager
        
        logger.info("Fetching table list...")
        
        # Get all available tables from DataManager
        tables = []
        for key, df in data_manager.load_all().items():
            if isinstance(df, pd.DataFrame):
                tables.append(TableInfo(
                    name=key,
                    display_name=key,  # Can be enhanced with display names from config
                    row_count=len(df)
                ))
        
        logger.info(f"Found {len(tables)} tables")
        
        return TableListResponse(tables=tables)
    
    except Exception as e:
        logger.error(f"Error fetching table list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch table list: {str(e)}")


@router.get("/tables/{table_name}", response_model=TableDataResponse)
async def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(100, ge=1, le=1000, description="Number of rows per page")
):
    """
    특정 테이블의 데이터를 조회합니다.
    페이지네이션을 지원합니다.
    """
    try:
        orchestrator = get_orchestrator()
        data_manager = orchestrator.core.data_manager
        
        logger.info(f"Fetching data for table: {table_name} (page={page}, page_size={page_size})")
        
        # Get table data
        df = data_manager.load_table(table_name)
        
        if df is None or not isinstance(df, pd.DataFrame):
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        # Calculate pagination
        total_count = len(df)
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_count)
        
        # Slice dataframe
        df_page = df.iloc[start_idx:end_idx]
        
        # Convert to list of dictionaries
        # Replace NaN with None for JSON serialization
        rows = df_page.where(pd.notnull(df_page), None).to_dict(orient="records")
        
        logger.info(f"Returning {len(rows)} rows (total: {total_count})")
        
        return TableDataResponse(
            columns=df.columns.tolist(),
            rows=rows,
            total_count=total_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching table data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch table data: {str(e)}")


@router.get("/quality-check", response_model=DataQualityResponse)
async def check_data_quality():
    """
    모든 데이터 테이블의 품질을 검증합니다.
    """
    try:
        orchestrator = get_orchestrator()
        data_manager = orchestrator.core.data_manager
        
        logger.info("Performing data quality check...")
        
        table_qualities = []
        
        for table_name, df in data_manager.load_all().items():
            if not isinstance(df, pd.DataFrame):
                continue
            
            logger.info(f"Checking quality for table: {table_name}")
            
            issues = []
            total_checks = 0
            failed_checks = 0
            
            # Check 1: Missing values
            for col in df.columns:
                missing_count = df[col].isna().sum()
                total_checks += len(df)
                failed_checks += missing_count
                
                if missing_count > 0:
                    # Find first missing row for example
                    first_missing_idx = df[df[col].isna()].index[0]
                    issues.append(QualityIssue(
                        severity="warning",
                        type="missing_field",
                        field=col,
                        row_index=int(first_missing_idx),
                        message=f"Column '{col}' has {missing_count} missing values"
                    ))
            
            # Check 2: Duplicate rows
            duplicate_count = df.duplicated().sum()
            failed_checks += duplicate_count
            
            if duplicate_count > 0:
                first_duplicate_idx = df[df.duplicated()].index[0]
                issues.append(QualityIssue(
                    severity="warning",
                    type="duplicate",
                    row_index=int(first_duplicate_idx),
                    message=f"Found {duplicate_count} duplicate rows"
                ))
            
            # Check 3: Data type consistency (example: numeric columns)
            for col in df.columns:
                if df[col].dtype == 'object':
                    # Check if column should be numeric
                    numeric_values = pd.to_numeric(df[col], errors='coerce')
                    non_numeric_count = numeric_values.isna().sum() - df[col].isna().sum()
                    
                    if non_numeric_count > 0 and non_numeric_count < len(df) * 0.5:
                        # More than half numeric suggests it should be numeric
                        first_error_idx = df[numeric_values.isna() & df[col].notna()].index[0] if len(df[numeric_values.isna() & df[col].notna()]) > 0 else None
                        if first_error_idx is not None:
                            issues.append(QualityIssue(
                                severity="info",
                                type="type_error",
                                field=col,
                                row_index=int(first_error_idx),
                                message=f"Column '{col}' has {non_numeric_count} non-numeric values"
                            ))
            
            # Calculate quality score (0-100)
            quality_score = 100.0
            if total_checks > 0:
                quality_score = max(0, 100.0 * (1 - failed_checks / total_checks))
            
            table_qualities.append(TableQuality(
                name=table_name,
                display_name=table_name,
                quality_score=round(quality_score, 1),
                issues=issues[:10]  # Limit to top 10 issues
            ))
        
        logger.info(f"Quality check complete for {len(table_qualities)} tables")
        
        return DataQualityResponse(tables=table_qualities)
    
    except Exception as e:
        logger.error(f"Error checking data quality: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data quality check failed: {str(e)}")
