# Workmate Compose Setup

This repository contains a multi-service setup for the Workmate project. To start the stack you need a `.env` file with your environment specific configuration.

```
cp .env.example .env
# adjust values inside .env
```

Build and start all services via Docker Compose:

```
docker-compose up --build
```


