#!/bin/sh
.PHONY: build dev down ssh publish
build:
	docker image rm -f izdrail/git.izdrail.com:latest && docker build --no-cache -t izdrail/git.izdrail.com:latest --progress=plain .
	docker-compose -f docker-compose.yml up  --remove-orphans

dev:
	docker-compose up

down:
	docker-compose down
ssh:
	docker exec -it git.izdrail.com /bin/zsh
publish:
	docker push izdrail/git.izdrail.com:latest
