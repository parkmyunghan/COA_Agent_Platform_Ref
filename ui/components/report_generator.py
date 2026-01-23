# ui/components/report_generator.py
# -*- coding: utf-8 -*-
"""
COA 보고서 자동 출력 (PDF 생성)
ReportLab 기반 PDF 생성
"""
import streamlit as st
from datetime import datetime
from pathlib import Path
import os
import platform


def _register_korean_font():
    """한글 폰트 등록 (Windows 시스템)"""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # Windows 시스템 폰트 경로
        if platform.system() == 'Windows':
            font_paths = [
                'C:/Windows/Fonts/malgun.ttf',      # 맑은 고딕
                'C:/Windows/Fonts/malgunbd.ttf',    # 맑은 고딕 Bold
                'C:/Windows/Fonts/gulim.ttc',       # 굴림 (TTC)
                'C:/Windows/Fonts/batang.ttc',      # 바탕 (TTC)
            ]
            
            # TTF 파일 찾기 및 등록
            for font_path in font_paths:
                if font_path.endswith('.ttf') and Path(font_path).exists():
                    try:
                        pdfmetrics.registerFont(TTFont('KoreanFont', font_path))
                        # Bold 폰트도 등록 시도
                        if 'bd' in font_path.lower() or 'bold' in font_path.lower():
                            pdfmetrics.registerFont(TTFont('KoreanFontBold', font_path))
                        else:
                            # 일반 폰트를 Bold로도 사용
                            pdfmetrics.registerFont(TTFont('KoreanFontBold', font_path))
                        return 'KoreanFont'
                    except Exception as e:
                        continue
            
            # TTC 파일 처리 (fonttools 필요)
            try:
                from fontTools.ttLib import TTFont as FontToolsTTFont
                for font_path in font_paths:
                    if font_path.endswith('.ttc') and Path(font_path).exists():
                        try:
                            # TTC에서 첫 번째 폰트 추출
                            ttc = FontToolsTTFont(font_path, fontNumber=0)
                            # 임시 TTF 파일로 저장
                            temp_dir = Path('./temp_fonts')
                            temp_dir.mkdir(exist_ok=True)
                            temp_ttf = temp_dir / 'korean_font_temp.ttf'
                            ttc.save(str(temp_ttf))
                            pdfmetrics.registerFont(TTFont('KoreanFont', str(temp_ttf)))
                            pdfmetrics.registerFont(TTFont('KoreanFontBold', str(temp_ttf)))
                            return 'KoreanFont'
                        except Exception:
                            continue
            except ImportError:
                # fonttools가 없으면 TTC 파일은 건너뜀
                pass
        
        # 폰트를 찾지 못한 경우 경고
        st.warning("한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다. (한글이 제대로 표시되지 않을 수 있습니다)")
        return 'Helvetica'
    except Exception as e:
        st.warning(f"폰트 등록 실패: {e}. 기본 폰트를 사용합니다.")
        return 'Helvetica'


