import { Router, Request, Response } from "express";
import fs from 'fs/promises';
import path from 'path';
import {
    getJsonFiles,
    getFileStatus,
    loadData,
    applyTransformationsToData,
    SOURCE_DATA_DIR,
    IN_PROGRESS_DATA_DIR,
    VALIDATED_DATA_DIR
} from './utils.js';

const router = Router();

// Route to get the list of all files and their statuses
router.get("/files", async (req: Request, res: Response) => {
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
router.get("/files/:json_filename", async (req: Request, res: Response) => {
    try {
        const data = await loadData(req.params.json_filename);
        if (!data) {
            return res.status(404).json({ error: "File not found." });
        }
        res.json(data);
    } catch (error) {
        console.error(`Error loading data for ${req.params.json_filename}:`, error);
        res.status(500).json({ error: "Failed to load file data." });
    }
});


// Route to autosave progress
router.patch("/autosave/:json_filename", async (req: Request, res: Response) => {
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

// Route to commit final changes
router.patch("/commit/:json_filename", async (req: Request, res: Response) => {
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


// Route to get original source data
router.get("/source-data/:json_filename", async (req: Request, res: Response) => {
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
