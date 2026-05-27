# ==============================================================================
# runner/Dockerfile — Sandboxed pytest execution environment
#
# WHAT IS THIS?
# This image is used in Milestone 7 to safely run patched test files.
# We never run untrusted/AI-generated code directly on the host machine.
# Instead we spin up this container with:
#   - No network access
#   - Read-only file mount
#   - Memory and time limits
#
# Build this image once:
#   docker build -t realive-runner:python ./runner
# ==============================================================================

FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /workspace

# Install pytest (the only tool this container needs)
RUN pip install --no-cache-dir pytest==8.3.3

# The test file and any fixtures are mounted at /workspace at runtime.
# This image intentionally has NO extra packages — tests that require
# them will fail, which is the correct behavior (reveals missing deps).

# Default command — overridden per-run with the specific test file path
CMD ["pytest", "--tb=short", "-v"]
