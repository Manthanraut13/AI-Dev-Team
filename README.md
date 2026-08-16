```
@@
 | POST | `/api/projects` | Start project generation |
 | GET | `/api/projects/{id}` | View project state |
 | POST | `/api/projects/{id}/approve` | Approve/reject at checkpoint |
 | POST | `/api/projects/{id}/research` | Ad-hoc web research |
 | POST | `/api/projects/{id}/github` | Commit + create PR |
 | WS | `/ws/{id}` | Real-time agent status |
+ | GET | `/health` | Health check endpoint |
```