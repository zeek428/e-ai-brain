from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
API_DOCKERFILE = REPO_ROOT / "infra" / "docker" / "api.Dockerfile"
API_ENTRYPOINT = REPO_ROOT / "infra" / "docker" / "api-entrypoint.sh"
POSTGRES_DOCKERFILE = REPO_ROOT / "infra" / "docker" / "postgres-pgvector.Dockerfile"
MIGRATIONS_DIR = REPO_ROOT / "apps" / "api" / "app" / "db" / "migrations"


def test_postgres_initdb_cannot_execute_application_migrations() -> None:
    compose_source = COMPOSE_FILE.read_text(encoding="utf-8")
    postgres_image_source = POSTGRES_DOCKERFILE.read_text(encoding="utf-8")
    initdb_mounts = [
        line.strip()
        for line in compose_source.splitlines()
        if "/docker-entrypoint-initdb.d" in line
    ]

    assert all("apps/api/app/db/migrations" not in mount for mount in initdb_mounts)
    assert "apps/api/app/db/migrations" not in postgres_image_source
    assert "121_requirement_driven_rd_cutover.sql" not in postgres_image_source
    for migration_number in range(125, 129):
        assert f"{migration_number}_" not in postgres_image_source


def test_api_image_packages_migrations_at_entrypoint_default_path() -> None:
    dockerfile_source = API_DOCKERFILE.read_text(encoding="utf-8")
    entrypoint_source = API_ENTRYPOINT.read_text(encoding="utf-8")

    assert "WORKDIR /app" in dockerfile_source
    assert "COPY apps/api/app ./app" in dockerfile_source
    assert '"/app/app/db/migrations"' in entrypoint_source
    assert (MIGRATIONS_DIR / "001_init.sql").is_file()
    assert (MIGRATIONS_DIR / "121_requirement_driven_rd_cutover.sql").is_file()
    for migration_number in range(125, 129):
        assert any(MIGRATIONS_DIR.glob(f"{migration_number}_*.sql"))
