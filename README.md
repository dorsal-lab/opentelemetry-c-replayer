# LTTng OTel Traces Adaptor

Read all opentelemetry-c CTF traces and send them to an OTel collector using [OTLP for GRPC](https://opentelemetry.io/docs/reference/specification/protocol/exporter/).

## Architecture

This repository provides configurations for an OpenTelemetry collector with Jaeger, Zipkin and Prometheus observability backends.
The picture below shows how components are connected. Arrows represent how data flows.

![Replayer Architecture](architecture.png)

- First, you need to have userspace CTF traces generated using the [opentelemetry-c](https://github.com/augustinsangam/opentelemetry-c) project.
- [replayer.py](src/replayer.py) can read traces directly from the CTF traces folder and send telemetry data to the OpenTelemetry collector.
- The collector will automatically forward data to Jaeger, Zipkin and Prometheus observability backends.

## Run the replayer

### Setup the collector and observability backends

```sh
docker-compose up -d
```

After this :

- OpenTelemetry collector GRPC receiver will be available on port 4317.
- Jaeger UI will be available at [http://localhost:16686](http://localhost:16686)
- Zipkin UI will be available at [http://localhost:9411](http://localhost:9411)
- Prometheus UI will be available at [http://localhost:9090](http://localhost:9090)

### Run the replayer

```sh
docker build -t otel-replayer .
docker run -it --net=host -v /path/to/ctf/traces:/ctf-traces otel-replayer -i /ctf-traces -e http://localhost:4317
```

If you wish to run the replayer locally without using docker :

```sh
pip install "poetry==1.1.14"
poetry config virtualenvs.create false --local
poetry install
python3 src/replayer.py -i path/to/ctf/traces -e http://localhost:4317
```
