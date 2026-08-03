"""
Views for analytics app - dashboard, charts, KPIs, and SQL queries.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings

from .models import SavedQuery, AnalysisReport, DashboardWidget
from .serializers import SavedQuerySerializer, AnalysisReportSerializer, DashboardWidgetSerializer
from datasets.models import Dataset
from .engine import DataProcessor
from .chart_generator import ChartGenerator
from accounts.models import AuditLog


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


class DashboardView(APIView):
    """Get complete dashboard data for a dataset."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, dataset_id):
        try:
            dataset = Dataset.objects.get(id=dataset_id, owner=request.user, status='ready')
        except Dataset.DoesNotExist:
            return Response({'error': 'Dataset not found or not ready.'}, status=status.HTTP_404_NOT_FOUND)

        processor = DataProcessor(str(dataset.file.path))
        processor.load()

        kpis = processor.get_kpis()
        correlations = processor.get_correlations()
        profile_dict = dataset.data_profile if dataset.data_profile else processor._create_profile()
        column_names = dataset.column_names if dataset.column_names else list(processor.df.columns)
        column_types = dataset.column_types if dataset.column_types else processor._get_column_types()
        sample_data = dataset.sample_data if dataset.sample_data else processor._get_sample_data()

        full_profile = {
            'row_count': dataset.row_count or int(len(processor.df)),
            'column_count': dataset.column_count or int(len(processor.df.columns)),
            'data_quality_score': dataset.data_quality_score if dataset.data_quality_score is not None else 100.0,
            'data_profile': profile_dict,
            'column_names': column_names,
            'column_types': column_types,
            'sample_data': sample_data,
        }

        # Generate chart configurations
        chart_gen = ChartGenerator(processor.df)
        charts = chart_gen.auto_generate_charts()

        return Response({
            'dataset': {
                'id': str(dataset.id),
                'name': dataset.name,
                'row_count': dataset.row_count,
                'column_count': dataset.column_count,
                'data_quality_score': dataset.data_quality_score,
                'file_type': dataset.file_type,
            },
            'kpis': kpis,
            'correlations': correlations,
            'profile': full_profile,
            'charts': charts,
            'widgets': DashboardWidgetSerializer(
                DashboardWidget.objects.filter(dataset=dataset, owner=request.user),
                many=True
            ).data,
        })


class ChartDataView(APIView):
    """Get chart data for a specific visualization."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, dataset_id):
        try:
            dataset = Dataset.objects.get(id=dataset_id, owner=request.user, status='ready')
        except Dataset.DoesNotExist:
            return Response({'error': 'Dataset not found.'}, status=status.HTTP_404_NOT_FOUND)

        processor = DataProcessor(str(dataset.file.path))
        processor.load()

        chart_type = request.query_params.get('type', 'bar')
        x_column = request.query_params.get('x')
        y_column = request.query_params.get('y')
        group_by = request.query_params.get('group_by')

        chart_gen = ChartGenerator(processor.df)
        data = chart_gen.generate_chart_data(
            chart_type=chart_type,
            x_column=x_column,
            y_column=y_column,
            group_by=group_by,
        )

        return Response(data)


class SQLQueryView(APIView):
    """Execute SQL-like queries on datasets using pandas."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, dataset_id):
        try:
            dataset = Dataset.objects.get(id=dataset_id, owner=request.user, status='ready')
        except Dataset.DoesNotExist:
            return Response({'error': 'Dataset not found.'}, status=status.HTTP_404_NOT_FOUND)

        sql = request.data.get('sql', '')
        if not sql:
            return Response({'error': 'SQL query is required.'}, status=status.HTTP_400_BAD_REQUEST)

        processor = DataProcessor(str(dataset.file.path))
        processor.load()

        try:
            from .sql_engine import SQLExecutor
            executor = SQLExecutor(processor.df)
            result = executor.execute(sql)

            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ActionType.QUERY,
                description=f"Executed query: {sql[:100]}",
                resource_type='dataset',
                resource_id=str(dataset.id),
                metadata={'sql': sql[:500]},
            )

            return Response(result)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AnalysisReportView(generics.ListCreateAPIView):
    """List and create analysis reports."""
    serializer_class = AnalysisReportSerializer

    def get_queryset(self):
        return AnalysisReport.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class AnalysisReportDetailView(generics.RetrieveDestroyAPIView):
    """Retrieve or delete an analysis report."""
    serializer_class = AnalysisReportSerializer

    def get_queryset(self):
        return AnalysisReport.objects.filter(owner=self.request.user)


class GenerateReportView(APIView):
    """Generate an analysis report for a dataset."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, dataset_id):
        try:
            dataset = Dataset.objects.get(id=dataset_id, owner=request.user, status='ready')
        except Dataset.DoesNotExist:
            return Response({'error': 'Dataset not found.'}, status=status.HTTP_404_NOT_FOUND)

        processor = DataProcessor(str(dataset.file.path))
        kpis = processor.get_kpis()
        correlations = processor.get_correlations()
        charts = ChartGenerator(processor.df).auto_generate_charts()

        report = AnalysisReport.objects.create(
            dataset=dataset,
            owner=request.user,
            title=f"Analysis Report: {dataset.name}",
            kpis=kpis,
            correlations=correlations,
            charts_config=charts,
        )

        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.ActionType.REPORT,
            description=f"Generated analysis report for {dataset.name}",
            resource_type='report',
            resource_id=report.id,
        )

        return Response(AnalysisReportSerializer(report).data, status=status.HTTP_201_CREATED)


class SavedQueryView(generics.ListCreateAPIView):
    """List and create saved queries."""
    serializer_class = SavedQuerySerializer

    def get_queryset(self):
        return SavedQuery.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class SavedQueryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a saved query."""
    serializer_class = SavedQuerySerializer

    def get_queryset(self):
        return SavedQuery.objects.filter(owner=self.request.user)


class WidgetView(generics.ListCreateAPIView):
    """List and create dashboard widgets."""
    serializer_class = DashboardWidgetSerializer

    def get_queryset(self):
        return DashboardWidget.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class WidgetDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a dashboard widget."""
    serializer_class = DashboardWidgetSerializer

    def get_queryset(self):
        return DashboardWidget.objects.filter(owner=self.request.user)
