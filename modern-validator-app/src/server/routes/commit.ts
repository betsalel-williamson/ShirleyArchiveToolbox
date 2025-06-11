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
