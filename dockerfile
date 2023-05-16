FROM python:3.8-slim

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["bash", "run.sh"]
# CMD ["python", "binanceapibot.py"]
# CMD ["python binanceapibot.py & python blisteners.py"]
# CMD ["parallel", "python", ":::", "binanceapibot.py", ":::", "blisteners.py"]
