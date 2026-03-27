FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir pydantic pyyaml openai
EXPOSE 7860
CMD ["python", "inference.py"]