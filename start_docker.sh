docker build -t fat-mango-compiler .
docker run -it --rm --name fat-mango-compiler -v $(pwd):/usr/src/app fat-mango-compiler