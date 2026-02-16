# Base image
FROM python:3.11
#FROM ubuntu:latest

WORKDIR /home/trending
LABEL maintainer="Stefan Bogdanel <stefan@izdrail.com>"

# Install dependencies
RUN apt update && apt install -y \
    curl \
    plocate \
    net-tools \
    && apt-get clean

# Install pip packages and supervisord
RUN pip install --no-cache-dir --upgrade pip \
    && pip install supervisor pipx 



WORKDIR /home/trending
# Install Python packages

RUN pip install fastapi uvicorn httpx pydantic


# Customize shell with Zsh
RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v1.1.5/zsh-in-docker.sh)" -- \
    -t https://github.com/denysdovhan/spaceship-prompt \
    -a 'SPACESHIP_PROMPT_ADD_NEWLINE="false"' \
    -a 'SPACESHIP_PROMPT_SEPARATE_LINE="false"' \
    -p git \
    -p ssh-agent \
    -p https://github.com/zsh-users/zsh-autosuggestions \
    -p https://github.com/zsh-users/zsh-completions

COPY . .


# Supervisord configuration
COPY docker/supervisord.conf /etc/supervisord.conf

# Update database
RUN updatedb


# Expose application port
EXPOSE 1097



# Run application
ENTRYPOINT ["supervisord", "-c", "/etc/supervisord.conf", "-n"]