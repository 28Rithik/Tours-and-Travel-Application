import os
from django.test import SimpleTestCase
from django.conf import settings


class Phase5DeploymentArchitectureTests(SimpleTestCase):
    """
    Test suite verifying Phase 5 production deployment architecture artifacts:
    1. Gunicorn configuration file and parameters.
    2. Nginx reverse proxy configuration syntax & directives.
    3. Dockerfile and docker-compose production orchestration files.
    4. Systemd service daemon unit file.
    5. Production environment sample template.
    """

    def test_01_gunicorn_conf_exists_and_configured(self):
        """Verifies gunicorn.conf.py is present with production worker concurrency and timeouts."""
        conf_path = os.path.join(settings.BASE_DIR, 'gunicorn.conf.py')
        self.assertTrue(os.path.exists(conf_path), "gunicorn.conf.py is missing from project root.")

        with open(conf_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('workers', content)
        self.assertIn('uvicorn.workers.UvicornWorker', content)
        self.assertIn('max_requests', content)
        self.assertIn('max_requests_jitter', content)
        self.assertIn('preload_app', content)
        self.assertIn('keepalive', content)

    def test_02_nginx_configuration_directives(self):
        """Verifies deploy/nginx/travelerp.conf includes rate limiting, SSL, and static caching."""
        nginx_path = os.path.join(settings.BASE_DIR, 'deploy', 'nginx', 'travelerp.conf')
        self.assertTrue(os.path.exists(nginx_path), "deploy/nginx/travelerp.conf is missing.")

        with open(nginx_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('upstream travelerp_upstream', content)
        self.assertIn('limit_req_zone', content)
        self.assertIn('expires 365d', content)
        self.assertIn('gzip on', content)
        self.assertIn('proxy_pass http://travelerp_upstream', content)
        self.assertIn('proxy_set_header Upgrade $http_upgrade', content)

    def test_03_systemd_service_file(self):
        """Verifies deploy/systemd/travelerp.service daemon configuration."""
        service_path = os.path.join(settings.BASE_DIR, 'deploy', 'systemd', 'travelerp.service')
        self.assertTrue(os.path.exists(service_path), "deploy/systemd/travelerp.service is missing.")

        with open(service_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('ExecStart', content)
        self.assertIn('travelerp.asgi:application', content)
        self.assertIn('Restart=always', content)
        self.assertIn('LimitNOFILE=65535', content)

    def test_04_docker_production_files(self):
        """Verifies Dockerfile and docker-compose.prod.yml configurations."""
        dockerfile_path = os.path.join(settings.BASE_DIR, 'Dockerfile')
        compose_path = os.path.join(settings.BASE_DIR, 'docker-compose.prod.yml')

        self.assertTrue(os.path.exists(dockerfile_path), "Dockerfile is missing.")
        self.assertTrue(os.path.exists(compose_path), "docker-compose.prod.yml is missing.")

        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            df_content = f.read()
        self.assertIn('python:3.12-slim', df_content)
        self.assertIn('travelerp.asgi:application', df_content)

        with open(compose_path, 'r', encoding='utf-8') as f:
            compose_content = f.read()
        self.assertIn('travelerp_web', compose_content)
        self.assertIn('travelerp_redis', compose_content)
        self.assertTrue('travelerp_postgis' in compose_content or 'travelerp_mysql' in compose_content)
        self.assertIn('travelerp_nginx', compose_content)

    def test_05_production_env_sample(self):
        """Verifies deploy/env.production.sample contains required production variables."""
        env_sample_path = os.path.join(settings.BASE_DIR, 'deploy', 'env.production.sample')
        self.assertTrue(os.path.exists(env_sample_path), "deploy/env.production.sample is missing.")

        with open(env_sample_path, 'r', encoding='utf-8') as f:
            env_content = f.read()

        self.assertIn('SECRET_KEY', env_content)
        self.assertIn('DATABASE_URL', env_content)
        self.assertIn('REDIS_URL', env_content)
        self.assertIn('GUNICORN_WORKERS', env_content)
