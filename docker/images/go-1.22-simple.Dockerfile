FROM devbox:latest

ENV GO_VERSION=1.22

# Install Go
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        golang-go && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up Go environment
USER dev
RUN mkdir -p ~/go/{bin,src,pkg} && \
    echo 'export GOPATH=$HOME/go' >> ~/.bashrc && \
    echo 'export PATH=$PATH:$GOPATH/bin' >> ~/.bashrc

USER root
WORKDIR /workspace

EXPOSE 22
CMD ["/usr/sbin/sshd","-D","-e"]