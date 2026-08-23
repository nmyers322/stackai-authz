FROM python:3.13-slim

WORKDIR /code

ENV PYTHONPATH=/code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./src /code/src

CMD ["fastapi", "run", "src/main.py", "--host", "0.0.0.0", "--port", "80"]
