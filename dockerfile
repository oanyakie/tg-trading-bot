FROM python:3.8-slim

COPY . .

# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install poetry
RUN poetry install

CMD ["python", "binanceapibot.py"]