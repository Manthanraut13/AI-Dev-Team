```
# API Reference

The backend exposes a set of REST endpoints to manage AI‑driven software projects.  
All endpoints are versioned under `/api`.  The API is stateless and uses JSON for
request and response bodies.  Authentication is handled via API keys in the
environment (see *Required API Keys* in the README).

> **Health Check**  
> The `/health` endpoint is a lightweight probe that can be used by load balancers,
> CI pipelines, or monitoring tools to verify that the service is running.

---

## Health Check

| Method | Endpoint | Description | Request | Response | Status Codes |
|--------|----------|-------------|---------|----------|--------------|
| **GET** | `/health` | Returns the health status of the service. | None | `{"status":"healthy"}` | `200 OK` (healthy) <br> `503 Service Unavailable` (unhealthy) |

> **Example**  
> ```bash
> curl -i http://localhost:8001/health
> HTTP/1.1 200 OK
> Content-Type: application/json
> 
> {"status":"healthy"}
> ```

---

## Project Management

| Method | Endpoint | Description | Request Body | Response Body | Status Codes |
|--------|----------|-------------|--------------|---------------|--------------|
| **POST** | `/api/projects` | Start a new project generation. | `{"idea":"Build a note‑taking app"}` | `{"project_id":"1234","status":"queued"}` | `202 Accepted` |
| **GET** | `/api/projects/{id}` | Retrieve the current state of a project. | None | `{"project_id":"1234","status":"in_progress","progress":45}` | `200 OK` |
| **POST** | `/api/projects/{id}/approve` | Approve or reject a checkpoint. | `{"action":"approve"}` | `{"project_id":"1234","status":"approved"}` | `200 OK` |
| **POST** | `/api/projects/{id}/research` | Trigger ad‑hoc web research. | `{"query":"fastapi pagination"}` | `{"project_id":"1234","research_id":"r5678"}` | `202 Accepted` |
| **POST** | `/api/projects/{id}/github` | Commit changes and create a PR. | `{"commit_message":"Add health check"}` | `{"project_id":"1234","pr_url":"https://github.com/.../pull/1"}` | `201 Created` |

---

## WebSocket

| Method | Endpoint | Description |
|--------|----------|-------------|
| **WS** | `/ws/{id}` | Real‑time stream of agent status updates for the given project. |

> **Example** (JavaScript)  
> ```js
> const socket = new WebSocket('ws://localhost:8001/ws/1234');
> socket.onmessage = (e) => console.log(JSON.parse(e.data));
> ```

---

### Error Handling

All error responses follow the same JSON structure:

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE"
}
```

Status codes are standard HTTP codes (e.g., `400 Bad Request`, `404 Not Found`,
`500 Internal Server Error`).

---

### Rate Limiting & Retries

The backend automatically retries transient failures (network hiccups, LLM
timeouts) with exponential back‑off.  Clients should be prepared to handle
`429 Too Many Requests` and `503 Service Unavailable` responses.

---

### Security

- All endpoints are protected by API keys set in the environment (`GROQ_API_KEY`,
  `LANGCHAIN_API_KEY`, etc.).  
- The `/health` endpoint is intentionally public to allow health monitoring
  without authentication.

---

### Versioning

The API is currently in **v1**.  Future releases will be backward compatible
where possible.  Clients should query the `/health` endpoint to confirm
compatibility before upgrading.

---

## Contact & Support

For questions or issues, please open an issue on the GitHub repository or
contact the maintainers via the project's Slack channel.

---

*Generated on 2026‑08‑16*
```