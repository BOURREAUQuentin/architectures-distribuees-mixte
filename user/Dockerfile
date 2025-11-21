FROM python:3.10-alpine
# FROM python:3.11-slim

WORKDIR /app

# copy the requirements file in the workdir
COPY requirements.txt /app/requirements.txt

# install the Python requirements
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# copy the app files and directories
COPY user/ /app

# start user.py when the container is started
CMD ["python","-u","user.py"]