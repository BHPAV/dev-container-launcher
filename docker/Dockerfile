ARG BASE_IMAGE=ubuntu:22.04
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    USER=dev \
    UID=1000

# Install essential packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-server \
        git \
        curl \
        sudo \
        build-essential \
        python3-pip \
        ca-certificates \
        locales && \
    locale-gen en_US.UTF-8 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set locale
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# Create user with specific sudo permissions
RUN useradd -m -u ${UID} -s /bin/bash ${USER} && \
    mkdir -p /etc/sudoers.d && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USER} && \
    chmod 0440 /etc/sudoers.d/${USER}

# Configure SSH
RUN mkdir /var/run/sshd && \
    ssh-keygen -A && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
    echo "AllowUsers ${USER}" >> /etc/ssh/sshd_config

# Setup SSH for user
USER ${USER}
RUN mkdir -p /home/${USER}/.ssh && \
    chmod 700 /home/${USER}/.ssh

USER root
COPY --chown=${USER}:${USER} authorized_keys /home/${USER}/.ssh/authorized_keys
RUN chmod 600 /home/${USER}/.ssh/authorized_keys

# Create workspace directory
RUN mkdir -p /workspace && \
    chown ${USER}:${USER} /workspace

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D", "-e"]