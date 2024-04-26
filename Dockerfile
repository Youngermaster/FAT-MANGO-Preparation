FROM ubuntu:latest

# Install essential packages
RUN apt-get update -y && apt-get -y install curl && \
    apt-get install -y g++ gcc vim git cmake g++ build-essential && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /usr/src/app

# By default, run a shell
CMD ["/bin/bash"]
