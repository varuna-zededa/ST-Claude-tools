"""
Unified logging configuration for the Zededa AI agents.
"""
import logging
import os
from pathlib import Path


def setup_logging(name: str = __name__,
                  log_file: str = None) -> logging.Logger:
    """
    Setup standardized logging to write to both file and console (stdout).
    This function configures the root logger to write to both destinations
    so logs are visible in both the log file and docker compose logs.
    
    Args:
        name: Logger name (typically __name__)
        log_file: Optional log file path. If None, uses default based on module name.
    
    Returns:
        A logger instance for the specified name.
    """
    logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)
    logging.getLogger("litellm").setLevel(logging.ERROR)
    logging.getLogger("httpcore.http11").setLevel(logging.ERROR)
    logging.getLogger("httpcore.connection").setLevel(logging.ERROR)
    logging.getLogger("faker.factory").setLevel(logging.ERROR)

    # Silence fakeredis and docket worker debug logging (used by FastMCP)
    logging.getLogger("fakeredis").setLevel(logging.ERROR)
    logging.getLogger("docket").setLevel(logging.WARNING)
    logging.getLogger("docket.worker").setLevel(logging.WARNING)

    # Silence MCP framework debug logging
    logging.getLogger("mcp").setLevel(logging.WARNING)
    logging.getLogger("mcp.server").setLevel(logging.WARNING)
    logging.getLogger("mcp.server.streamable_http").setLevel(logging.WARNING)
    logging.getLogger("mcp.server.streamable_http_manager").setLevel(
        logging.WARNING)
    logging.getLogger("sse_starlette").setLevel(logging.WARNING)
    logging.getLogger("sse_starlette.sse").setLevel(logging.WARNING)

    # Silence FastMCP internal library logging (fakeredis and docket for queue management)
    logging.getLogger("fakeredis").setLevel(logging.WARNING)
    logging.getLogger("fakeredis._basefakesocket").setLevel(logging.WARNING)
    logging.getLogger("docket").setLevel(logging.WARNING)
    logging.getLogger("docket.worker").setLevel(logging.WARNING)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s'
    )

    # Set default log file if not provided
    if log_file is None:
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        module_name = name.split('.')[-1] if '.' in name else name
        log_file = log_dir / f"{module_name}.log"

    # Get the root logger and clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.DEBUG)

    # Create and add console handler (for stdout/docker logs)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Create and add file handler
    try:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except (OSError, IOError) as e:
        # If file logging fails, continue with console logging only
        print(f"WARNING: Could not create log file {log_file}: {e}")
        logging.warning(f"Could not create log file {log_file}: {e}")

    # Now that logging is configured, use the logger to announce it.
    # This will go to both the file and console.
    logging.info(f"Logging configured - File: {log_file}, Console: enabled")

    # Return a specific logger for the module, which will inherit the root setup.
    return logging.getLogger(name)
