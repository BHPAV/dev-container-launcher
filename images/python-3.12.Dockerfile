FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    USER=dev \
    UID=1000 \
    PYTHON_VERSION=3.12

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-server git curl sudo build-essential \
        software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-dev \
        python${PYTHON_VERSION}-venv \
        python3-pip && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1 && \
    useradd -m -u ${UID} -s /bin/bash ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    mkdir /var/run/sshd && \
    ssh-keygen -A

# Install common Python dev tools
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    python3 -m pip install pipx && \
    python3 -m pipx ensurepath

USER ${USER}
RUN python3 -m pipx install poetry ruff black mypy

USER root
COPY --chown=${USER}:${USER} authorized_keys /home/${USER}/.ssh/authorized_keys
RUN chmod 600 /home/${USER}/.ssh/authorized_keys

EXPOSE 22
CMD ["/usr/sbin/sshd","-D","-e"]
