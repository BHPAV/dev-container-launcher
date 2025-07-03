FROM devbox:latest

ENV PYTHON_VERSION=3.12

# Install Python 3.12 from Ubuntu's default repositories
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-dev \
        python3-venv \
        python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install common Python dev tools
USER dev
RUN python3 -m pip install --user --upgrade pip setuptools wheel && \
    python3 -m pip install --user poetry ruff black mypy pytest

USER root
WORKDIR /workspace

EXPOSE 22
CMD ["/usr/sbin/sshd","-D","-e"]