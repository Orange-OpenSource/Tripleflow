.PHONY: help docker-build docker-run docker-run-bash docker-stop

.DEFAULT: help

help:
	@echo "make docker-build"
	@echo "	   build docker image"
	@echo "make docker-run"
	@echo "	   run docker image as container as daemon"
	@echo "make docker-run-bash"
	@echo "	   run docker image as container as bash"
	@echo "make docker-stop"
	@echo "	   stop docker container"

docker-build:
	docker build --tag=tripleflow-api:latest .

docker-run:
	docker run -d -v '$(CURDIR)/src':/app/tripleflow-api -v '$(CURDIR)/data':/app/data -p 8081:8081 --name=tripleflow-api tripleflow-api:latest

docker-stop:
	docker stop tripleflow-api
