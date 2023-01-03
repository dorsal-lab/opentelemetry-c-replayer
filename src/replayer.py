"""
replayer.py

Read all opentelemetry-c CTF traces and send them to an
Opentelemetry collector using OpenTelelemetry Protocol for GRPC.
"""
import logging
from argparse import ArgumentParser
from pathlib import Path

import bt2
from google.protobuf.message import DecodeError
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans
from opentelemetry.proto.metrics.v1.metrics_pb2 import ResourceMetrics
from opentelemetry.sdk.trace.export import SpanExportResult
from otlp_metrics_exporter import OTLPMetricExporter
from otlp_span_exporter import OTLPSpanExporter
from tqdm.auto import tqdm
from opentelemetry.sdk.metrics.export import (
    MetricExportResult
)


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="""
            Read all opentelemetry-c CTF traces and send them to an Opentelemetry collector
            using OpenTelelemetry Protocol for GRPC.
        """,
        epilog="""
            Instead, you can also configure the collector GRPC server using the following environment variables :
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE, OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
            OTEL_EXPORTER_OTLP_METRICS_ENDPOINT, OTEL_EXPORTER_OTLP_METRICS_HEADERS,
            OTEL_EXPORTER_OTLP_METRICS_INSECURE, OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
            OTEL_EXPORTER_OTLP_METRICS_TIMEOUT, OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,  OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
            OTEL_EXPORTER_OTLP_TRACES_ENDPOINT, OTEL_EXPORTER_OTLP_TRACES_HEADERS, OTEL_EXPORTER_OTLP_TRACES_INSECURE,
            OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
            Description of all those environment variables are available here :
            https://opentelemetry.io/docs/reference/specification/protocol/exporter/#configuration-options
        """
    )
    parser.add_argument('-i', '--ctf-traces-folder-path',
                        action='store',
                        help='The path of folder where ctf traces',
                        required=True,
                        type=Path,
                        dest='input_folder')
    parser.add_argument('-e', '--otel-exporter-otlp-traces-endpoint',
                        action='store',
                        help='The OTel collector GRPC server endpoint. If set, we assume the endpoint is insecure',
                        required=False,
                        type=str,
                        dest='otel_exporter_otlp_traces_endpoint')
    return parser


if __name__ == "__main__":

    logging.root.setLevel(logging.INFO)

    args = get_parser().parse_args()

    if not args.input_folder.is_dir():
        logging.fatal(
            "The path of the CTF traces must be passed as first argument of the script.")
        exit(1)

    # Create the span exporter
    span_exporter = OTLPSpanExporter(
        endpoint=args.otel_exporter_otlp_traces_endpoint,
        insecure=True if args.otel_exporter_otlp_traces_endpoint else None
    )

    # Create the metrics exporter
    metrics_exporter = OTLPMetricExporter(
        endpoint=args.otel_exporter_otlp_traces_endpoint,
        insecure=True if args.otel_exporter_otlp_traces_endpoint else None
    )

    ust_traces_folders = list(
        str(p) for p in args.input_folder.glob("**/ust") if p.is_dir())
    logging.info("Found %d ust traces folders : %s", len(ust_traces_folders), str(ust_traces_folders))

    # Create a progress bar
    n_ust_events = sum(sum(
        1 for _ in bt2.TraceCollectionMessageIterator(p)) for p in ust_traces_folders)
    logging.info("Found %d ust trace events", n_ust_events)
    pbar = tqdm(total=n_ust_events)

    # Iterate over trace events
    logging.info("Exporting telemetry data ...")
    n_tel_data = 0
    n_tel_data_exported = 0
    for ust_traces_folder in ust_traces_folders:
        for msg in bt2.TraceCollectionMessageIterator(ust_traces_folder):
            pbar.update(1)
            # pylint: disable=protected-access
            if not isinstance(msg, bt2._EventMessageConst):
                continue
            # An event message holds a trace event.
            ev = msg.event

            if ev.name.startswith("opentelemetry:"):
                n_tel_data += 1

            if ev.name == "opentelemetry:resource_spans":
                # Export resource spans
                resource_spans_bytes = bytes(list(ev['resource_spans']))

                # resource_spans_str_as_bytes = resource_spans_str.encode()
                # print(type(resource_spans_str_as_bytes))
                resource_spans = ResourceSpans()
                try:
                    resource_spans.ParseFromString(resource_spans_bytes)
                except DecodeError:
                    logging.error("Unable to parse one %s event", ev.name)
                    continue
                # TODO (augustinsangam): In future export spans in group
                # Exporting spans one by one
                result = span_exporter.export([resource_spans])
                if result == SpanExportResult.SUCCESS:
                    n_tel_data_exported += 1
                else:
                    logging.error(
                        "Unable to export trace id %s",
                        resource_spans.scope_spans[0].spans[0].trace_id)

            elif ev.name == "opentelemetry:resource_metrics":
                # Export resource metrics
                resource_metrics_bytes = bytes(list(ev['resource_metrics']))

                resource_metrics = ResourceMetrics()
                try:
                    resource_metrics.ParseFromString(resource_metrics_bytes)
                except DecodeError:
                    logging.error("Unable to parse one %s event", ev.name)
                    continue

                # TODO (augustinsangam): In future export metrics in group
                # Exporting metrics one by one
                result2 = metrics_exporter.export([resource_metrics])
                if result2 == MetricExportResult.SUCCESS:
                    n_tel_data_exported += 1
                else:
                    logging.error(
                        "Unable to export trace id %s",
                        resource_metrics.scope_metrics[0].metrics[0].name)

            elif ev.name == "opentelemetry:resource_logs":
                # TODO (augustinsangam): Add supports for logs
                pass

    # Stop and cleanup progress bar
    pbar.close()

    logging.info("Exporting done. %d/%d telemetry data exported.",
                 n_tel_data_exported, n_tel_data)
