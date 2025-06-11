#!/bin/bash

# This script refactors the monolithic server API into a modular structure,
# promoting better organization and maintainability. Each primary API endpoint
# is moved into its own file within a new 'src/server/routes' directory.

# ==============================================================================
# Step 1: Create the directory for the new route modules.
# ==============================================================================
echo "Creating directory for API routes..."
mkdir -p src/server/routes
echo "✅ Directory 'src/server/routes' created."

# ==============================================================================
# Step 2: Create the route module for handling file listings and data loading.
# Handles GET /api/files and GET /api/files/:json_filename
# ==============================================================================
echo "Creating 'src/server/routes/files.ts'..."
cat > src/server/routes/files.ts << 'EOF'
import { Router, Request, Response } from "express";
import { getJsonFiles, getFileStatus, loadData } from '../utils.js';

const router = Router();

// Route to get the list of all files and their statuses
router.get("/", async (req: Request, res: Response) => {
    try {
        const files = await getJsonFiles();
        const fileStatuses = await Promise.all(
            files.map(async (f) => ({
                filename: f,
                status: await getFileStatus(f),
            }))
        );
        res.json(fileStatuses);
    } catch (error) {
        console.error("Error getting files:", error);
        res.status(500).json({ error: "Failed to retrieve file list." });
    }
});

// Route to get data for a specific file
router.get("/:json_filename", async (req: Request, res: Response) => {
    try {
        const data = await loadData(req.params.json_filename);
        if (!data) {
            return res.status(404).json({ error: "File not found." });
        }
        res.json(data);
    } catch (error)        {
        console.error(`Error loading data for ${req.params.json_filename}:`, error);
        res.status(500).json({ error: "Failed to load file data." });
    }
});

export default router;
EOF
echo "✅ Route module for files created."

# ==============================================================================
# Step 3: Create the route module for autosaving progress.
# Handles PATCH /api/autosave/:json_filename
# ==============================================================================
echo "Creating 'src/server/routes/autosave.ts'..."
cat > src/server/routes/autosave.ts << 'EOF'
import { Router, Request, Response } from "express";
import fs from 'fs/promises';
import path from 'path';
import { loadData, applyTransformationsToData, IN_PROGRESS_DATA_DIR } from '../utils.js';

const router = Router();

// Route to autosave progress
router.patch("/:json_filename", async (req: Request, res: Response) => {
    const { json_filename } = req.params;
    try {
        const baseData = await loadData(json_filename);
        if (!baseData) {
            return res.status(404).json({ error: "Cannot autosave, base file not found."});
        }

        const transformedData = applyTransformationsToData(baseData, req.body);
        const savePath = path.join(IN_PROGRESS_DATA_DIR, json_filename);
        await fs.writeFile(savePath, JSON.stringify(transformedData, null, 2));
        res.json({ status: "ok", message: "Draft saved." });
    } catch (error) {
        console.error(`Error autosaving ${json_filename}:`, error);
        res.status(500).json({ error: "Failed to save draft." });
    }
});

export default router;
EOF
echo "✅ Route module for autosave created."

# ==============================================================================
# Step 4: Create the route module for committing final changes.
# Handles PATCH /api/commit/:json_filename
# ==============================================================================
echo "Creating 'src/server/routes/commit.ts'..."
cat > src/server/routes/commit.ts << 'EOF'
import { Router, Request, Response } from "express";
import fs from 'fs/promises';
import path from 'path';
import {
    loadData,
    applyTransformationsToData,
    VALIDATED_DATA_DIR,
    IN_PROGRESS_DATA_DIR,
    getJsonFiles,
    getFileStatus
} from '../utils.js';

const router = Router();

// Route to commit final changes
router.patch("/:json_filename", async (req: Request, res: Response) => {
    const { json_filename } = req.params;
    try {
        const baseData = await loadData(json_filename);
        if (!baseData) {
            return res.status(404).json({ error: "Cannot commit, base file not found." });
        }

        const transformedData = applyTransformationsToData(baseData, req.body);
        transformedData.validated = true;

        const validatedPath = path.join(VALIDATED_DATA_DIR, json_filename);
        await fs.writeFile(validatedPath, JSON.stringify(transformedData, null, 2));

        const inProgressPath = path.join(IN_PROGRESS_DATA_DIR, json_filename);
        try {
            await fs.unlink(inProgressPath);
        } catch (e: any) {
            if (e.code !== 'ENOENT') console.error(`Could not remove in-progress file: ${e.message}`);
        }

        const allFiles = await getJsonFiles();
        const currentIndex = allFiles.indexOf(json_filename);

        let nextFile = null;
        if (currentIndex !== -1) {
            for (let i = currentIndex + 1; i < allFiles.length; i++) {
                const status = await getFileStatus(allFiles[i]);
                if (status !== 'validated') {
                    nextFile = allFiles[i];
                    break;
                }
            }
        }

        res.json({ status: "ok", message: "Committed successfully.", nextFile });

    } catch (error) {
        console.error(`Error committing ${json_filename}:`, error);
        res.status(500).json({ error: "Failed to commit changes." });
    }
});

export default router;
EOF
echo "✅ Route module for commit created."

# ==============================================================================
# Step 5: Create the route module for retrieving original source data.
# Handles GET /api/source-data/:json_filename
# ==============================================================================
echo "Creating 'src/server/routes/sourceData.ts'..."
cat > src/server/routes/sourceData.ts << 'EOF'
import { Router, Request, Response } from "express";
import fs from 'fs/promises';
import path from 'path';
import { SOURCE_DATA_DIR } from '../utils.js';

const router = Router();

router.get("/:json_filename", async (req: Request, res: Response) => {
    const { json_filename } = req.params;
    try {
        const sourcePath = path.join(SOURCE_DATA_DIR, json_filename);
        const data = await fs.readFile(sourcePath, 'utf-8');
        res.json(JSON.parse(data));
    } catch (error) {
        res.status(404).json({ error: `Source file '${json_filename}' not found.` });
    }
});

export default router;
EOF
echo "✅ Route module for source-data created."

# ==============================================================================
# Step 6: Overwrite the main api.ts to act as a central router.
# This file now imports the modular routers and mounts them at their respective paths.
# ==============================================================================
echo "Refactoring 'src/server/api.ts' to be the main API router..."
cat > src/server/api.ts << 'EOF'
import { Router } from "express";
import filesRouter from './routes/files.js';
import autosaveRouter from './routes/autosave.js';
import commitRouter from './routes/commit.js';
import sourceDataRouter from './routes/sourceData.js';

const router = Router();

router.use('/files', filesRouter);
router.use('/autosave', autosaveRouter);
router.use('/commit', commitRouter);
router.use('/source-data', sourceDataRouter);

export default router;
EOF
echo "✅ Main API router has been updated."

# ==============================================================================
# Step 7: Clean up the old example route file.
# ==============================================================================
if [ -f "src/server/routes/api.ts" ]; then
    echo "Removing old example route file 'src/server/routes/api.ts'..."
    rm src/server/routes/api.ts
    echo "✅ Old file removed."
fi

echo "🚀 API refactoring complete!"