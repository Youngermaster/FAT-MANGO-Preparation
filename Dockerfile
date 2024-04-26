FROM ubuntu:latest

# Install essential packages
RUN apt-get update && \
    apt-get install -y g++ gcc multiarch-support && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /usr/src/app

# By default, run a shell
CMD ["/bin/bash"]
