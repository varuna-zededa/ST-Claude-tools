FROM ghcr.io/astral-sh/uv:0.7.21-python3.12-bookworm-slim

WORKDIR /zededa-mcp

# Apply security patches
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Copy dependency definition and logging_config.py
COPY mcp/pyproject.toml ./
COPY logging_config.py ./

# Install dependencies
RUN uv pip install --system .

# Copy the rest of your app code
COPY mcp/ .
COPY utility/ ./utility/
COPY app/prompts/ ./prompts
COPY app/swagger/ ./swagger

EXPOSE 8000

CMD ["uv", "run", "mcpserver.py"]
