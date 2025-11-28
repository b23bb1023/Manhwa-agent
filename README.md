# **Manga Content Agent (MangaAgent)**

A robust, localized, and resilient automation solution designed for continuous monitoring and visualization of web comic updates from Cloudflare-protected sources (Asura Scans).

This project employs a decoupled, containerized architecture to ensure stability, maintain state persistence, and provide a low-latency user experience via a custom desktop GUI.

## **Purpose and Technical Scope**

The core objective is to bypass common anti-bot mechanisms (e.g., JavaScript challenges, TLS fingerprinting) to reliably extract dynamic content, format the data for user consumption, and present it in an always-on, high-availability desktop dashboard.

## **Technical Architecture and Components**

The system is deployed using Docker Compose for simple orchestration of three primary services:

### **1\. Scraper Microservice (Python / FastAPI / Playwright)**

* **Role:** Performs browser emulation to execute JavaScript and resolve anti-bot protection layers (Cloudflare).  
* **Technology:** Python, FastAPI (for containerized API endpoint), and Playwright (headless Chromium) for automation and page rendering.  
* **Functionality:** Exposes a simple GET /scrape?url= endpoint for external consumption.

### **2\. Automation Engine (n8n / Node.js)**

* **Role:** The centralized state manager and orchestration layer. It manages scheduling, data flow integrity, error handling, and file persistence.  
* **Technology:** n8n (self-hosted), utilizing Schedule and Webhook nodes for triggering and **Code Nodes** for data validation and aggregation.  
* **Functionality:**  
  * **Persistent State:** Manages the reading\_list.json database.  
  * **Flow Control:** Implements a single-item loop with deliberate Wait nodes and Continue on Fail logic to achieve safe, throttled scraping.  
  * **API Interaction:** Consumes the Scraper Microservice API via HTTP requests.

### **3\. Frontend Widget (Python / Flet GUI)**

* **Role:** The client-side visualization layer, designed for quick access and interaction.  
* **Technology:** Python (Flet framework) for platform-independent desktop UI generation.  
* **Functionality:**  
  * **Passive Read:** Reads the local reading\_list.json for instant UI rendering.  
  * **Active Trigger:** Sends a non-blocking GET request (Webhook) to the n8n service upon application startup to initiate a fresh scrape cycle.  
  * **UI Logic:** Sorts items by update availability (new chapters prioritized) and safely loads image data using Base64 encoding to circumvent cross-origin and hotlink restrictions.

## **Key Features and Flexibility**

| Feature | Technical Benefit |
| :---- | :---- |
| **Containerization (Docker)** | Guarantees environmental consistency (e.g., specific Playwright/Chromium versions) and simplifies deployment across host platforms (macOS, Linux). |
| **Persistent JSON State** | Decouples the backend logic from the frontend presentation. Allows for fast startup and easy backup/migration of reading data. |
| **Webhook Integration** | Enables asynchronous, non-blocking manual execution of the scheduled task directly from the client application. |
| **Throttled Looping** | Prevents IP rate-limiting by utilizing the Wait node within the main processing loop. |
| **Base64 Image Pipeline** | Resolves external hotlink protection issues, ensuring robust display of cover art within the local GUI client. |

## **Prerequisites**

* **Docker Desktop** (Required for containerized deployment of the backend services).  
* **Python 3.x** (Required for the desktop widget and Flet library).  
* **Brave Browser** (Target browser for chapter links).

## **Installation**

### **1\. Folder Structure**

Ensure your project directory is set up as follows:

MangaAgent/  
├── docker-compose.yml  
├── data/  
│   └── reading\_list.json  (Your database)  
├── scraper/  
│   ├── Dockerfile  
│   ├── requirements.txt  
│   └── main.py  
└── widget.py              (Your Desktop App)

### **2\. Start the Backend**

Open your terminal in the project folder and execute the Docker Compose command to build and launch the services in detached mode:

cd path/to/MangaAgent  
docker-compose up \-d \--build

*Wait for the containers manga\_n8n and manga\_scraper to report "Healthy" or "Running".*

### **3\. Configure n8n (The Automation Engine)**

1. Access the n8n interface at http://localhost:5678.  
2. Import the workflow JSON configuration.  
3. **Webhook Configuration:**  
   * Verify the Webhook Node HTTP Method is **GET** and the path is /refresh.  
   * Copy the **Production URL** (e.g., http://localhost:5678/webhook/refresh).  
4. **Activate the Workflow:** Set the top-right toggle to **Active** (Green).

### **4\. Setup the Widget Client**

Install the required UI library:

pip3 install flet

Edit widget.py and ensure the WEBHOOK\_URL variable matches the n8n Production URL copied in Step 3\.

## **Usage**

### **Running the Dashboard**

The application can be executed via the configured Python interpreter:

python3 widget.py

For platform-native launch without relying on the command line, use the compiled **MangaWidget.app** (macOS).

### **Adding New Manga**

1. Open data/reading\_list.json.  
2. Add a new JSON object entry, ensuring the id, title, and url fields are accurately populated. Set latest\_available to 0 to force an initial scrape.  
3. Relaunch the desktop application. The system will auto-trigger a full scrape cycle, and the new data will populate after processing completes.

## **Troubleshooting**

* **Data Integrity:** If the database becomes corrupted, restore the array structure in data/reading\_list.json.  
* **Connection Error:** Verify that the n8n workflow is **Active** and that the WEBHOOK\_URL in widget.py is identical to the Production URL.  
* **Scraper Failure:** If the Scraper API node fails, re-execute the docker-compose up \-d \--build command to download updated Playwright binaries.

## **License**

This project is intended for personal, non-commercial use.