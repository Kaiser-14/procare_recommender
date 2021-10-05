#!/bin/bash
git reset --hard
git pull

docker build -t procare_re:1.0 .
docker-compose up -d
