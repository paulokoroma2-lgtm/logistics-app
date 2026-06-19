import psycopg2

conn = psycopg2.connect(
    "postgresql://neondb_owner:npg_oDk2UqR3AtBl@ep-dark-bird-abr04jkk.eu-west-2.aws.neon.tech/neondb?sslmode=require"
)

print("CONNECTED")