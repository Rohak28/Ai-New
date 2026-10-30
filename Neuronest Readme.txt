# NeuroNest Sandbox Template

Welcome to the **NeuroNest Sandbox Template**. This repository serves as the foundational boilerplate to set up, develop, and run your `DemoApp` application for the NeuroNest ecosystem.

---

##  Project Structure

| Directory/File | Description |
| --- | --- |
| `backend/` | Contains the FastAPI application, data extraction scripts, and environment settings. |
| `frontend/` | Contains the React UI and frontend assets. |
| `shared_config/` | Contains the centralized files. |
| `app_config.json` | Contains routing, port, and dashboard details for NeuroNest Platform integration. |

---

##  Mandatory Pre-requisites

Before starting the backend server, you must configure your environment settings.

1. Navigate to the backend directory:
   ```bash
   cd backend/demoapp
   ```
2. Configure your environment credentials and model settings:
   - **Environment Variables (`.env.app`):** Open this file and fill in your sensitive credentials provided by the NeuroNest Team.
     - **LLM Config:** Provide your `OPENAI_API_KEY`.
     - **Database Config:** Provide the MongoDB credentials(MONGO_USERNAME,MONGO_PASSWORD,DB_NAME,MONGO_COLLECTION_NAME).
     - **Milvus Config (Optional):** If using the Centralized Milvus DB, provide details(MILVUS_BASE,MILVUS_PORT,MILVUS_USER,     MILVUS_PASSWORD,VECTOR_DB_NAME).
   - **Model Settings (`settings.py`):** Open this file to customize the default model strings for your application:
     - `model_name_llm`: Default text model (e.g., `neuroverse-gpt-oss-120b`).
     - `vision_model_name`: Default vision model (e.g., `neuroverse-Qwen2.5-VL-72B-Instruct`).
     - `model_name_emb`: Default embedding model.

3. you will be provided with the port numbers to run your fronend and backend service.
	
4. Use these port numbers to start frontend and  backend service (details are porvided in next section)

---

##  Steps to Run (Development)

To run the full stack application, you will need to open **two separate terminal windows** inside your Code-Server.

### Scenario A: Standard Execution (Default)
*Use this if you do not need to inject new data into the Centralized Milvus DB.*

**Terminal 1 (Frontend):**
```bash
  1. cd frontend/
  2. PUBLIC_URL=/code-{your_name}/proxy/6001/ npm run build
        eg- PUBLIC_URL=/code-mangesh/proxy/6001/ npm run build 
  3. npx serve -s build -l 6001
```

**Terminal 2 (Backend):**
```bash
  1. cd backend/demoapp
  2. pip install -r requirements.txt
  3. uvicorn app:app --host 0.0.0.0 --port 8001
```

---

### Scenario B: With Vector Data Injection
*Use this if you need to extract data from documents and inject embeddings into the Milvus DB.*

Imp: Before running any command, open the backend file (DemoApp_service.py)
and uncomment the line nu 189 [# SYSTEM_PROMPT = await _get_prompt(text)] to enable RAG flow on your own data.
**Terminal 1 (Frontend):**
```bash
  1. cd frontend/
  2. PUBLIC_URL=/code-{your_name}/proxy/6001/ npm run build
     eg- PUBLIC_URL=/code-mangesh/proxy/6001/ npm run build 
  3. npx serve -s build -l 6001
```

**Terminal 2 (Backend & Data Extraction):**
```bash
  1. cd backend/demoapp
  2. pip install -r requirements.txt
  3. upload your pdf or excel file into (backend/demoapp/input_documents/) and run below 2 commands to extract text from pdf/excel and then injest that text into Milvus VDB
					   
		a. python PDF_extraction.py   ----> for PDF data extraction
			 python excel_extraction.py   ----> for excel data extraction
		b. python vector_database_creation.py
  4. uvicorn app:app --host 0.0.0.0 --port 8001
```


> > [!IMPORTANT]
> ## Customizing Your Chatbot

### Default Chatbot Behavior
**Location:** `backend/demoapp`

- **Non-RAG Flow:** To modify the default system prompt, edit **line 33** in `DemoApp_service.py`.
- **RAG Flow:** To change the chatbot's behavior in the RAG pipeline, update the system prompt in `prompts/prompts.yaml` (around **line 8**).

### Adding Your Own Knowledge Base
Place all your knowledge files (PDF, Excel, etc.) in the directory mentioned in **Scenario B**.

**Note:**
- Newly processed chunks will be appended to the existing **Milvus** collection.
- If required, you can:
  - Create a new Milvus collection by updating the `.env.app` configuration.
  - Delete the existing collection data by uncommenting the appropriate code block in `vector_database_creation.py`.

---

> [!IMPORTANT]
> ## Preparing Your Project for Git Integration

### Integration Readiness
This template includes a generic `app_config.json` file for QA/dev and Production integration.

When your application is ready for QA/dev deployment, the Neuronest team will provide the required configuration values to update this file.

### Project Repository
Before pushing your project to the development environment, contact the **Neuronest team** to:

- Create your project's Git repository.
- Grant repository access.
- Provide your **SonarQube Project Key**.

### SonarQube Configuration

Running a SonarQube scan is **mandatory** before integrating your project.

The required pipeline is already included in the root directory:

- `gitlab-ci.yml`
- `sonar-project.properties`

#### 1. Update `sonar-project.properties`

Replace the placeholder with your project-specific SonarQube key.

```properties
sonar.projectKey=YOUR_APP_SPECIFIC_SONAR_KEY_HERE
```

#### 2. Update `gitlab-ci.yml`

In **Stage 2 – Security Scanning**, replace:

```bash
/sonar-scanner/bin/sonar-scanner \
  -Dsonar.host.url="${SONAR_HOST_URL}" \
  -Dsonar.projectKey="${SONAR_PROJECT_KEY}" \
  -Dsonar.sources="."

curl -u "${SONAR_TOKEN}:" \
"${SONAR_HOST_URL}/api/issues/gitlab_sast_export?projectKey=${SONAR_PROJECT_KEY}&branch=${CI_COMMIT_BRANCH}&pullRequest=${CI_MERGE_REQUEST_IID}" \
-o gl-sast-sonar-report.json
```

with:

```bash
/sonar-scanner/bin/sonar-scanner \
  -Dsonar.host.url="${SONAR_HOST_URL}" \
  -Dsonar.sources="."

curl -u "${SONAR_TOKEN}:" \
"${SONAR_HOST_URL}/api/issues/gitlab_sast_export?projectKey=<YOUR_SONAR_PROJECT_KEY>&branch=${CI_COMMIT_BRANCH}&pullRequest=${CI_MERGE_REQUEST_IID}" \
-o gl-sast-sonar-report.json
```

Replace `<YOUR_SONAR_PROJECT_KEY>` with the SonarQube Project Key provided by the Neuronest team.

#### 3. Enable Dynamic Integration Stage

Uncomment **Stage 3 – Dynamic Integration** in `gitlab-ci.yml` before using the pipeline for deployment.