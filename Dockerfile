FROM python:3.12-slim
WORKDIR /app
COPY . .
# Added networkx and matplotlib for the visualizer
RUN pip install --no-cache-dir pydantic pyyaml openai gradio networkx matplotlib
EXPOSE 7860
ENV GRADIO_SERVER_NAME="0.0.0.0"
CMD ["python", "inference.py"]