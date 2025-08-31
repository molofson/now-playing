# Base Python image
FROM python:3.11-bookworm

# Install system dependencies
USER root

# Install system packages and generate locale
RUN apt-get update && \
    apt-get install -y \
    locales \
    curl \
    gnupg \
    git \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    unzip \
    ca-certificates \
    bash-completion \
    vim \
    wget

# Generate the locale separately to avoid environment issues
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen && \
    update-locale LANG=en_US.UTF-8

# Set locale environment variables explicitly
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# Install Node.js + aicommits
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g aicommits && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m vscode
# Set Bash as the default shell for the vscode user (non-interactive alternative to chsh)
RUN sed -i 's|^vscode:[^:]*:[^:]*:[^:]*:[^:]*:[^:]*:[^:]*$|vscode:x:1000:1000::/home/vscode:/bin/bash|' /etc/passwd

USER vscode
WORKDIR /workspaces/now-playing

# Set up Python virtual environment
COPY --chown=vscode:vscode requirements-dev.txt /workspaces/now-playing/
RUN python -m venv /home/vscode/.venv && \
    /home/vscode/.venv/bin/pip install --upgrade pip && \
    /home/vscode/.venv/bin/pip install -r /workspaces/now-playing/requirements-dev.txt

# Path setup
ENV VIRTUAL_ENV="/home/vscode/.venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /workspaces/now-playing
