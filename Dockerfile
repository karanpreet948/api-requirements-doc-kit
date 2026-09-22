FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apidoc/ ./apidoc/
COPY examples/ ./examples/

# Default: generate the requirements document for the bundled example spec.
# Override the command to point at a different spec/output path, e.g.:
#   docker run --rm -v "$PWD/out:/app/out" apidoc \
#       generate --spec examples/customer_profile_api.yaml --output out/requirements.md
ENTRYPOINT ["python", "-m", "apidoc"]
CMD ["generate", "--spec", "examples/customer_profile_api.yaml", "--output", "out/customer_profile_api_requirements.md"]
