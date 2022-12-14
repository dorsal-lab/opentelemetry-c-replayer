"""
otlp_span_exporter.py

The OTLP GRPC exporter class
"""

from os import environ
from typing import Optional, Sequence

from grpc import ChannelCredentials, Compression
from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    OTLPExporterMixin, _get_credentials, environ_to_compression)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import \
    ExportTraceServiceRequest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import \
    TraceServiceStub
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION, OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS, OTEL_EXPORTER_OTLP_TRACES_INSECURE,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT)
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


# pylint: disable=no-member
class OTLPSpanExporter(
    SpanExporter,
    OTLPExporterMixin[
        ResourceSpans, ExportTraceServiceRequest, SpanExportResult
    ],
):
    # pylint: disable=unsubscriptable-object
    """OTLP span exporter
    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        insecure: Connection type
        credentials: Credentials object for server authentication
        headers: Headers to send when exporting
        timeout: Backend request timeout in seconds
        compression: gRPC compression method to use
    """

    _result = SpanExportResult
    _stub = TraceServiceStub

    def __init__(
        self,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        headers: Optional[Sequence] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
    ):

        if insecure is None:
            insecure_environ = environ.get(OTEL_EXPORTER_OTLP_TRACES_INSECURE)
            if insecure_environ is not None:
                insecure = insecure_environ.lower() == "true"

        if (
            not insecure
            and environ.get(OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE) is not None
        ):
            credentials = _get_credentials(
                credentials, OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE
            )

        if timeout is None:
            environ_timeout = environ.get(OTEL_EXPORTER_OTLP_TRACES_TIMEOUT)
            timeout = (
                int(environ_timeout) if environ_timeout is not None else None
            )

        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_TRACES_COMPRESSION)
            if compression is None
            else compression
        )

        super().__init__(
            **{
                "endpoint": endpoint
                or environ.get(OTEL_EXPORTER_OTLP_TRACES_ENDPOINT),
                "insecure": insecure,
                "credentials": credentials,
                "headers": headers
                or environ.get(OTEL_EXPORTER_OTLP_TRACES_HEADERS),
                "timeout": timeout,
                "compression": compression,
            }
        )

    def _translate_data(
        self, data: Sequence[ResourceSpans]
    ) -> ExportTraceServiceRequest:
        return ExportTraceServiceRequest(
            resource_spans=data
        )

    def export(self, spans: Sequence[ResourceSpans]) -> SpanExportResult:
        return self._export(spans)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    @property
    def _exporting(self):
        return "traces"
