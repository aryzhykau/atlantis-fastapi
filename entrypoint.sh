#!/bin/sh
set -e 

run_migrations(){
	uv run alembic upgrade head
	echo "migrations completed"
}

start_app(){
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
	echo "app started"
}

case "$1" in 
	domigrations)
		run_migrations
		exit 0
		;;
	startapp)
		start_app
		;;
	*)
	 	echo "unknown command $1"
		exit 1
		;;
esac 