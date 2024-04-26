docker build -t fat-mango-compiler .
docker run -it --name fat-mango-compiler -v $(pwd):/usr/src/app fat-mango-compiler