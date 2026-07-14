# Isolated Deployment Protocol Regression Environment

This environment is intentionally separate from the application development stack. It provides a disposable SSH host, Docker Compose target, and Jenkins instance for protocol regression: Runner claim, non-mutating probe, execution, log return, timeout handling, and rollback.

It is not a release-candidate gate. Release candidates must use the existing non-production Jenkins acceptance Job through `.github/workflows/nonproduction-jenkins-acceptance.yml`; that workflow creates only an AI Brain deployment record and never creates or reconfigures a deployment environment.

It must never be pointed at production hosts, production Docker daemons, or production Jenkins.

## Start the providers

Generate a disposable SSH key pair and start the services:

```bash
ssh-keygen -t ed25519 -N '' -f /tmp/ai-brain-deployment-e2e
export E2E_SSH_AUTHORIZED_KEY="$(cat /tmp/ai-brain-deployment-e2e.pub)"
docker compose -f infra/e2e/deployment-external/docker-compose.yml up -d --build
```

Jenkins is exposed only on `127.0.0.1:18080`; its disposable jobs are `e2e-deploy`, `e2e-rollback`, and `e2e-verify`. It deliberately has no authentication and disables CSRF crumb validation so the disposable platform fixture can exercise `buildWithParameters`; never reuse this Jenkins image or configuration outside the isolated E2E environment. The SSH target is exposed only on `127.0.0.1:2222`.

## Configure the Runner and platform

1. Create a deployment-trust-domain Runner in AI Brain and install its package on the host that owns the Docker daemon.
2. Merge the `deployment_targets` block from `runner_config.deployment_targets.json` into its local `runner_config.json`; replace the three path placeholders with absolute local paths and the disposable SSH key locations.
3. Start the Runner and wait for its heartbeat. It will publish a configuration fingerprint for each target; the platform never receives the host, command, key, or Docker directory.
4. In the product/environment execution-resource page, authorize `e2e-ssh`, `e2e-ssh-timeout` and `e2e-docker` for the isolated test product.
5. Create a Jenkins connection for `http://127.0.0.1:18080`, authorize it for the same product/environment, and create an `e2e-deploy` deployment scheme. Use only disposable credentials or no-security local Jenkins.
6. Create separate SSH, Docker and Jenkins deployment records that are ready to start. Create one additional SSH deployment using `e2e-ssh-timeout` with a 30-second scheme timeout to exercise timeout handling. Export their IDs plus a disposable admin bearer token as the `AI_BRAIN_E2E_*` variables used below.

## Run the optional protocol regression

```bash
cd apps/api
AI_BRAIN_E2E_BASE_URL=http://127.0.0.1:8000 \
AI_BRAIN_E2E_BEARER_TOKEN=replace-with-disposable-token \
AI_BRAIN_E2E_SSH_DEPLOYMENT_ID=deployment_ssh \
AI_BRAIN_E2E_DOCKER_DEPLOYMENT_ID=deployment_docker \
AI_BRAIN_E2E_JENKINS_DEPLOYMENT_ID=deployment_jenkins \
AI_BRAIN_E2E_TIMEOUT_DEPLOYMENT_ID=deployment_ssh_timeout \
uv run pytest -m deployment_protocol_regression tests/integration/test_external_deployment_e2e.py -q
```

The test first calls the real connectivity probe, waits for evidence, starts the deployment, waits for Runner/Jenkins completion and returned logs, then requests and verifies rollback. The timeout target validates bounded timeout reporting. The protocol regression group is skipped unless its three deployment IDs are provided; the timeout case is skipped only when its separate deployment ID is absent. The GitHub Actions workflow is manual and requires a self-hosted runner labelled `deployment-e2e` with the same isolated environment.

## Configure the release-candidate Jenkins gate

Create a non-mutating Jenkins acceptance Job in an existing non-production Jenkins environment. It must be available to the deployment scheme's configured credential and should only validate the intended deployment integration, such as artifact access, Jenkins parameters, Runner log return and status synchronization. Configure the `nonproduction-jenkins-gate` GitHub Environment with the two secrets and five variables listed by `.github/workflows/nonproduction-jenkins-acceptance.yml`, then mark the **Non-production Jenkins deployment acceptance** check as required for release branches or invoke it from the release-candidate workflow via `workflow_call`.

## Clean up

```bash
docker compose -f infra/e2e/deployment-external/docker-compose.yml down --volumes
rm -f /tmp/ai-brain-deployment-e2e /tmp/ai-brain-deployment-e2e.pub
```