def generate_coa_report(
    agent_name: str,
    summary: str,
    citations: list,
    threat_summary: dict = None,
    output_path: str = None
) -> str:
    """
    Defense COA Recommendation Report PDF 생성
    
    Args:
        agent_name: Agent 이름
        summary: LLM 요약 결과
        citations: 근거 문서 리스트
        threat_summary: 위협 요약 정보
        output_path: 출력 경로
        
    Returns:
        생성된 PDF 파일 경로
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        
        # 한글 폰트 등록
        korean_font = _register_korean_font()
        korean_font_bold = 'KoreanFontBold' if korean_font == 'KoreanFont' else 'Helvetica-Bold'
        
        # 출력 경로 설정
        if output_path is None:
            reports_dir = Path("./reports")
            reports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(reports_dir / f"COA_Report_{timestamp}.pdf")
        
        # PDF 문서 생성
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        story = []
        
        # 스타일 설정 (한글 폰트 사용)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=korean_font  # 한글 폰트 추가
        )
        
        # 한글 폰트를 사용하는 Normal 스타일
        normal_style = ParagraphStyle(
            'KoreanNormal',
            parent=styles['Normal'],
            fontName=korean_font,
            fontSize=10
        )
        
        # 한글 폰트를 사용하는 Heading2 스타일
        heading2_style = ParagraphStyle(
            'KoreanHeading2',
            parent=styles['Heading2'],
            fontName=korean_font,
            fontSize=14
        )
        
        # 제목
        story.append(Paragraph("Defense COA Recommendation Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # 날짜 및 Agent 정보
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"<b>Date:</b> {date_str}", normal_style))
        story.append(Paragraph(f"<b>Agent:</b> {agent_name}", normal_style))
        story.append(Spacer(1, 0.3*inch))
        
        # 요약 섹션
        story.append(Paragraph("<b>Summary:</b>", heading2_style))
        story.append(Paragraph(summary.replace('\n', '<br/>'), normal_style))
        story.append(Spacer(1, 0.3*inch))
        
        # 위협 요약 (있는 경우)
        if threat_summary:
            story.append(Paragraph("<b>Threat Summary:</b>", heading2_style))
            # Paragraph 객체로 변환하여 줄바꿈 지원
            threat_data = []
            for key, value in threat_summary.items():
                threat_data.append([
                    Paragraph(str(key), normal_style),
                    Paragraph(str(value), normal_style)  # Paragraph 객체 사용
                ])
            
            threat_table = Table(threat_data, colWidths=[2*inch, 4*inch])
            threat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # 상단 정렬 추가
                ('FONTNAME', (0, 0), (-1, 0), korean_font_bold),  # 한글 폰트 사용
                ('FONTNAME', (0, 1), (-1, -1), korean_font),  # 본문도 한글 폰트 사용
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 1), (-1, -1), 6),  # 상단 패딩 추가
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),  # 하단 패딩 추가
                ('LEFTPADDING', (0, 0), (-1, -1), 6),  # 좌측 패딩 추가
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),  # 우측 패딩 추가
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(threat_table)
            story.append(Spacer(1, 0.3*inch))
        
        # 참고 문서 섹션
        if citations:
            story.append(Paragraph("<b>References:</b>", heading2_style))
            # 헤더는 Paragraph로 생성
            ref_data = [[Paragraph("<b>No.</b>", normal_style), 
                         Paragraph("<b>Document</b>", normal_style), 
                         Paragraph("<b>Score</b>", normal_style)]]
            for i, citation in enumerate(citations, 1):
                text = citation.get("text", "")
                # 텍스트가 너무 길어도 자르지 않고 그대로 사용 (Paragraph가 자동 줄바꿈)
                score = citation.get("score", 0.0)
                ref_data.append([
                    Paragraph(str(i), normal_style),
                    Paragraph(text, normal_style),  # Paragraph 객체 사용하여 자동 줄바꿈
                    Paragraph(f"{score:.4f}", normal_style)
                ])
            
            ref_table = Table(ref_data, colWidths=[0.5*inch, 4.5*inch, 1*inch])
            ref_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # 상단 정렬 추가
                ('FONTNAME', (0, 0), (-1, 0), korean_font_bold),  # 한글 폰트 사용
                ('FONTNAME', (0, 1), (-1, -1), korean_font),  # 본문도 한글 폰트 사용
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 1), (-1, -1), 6),  # 상단 패딩 추가
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),  # 하단 패딩 추가
                ('LEFTPADDING', (0, 0), (-1, -1), 6),  # 좌측 패딩 추가
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),  # 우측 패딩 추가
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(ref_table)
        
        # PDF 빌드
        doc.build(story)
        
        return output_path
        
    except ImportError:
        st.error("ReportLab이 설치되지 않았습니다. pip install reportlab")
        return None
    except Exception as e:
        st.error(f"PDF 생성 실패: {e}")
        return None


def render_report_download_button(
    agent_name: str,
    summary: str,
    citations: list,
    threat_summary: dict = None
):
    """
    PDF 보고서 다운로드 버튼 렌더링
    
    Args:
        agent_name: Agent 이름
        summary: 요약 텍스트
        citations: 근거 문서 리스트
        threat_summary: 위협 요약 정보
    """
    if st.button("📄 PDF 보고서 생성 및 다운로드"):
        with st.spinner("PDF 생성 중..."):
            pdf_path = generate_coa_report(
                agent_name=agent_name,
                summary=summary,
                citations=citations,
                threat_summary=threat_summary
            )
            
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="📥 PDF 다운로드",
                        data=pdf_file.read(),
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf"
                    )
                st.success(f"✅ PDF 생성 완료: {os.path.basename(pdf_path)}")
            else:
                st.error("PDF 생성에 실패했습니다.")














