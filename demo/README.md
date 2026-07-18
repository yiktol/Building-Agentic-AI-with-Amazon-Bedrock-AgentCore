# MLAGAC Module Demos

Instructor-led demonstrations for the Machine Learning & AI on AWS: Generative AI Agents Course.

| Module | Folder | Topic |
|--------|--------|-------|
| Module 02 | [`runtime/`](runtime/) | AgentCore Runtime and Framework Integration |
| Module 03 | [`identity/`](identity/) | Security and Identity Management |
| Module 04 | [`tools-gateway/`](tools-gateway/) | Tool Integration and AgentCore Gateway |
| Module 05 | [`memory/`](memory/) | AgentCore Memory — Short-Term, Long-Term, and Security |
| Module 06 | [`observability/`](observability/) | Production Monitoring, Observability, and Evaluations |
| Module 07 | [`harness/`](harness/) | AgentCore Harness — Managed Agent Loop (Zero Code) |

See the module-specific README for step-by-step instructions.

## Architecture

All AWS resources are provisioned via CloudFormation templates. Demo scripts only deploy/invoke/cleanup AgentCore Runtimes.

```
1. Deploy CFN stack (creates Cognito, IAM, S3)
2. python deploy.py   (deploys agent to AgentCore Runtime)
3. python invoke.py   (sends prompts)
4. python cleanup.py  (deletes runtime)
5. Delete CFN stack when done
```
