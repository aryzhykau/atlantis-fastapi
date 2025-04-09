#!/bin/sh
set -e 


run_migrations(){
	poetry run alembic upgrade head
	echo "migrations start"
}

start_app(){
	poetry run uvicorn app.main:app --reload --host 0.0.0.0
	echo "start app"
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