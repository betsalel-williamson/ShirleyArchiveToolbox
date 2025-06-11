import { Router, Request, Response } from "express";
import fs from 'fs/promises';
import path from 'path';
import { loadData, applyTransformationsToData, IN_PROGRESS_DATA_DIR } from '../utils.js';

const router: Router = Router();

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
