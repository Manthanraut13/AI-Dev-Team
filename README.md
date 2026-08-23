```diff
@@
 6. **Start the API server**
    ```bash
    uvicorn plugin.server:app --host $APP_HOST --port $APP_PORT --reload
    ```
 
    7. **Explore the API**
    Open your browser at `http://localhost:8000/docs` to view the automatically generated OpenAPI/Swagger UI.
 
    For a detailed endpoint reference, see **[docs/API.md](docs/API.md)**.
@@
 
 ## Running Tests
 ```
 pytest
 ```
 
 ## License
 This project is licensed under the MIT License.
+
+## API Documentation
+
+For a complete reference of all available endpoints, request payloads, response schemas, and example
+interactions, see the dedicated API documentation file:
+
+[docs/API.md](docs/API.md)
```