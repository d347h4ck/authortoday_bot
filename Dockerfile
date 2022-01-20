FROM python:3.9
WORKDIR /code
COPY requirements.txt .

RUN pip install -r requirements.txt

COPY src/ .

CMD ["sh", "-c", "python author.py init ; python author.py"]