.PHONY: opencode

default: up opencode

buildup:
	docker compose up --build --force-recreate -d opencode

up:
	docker compose up -d opencode

shell:
	docker compose exec -ti opencode bash

opencode:
	docker compose exec -ti opencode /home/ubuntu/.opencode/bin/opencode

down:
	docker compose down
