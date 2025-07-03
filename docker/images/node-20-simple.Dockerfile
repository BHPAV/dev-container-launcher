FROM devbox:latest

ENV NODE_VERSION=20

# Install Node.js and npm from Ubuntu repositories
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        nodejs \
        npm && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install global Node tools
USER dev
RUN npm config set prefix ~/.npm-global && \
    export PATH=$PATH:~/.npm-global/bin && \
    npm install -g yarn typescript @types/node

USER root
WORKDIR /workspace

EXPOSE 22
CMD ["/usr/sbin/sshd","-D","-e"]