.PHONY: help docker-build docker-run docker-bash docker-stop
.DEFAULT: help

help:
	@echo "make docker-build"
	@echo "	   build docker image"
	@echo "make docker-run"
	@echo "	   run docker image as container"
	@echo "make docker-bash"
	@echo "	   access docker container bash"
	@echo "make docker-stop"
	@echo "	   stop docker container"

docker-build:
	docker build -t tripleflow-frontend:latest .

docker-run:
	@if [ "$$(docker ps -q -f name=tripleflow-frontend)" ]; then \
		docker rm -f tripleflow-frontend; \
		sleep 2; \
	fi
	docker run -d --restart unless-stopped --name tripleflow-frontend -p 8080:8080 tripleflow-frontend:latest

docker-stop:
	docker rm -f tripleflow-frontend
