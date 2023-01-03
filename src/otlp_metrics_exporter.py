from os import environ
from typing import Dict, Optional, Sequence
from grpc import ChannelCredentials, Compression
from opentelemetry.sdk.metrics._internal.aggregation import Aggregation
from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    OTLPExporterMixin,
    _get_credentials,
    environ_to_compression,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2_grpc import (
    MetricsServiceStub,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_INSECURE,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import ResourceMetrics
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExporter,
    MetricExportResult
)


class OTLPMetricExporter(
    MetricExporter,
    OTLPExporterMixin[ResourceMetrics,
                      ExportMetricsServiceRequest, MetricExportResult],
):
    """OTLP metric exporter
    Args:
        endpoint: Target URL to which the exporter is going to send metrics
        max_export_batch_size: Maximum number of data points to export in a single request. This is to deal with
            gRPC's 4MB message size limit. If not set there is no limit to the number of data points in a request.
            If it is set and the number of data points exceeds the max, the request will be split.
    """

    _result = MetricExportResult
    _stub = MetricsServiceStub

    def __init__(
        self,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        headers: Optional[Sequence] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        preferred_temporality: Dict[type, AggregationTemporality] = None,
        preferred_aggregation: Dict[type, Aggregation] = None,
        max_export_batch_size: Optional[int] = None,
    ):

        if insecure is None:
            insecure_environ = environ.get(OTEL_EXPORTER_OTLP_METRICS_INSECURE)
            if insecure_environ is not None:
                insecure = insecure_environ.lower() == "true"

        if (
            not insecure
            and environ.get(OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE) is not None
        ):
            credentials = _get_credentials(
                credentials, OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE
            )

        if timeout is None:
            environ_timeout = environ.get(OTEL_EXPORTER_OTLP_METRICS_TIMEOUT)
            timeout = (
                int(environ_timeout) if environ_timeout is not None else None
            )

        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_METRICS_COMPRESSION)
            if compression is None
            else compression
        )

        instrument_class_temporality = {}
        if (
            environ.get(
                OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
                "CUMULATIVE",
            )
            .upper()
            .strip()
            == "DELTA"
        ):
            instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.DELTA,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        else:
            instrument_class_temporality = {
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        instrument_class_temporality.update(preferred_temporality or {})

        MetricExporter.__init__(
            self,
            preferred_temporality=instrument_class_temporality,
            preferred_aggregation=preferred_aggregation,
        )

        OTLPExporterMixin.__init__(
            self,
            endpoint=endpoint
            or environ.get(OTEL_EXPORTER_OTLP_METRICS_ENDPOINT),
            insecure=insecure,
            credentials=credentials,
            headers=headers or environ.get(OTEL_EXPORTER_OTLP_METRICS_HEADERS),
            timeout=timeout,
            compression=compression,
        )

        self._max_export_batch_size: Optional[int] = max_export_batch_size

    def _translate_data(
        self, data: Sequence[ResourceMetrics]
    ) -> ExportMetricsServiceRequest:
        return ExportMetricsServiceRequest(
            resource_metrics=data
        )

    def export(
        self,
        metrics: Sequence[ResourceMetrics],
    ) -> MetricExportResult:
        return self._export(metrics)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        pass

    @property
    def _exporting(self) -> str:
        return "metrics"

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True
