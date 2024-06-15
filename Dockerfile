FROM python:3.11-slim-bookworm

# Update system and install dependencies
RUN apt update \
    && apt full-upgrade -y \
    && apt install build-essential bc curl -y \
    && rm -rf /var/lib/apt/lists/*

# Setup ollama
RUN curl -fsSL https://ollama.com/install.sh | sh
RUN ollama serve && ollama pull llama3:8b

# Install the app
COPY . /tmp/
RUN cd /tmp && python3.11 setup.py install
RUN rm -rf /tmp/*

WORKDIR /opt/iamksm/
COPY entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 7777
ENTRYPOINT ["bash", "entrypoint.sh"]
