FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu-22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install python3.10, babeltrace with python bindings
WORKDIR /tmp
RUN apt-get update && \
	apt-get install -y software-properties-common && \
	apt-get update

RUN apt-get update && apt-get install -y build-essential\
	libglib2.0-dev\
	autoconf\
	libc-dev\
	libtool\
	automake\
	bison\
	flex\
	swig\
	python3-dev\
	python3-pip\
	# python-setuptools\
	# python-pkg-resources\
	git\
	babeltrace2\
	python3-bt2

RUN git clone https://git.efficios.com/babeltrace.git -b stable-2.0 &&\
	cd babeltrace &&\
	./bootstrap &&\
	./configure --enable-python-bindings --disable-debug-info --disable-man-pages &&\
	make -j $(nproc) &&\
	make install

# Install poetry
RUN pip install "poetry==1.1.14"
RUN pip install setuptools

# Resolve python dependencies
WORKDIR /code
COPY poetry.lock poetry.toml pyproject.toml ./
RUN poetry config virtualenvs.create false --local &&\
	poetry install --no-interaction --no-ansi

# Copy sources
COPY . .

# Entrypoint
ENTRYPOINT ["python3", "src/replayer.py"]
