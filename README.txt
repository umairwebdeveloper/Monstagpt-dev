-----------------------------------
Getting everything up and running
-----------------------------------

1. Copy .env.example to .env

2. Add your email and Stripe credentials to your .env file. but not needed

3. Open a terminal configured to run Docker and then run:

docker compose down -v
docker compose build --no-cache
docker compose up
./run flask db reset --with-testdb
./run flask db seed

log in with the seed credientials in the .env file

the rest is not needed.
./run format:imports
./run format
./run lint
./run test

