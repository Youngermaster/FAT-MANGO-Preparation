# FAT MANGO Preparation

This repo contains all my coding preparation to get into **FAT MANGO** industries, also for the _ICPC_ competitions, _CodeForces_ contests, and the _most important thing_, **Learn a lot to Improve my programming skills to be able to Change the World**.

> Note\*: FAT MANGO -> Facebook, Amazon, Twitter, Microsoft, Apple, Netflix, Google, and Oracle.

## Using Docker for Isolated Development Environment

To ensure that your development environment is consistent and does not interfere with other projects, I have set up a Docker container for compiling and running your C++ code. Here's how to use it:

1. **Build the Docker Image**: Run the `start_docker.sh` script in your terminal to build and start the Docker container. This script will use the `Dockerfile` in the repository to create an image with all the necessary tools installed.

   ```bash
   ./start_docker.sh
   ```

2. **Compile and Run Your Code**: I have the `compile_template.sh` script template to compile your code. This template will show you how to compile your C++ code with `g++` and the required flags for a standard Competitive Programming environment. You can modify this script to compile and run your code as needed or manually compile your code using `g++`.

   ```bash
   ./compile_template.sh
   ```

3. **Exiting the Container**: Once you are done, you can exit the container by typing `exit`. The `--rm` flag in the `start_docker.sh` script ensures that the container is removed after you exit, keeping your system clean.

## Contest Problems

These are some of the places where I solve problems, each one has a folder and
subfolders for different programming languages and different approaches.

```bash
├── CodeForces
├── FacebookCarrers
├── GitHubAssets
└── LeetCode
└── RandomCodes
```

## Name idea

The name idea was inspired by:
![NameIdea](GitHubAssets/NameIdea.png)
