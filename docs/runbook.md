# Runbook: <Project name>

> Audience: whoever is on call at 2 a.m. Every section answers "what do I do now?"

## Service at a glance

- What it does: <!-- one line -->
- Depends on: <!-- Claude API, database, queues, customer webhooks -->
- Where it runs: <!-- local demo / AWS account and region -->
- Logs: <!-- where, and the query to start with -->
- Health check: <!-- URL or command, and what healthy looks like -->

## Alerts

| Alert | What it means | First action |
| --- | --- | --- |
| | | |

## Common incidents

### Claude API errors or timeouts
- Check: <!-- status page, error rate, 429 vs 5xx -->
- Fix: <!-- retries, backoff, fallback behavior -->

### Costs spiking
- Check: <!-- Console usage for this project's key -->
- Stop it: <!-- kill switch, lower the spend limit, revoke the key -->

### Wrong or unsafe model output reported by a customer
- Check: <!-- find the request by ID, inputs, prompt version -->
- Fix: <!-- roll back the prompt, add an eval case, tell the customer -->

### Data shown to the wrong tenant
- Stop it: <!-- disable the endpoint -->
- Then: <!-- scope the exposure, tell the affected customers, write the post-incident review -->

## Deploy and roll back

<!-- Exact commands. Rollback first. -->

## Rotate a secret

<!-- Which key, where it is set, and how to verify the new one works. -->

## After an incident

Write a short review in `docs/incidents/YYYY-MM-DD-<slug>.md`: timeline, impact, root cause,
what you changed, and the test or alert that now catches it.
