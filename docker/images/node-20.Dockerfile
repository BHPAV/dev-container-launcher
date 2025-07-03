FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    USER=dev \
    UID=1000 \
    NODE_VERSION=20

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-server git curl sudo build-essential && \
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g yarn pnpm && \
    useradd -m -u ${UID} -s /bin/bash ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    mkdir /var/run/sshd && \
    ssh-keygen -A

COPY --chown=${USER}:${USER} authorized_keys /home/${USER}/.ssh/authorized_keys
RUN chmod 600 /home/${USER}/.ssh/authorized_keys

EXPOSE 22
CMD ["/usr/sbin/sshd","-D","-e"]
