FROM python:3.11-slim
# FROM python:3.8-alpine

WORKDIR /app

# copy the requirements file in the workdir
COPY requirements.txt /app/requirements.txt

# install the Python requirements
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# copy the app files and directories
COPY schedule/ /app

# grpc compilation of proto files or copy of generated files
RUN python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. ./protos/schedule.proto

# start schedule.py when the container is started
CMD ["python","-u","schedule.py"]