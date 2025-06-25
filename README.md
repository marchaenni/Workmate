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



## CI/CD Deployment on AWS EC2

This project includes a GitHub Actions workflow that builds the services, runs the tests and deploys the stack to an EC2 instance via SSH.

### Setup

1. Prepare an EC2 instance with Docker and `docker-compose` installed.
2. Clone this repository on the server, e.g. into `~/workmate`.
3. In your GitHub repository settings create the following secrets:
   - `EC2_HOST` – Public hostname or IP of the EC2 server.
   - `EC2_USER` – SSH username.
   - `EC2_SSH_KEY` – Private key with access to the server.
4. Push changes to the `main` branch. The workflow defined in `.github/workflows/deploy.yml` will run the tests and update the running stack on the EC2 instance.
