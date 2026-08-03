"""
PDF report generator using ReportLab.
"""

import io
from datetime import datetime
from typing import Dict, List, Any, Optional

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether,
)
from reportlab.lib import colors

import pandas as pd


class PDFReportGenerator:
    """Generate professional PDF reports from analytics data."""

    # Color scheme
    PRIMARY_COLOR = HexColor('#2563eb')
    SECONDARY_COLOR = HexColor('#64748b')
    SUCCESS_COLOR = HexColor('#10b981')
    WARNING_COLOR = HexColor('#f59e0b')
    DANGER_COLOR = HexColor('#ef4444')
    LIGHT_BG = HexColor('#f8fafc')

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=self.PRIMARY_COLOR,
            spaceAfter=20,
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=self.PRIMARY_COLOR,
            spaceBefore=20,
            spaceAfter=10,
            borderWidth=1,
            borderColor=self.PRIMARY_COLOR,
            borderPadding=5,
        ))
        self.styles.add(ParagraphStyle(
            name='SubSectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=self.SECONDARY_COLOR,
            spaceBefore=12,
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name='BodyText2',
            parent=self.styles['BodyText'],
            fontSize=10,
            leading=14,
        ))
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=self.SECONDARY_COLOR,
            alignment=TA_CENTER,
        ))

    def generate_dataset_report(
        self,
        dataset_name: str,
        dataset_id: str,
        profile: Dict[str, Any],
        kpis: Dict[str, Any],
        correlations: Dict[str, float],
        sample_data: List[Dict],
        charts: List[Dict],
        ai_insights: Optional[List] = None,
    ) -> io.BytesIO:
        """Generate a comprehensive dataset analysis PDF report."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        elements = []

        # Title page
        elements.append(Spacer(1, 2 * inch))
        elements.append(Paragraph("Enterprise AI Analytics Platform", self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph(f"Dataset Analysis Report", self.styles['SectionHeader']))
        elements.append(Paragraph(f"<b>{dataset_name}</b>", self.styles['BodyText2']))
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", self.styles['BodyText2']))
        elements.append(Spacer(1, 1 * inch))

        # KPI Summary Table
        kpi_data = [
            ['Metric', 'Value'],
            ['Total Rows', str(kpis.get('total_rows', 0))],
            ['Total Columns', str(kpis.get('total_columns', 0))],
            ['Numeric Columns', str(kpis.get('numeric_columns', 0))],
            ['Categorical Columns', str(kpis.get('categorical_columns', 0))],
            ['Null Percentage', f"{kpis.get('null_percentage', 0)}%"],
            ['Duplicate Rows', str(kpis.get('duplicate_rows', 0))],
        ]

        elements.append(Paragraph("Key Performance Indicators", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.2 * inch))

        table = Table(kpi_data, colWidths=[3 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.LIGHT_BG),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.LIGHT_BG]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))

        # Column Profile
        elements.append(Paragraph("Data Profile", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.2 * inch))

        if profile.get('data_profile'):
            for col_name, col_info in list(profile['data_profile'].items())[:20]:
                if isinstance(col_info, dict):
                    elements.append(Paragraph(f"<b>{col_name}</b> ({col_info.get('dtype', 'unknown')})", self.styles['SubSectionHeader']))
                    details = [
                        ['Property', 'Value'],
                        ['Null Count', str(col_info.get('null_count', 'N/A'))],
                        ['Null %', f"{col_info.get('null_percent', 0)}%"],
                        ['Unique Values', str(col_info.get('unique_count', 'N/A'))],
                    ]

                    if 'mean' in col_info:
                        details.extend([
                            ['Mean', str(col_info.get('mean', 'N/A'))],
                            ['Median', str(col_info.get('median', 'N/A'))],
                            ['Std Dev', str(col_info.get('std', 'N/A'))],
                            ['Min', str(col_info.get('min', 'N/A'))],
                            ['Max', str(col_info.get('max', 'N/A'))],
                        ])

                    col_table = Table(details, colWidths=[2 * inch, 3 * inch])
                    col_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e2e8f0')),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ]))
                    elements.append(col_table)
                    elements.append(Spacer(1, 0.1 * inch))

        # Correlations
        if correlations:
            elements.append(PageBreak())
            elements.append(Paragraph("Correlation Analysis", self.styles['SectionHeader']))
            elements.append(Spacer(1, 0.2 * inch))

            corr_data = [['Column Pair', 'Correlation']]
            for pair, value in sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)[:15]:
                corr_data.append([pair, f"{value:.4f}"])

            corr_table = Table(corr_data, colWidths=[4 * inch, 1.5 * inch])
            corr_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(corr_table)

        # AI Insights
        if ai_insights:
            elements.append(PageBreak())
            elements.append(Paragraph("AI Insights", self.styles['SectionHeader']))
            elements.append(Spacer(1, 0.2 * inch))

            for insight in ai_insights:
                insight_text = insight if isinstance(insight, str) else insight.get('content', str(insight))
                elements.append(Paragraph(f"• {insight_text}", self.styles['BodyText2']))
                elements.append(Spacer(1, 0.1 * inch))

        # Footer
        elements.append(Spacer(1, 1 * inch))
        elements.append(Paragraph(
            f"Report generated by Enterprise AI Analytics Platform | Dataset ID: {dataset_id}",
            self.styles['Footer']
        ))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer

    def generate_forecast_report(
        self,
        dataset_name: str,
        method: str,
        target_column: str,
        horizon: int,
        forecast_results: Dict[str, Any],
    ) -> io.BytesIO:
        """Generate a forecast report PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        elements = []

        elements.append(Paragraph("Forecast Report", self.styles['CustomTitle']))
        elements.append(Paragraph(f"Dataset: {dataset_name}", self.styles['BodyText2']))
        elements.append(Paragraph(f"Method: {method} | Target: {target_column} | Horizon: {horizon} periods", self.styles['BodyText2']))
        elements.append(Spacer(1, 0.5 * inch))

        # Metrics
        metrics = forecast_results.get('metrics', {})
        if metrics:
            metrics_data = [['Metric', 'Value']]
            for key, value in metrics.items():
                metrics_data.append([key.upper(), f"{value:.4f}" if isinstance(value, float) else str(value)])

            table = Table(metrics_data, colWidths=[3 * inch, 2 * inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(table)

        doc.build(elements)
        buffer.seek(0)
        return buffer
