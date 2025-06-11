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
