FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    USER=dev \
    UID=1000 \
    GO_VERSION=1.22

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-server git curl sudo build-essential && \
    curl -fsSL https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz | tar -C /usr/local -xz && \
    useradd -m -u ${UID} -s /bin/bash ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    mkdir /var/run/sshd && \
    ssh-keygen -A

ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/home/${USER}/go"
ENV PATH="${GOPATH}/bin:${PATH}"

COPY --chown=${USER}:${USER} authorized_keys /home/${USER}/.ssh/authorized_keys
RUN chmod 600 /home/${USER}/.ssh/authorized_keys

EXPOSE 22
CMD ["/usr/sbin/sshd","-D","-e"]
