# PostgreSQL 15 + PostGIS 3.4 + pgvector Enterprise Image
FROM postgis/postgis:15-3.4

# Install pgvector extension for high-dimensional semantic search
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        postgresql-15-pgvector \
    && rm -rf /var/lib/apt/lists/*
