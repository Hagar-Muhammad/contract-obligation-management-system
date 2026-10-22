-- Runs once, when the Postgres volume is first created.
-- A separate database keeps the test suite from touching development data.
CREATE DATABASE coms_test OWNER coms;
