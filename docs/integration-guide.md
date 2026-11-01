# Integration guide: <Project name>

> Audience: an engineer at the customer who has never seen this project. They should get from
> zero to a verified working integration using only this page.

## What you get

<!-- One paragraph: what the integration does for them, in their terms. -->

## Before you start

- Access you need: <!-- accounts, roles, network access -->
- Tools: <!-- versions -->
- Time: about <!-- N --> minutes

## How it fits

<!-- Diagram or numbered steps: what calls what, and in which direction data flows. -->

## Set up

1. <!-- Step, with the exact command or click path -->
2.
3.

## Configuration

| Setting | Required | Example | What it does |
| --- | --- | --- | --- |
| `ANTHROPIC_API_KEY` | yes | (secret) | Calls the Claude API; set a spend limit on this key |

## Verify it works

<!-- One request or action and the exact response they should see. -->

## Data and security

- Data that leaves your environment: <!-- fields, and where it goes -->
- Data that is stored, and for how long: <!-- -->
- How secrets are handled: <!-- -->
- Tenant isolation: <!-- how one customer's data is kept from another's -->

## Limits and cost

<!-- Rate limits, payload sizes, expected cost per 1,000 requests, and how to cap it. -->

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| | | |

## Remove the integration

<!-- How to turn it off and delete stored data. -->
