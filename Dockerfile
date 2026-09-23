FROM python:3.11-slim

WORKDIR /app
COPY . /app
ENV PYTHONPATH=/app/src
EXPOSE 8765
RUN python -m simulation_copilot.build_assets --root /app
CMD ["python", "-m", "simulation_copilot.server", "--root", "/app", "--host", "0.0.0.0", "--port", "8765"]

