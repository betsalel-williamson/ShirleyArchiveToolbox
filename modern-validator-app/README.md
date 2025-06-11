# Modern Full-Stack Validator App

This is a modern full-stack application built with Vite, React, SSR, Express, and Sequelize (SQLite). It's a conversion from an original Python Flask application.

## Project Structure

- **`/`**: Root of the project, contains the main server entrypoint (`server.ts`) and configs.
- **`/client`**: The Vite + React frontend application.
- **`/server`**: The Express.js backend API and database logic.
- **`/data`**: Contains the initial source JSON files and images.

## How to Run

1.  **Install All Dependencies:**
    - `npm install` (in the root directory)
    - `cd client && npm install && cd ..`
    - `cd server && npm install && cd ..`

2.  **Seed the Database:**
    Run this command from the root directory to populate the SQLite database from the files in `/data/source_json`.
    \`\`\`bash
    npm run seed
    \`\`\`

3.  **Start the Development Server:**
    Run this command from the root directory. It will start the backend and the Vite server with SSR.
    \`\`\`bash
    npm run dev
    \`\`\`

4.  **Access the App:**
    Open your browser and navigate to `http://localhost:5173`.
