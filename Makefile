# Convenience Makefile for common tasks
.PHONY: help run migrate makemigrations test shell docker-build docker-up collectstatic

help:
	@echo "Available targets: run, migrate, makemigrations, test, shell, docker-build, docker-up, collectstatic"

run:
	python manage.py runserver

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

test:
	python manage.py test

shell:
	python manage.py shell

docker-build:
	docker build -t yd-cleaning:local .

docker-up:
	docker-compose up --build

collectstatic:
	python manage.py collectstatic --noinput
