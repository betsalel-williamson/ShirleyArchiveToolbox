import { Router, Request, Response } from "express";
import fs from 'fs/promises';
import path from 'path';
import { SOURCE_DATA_DIR } from '../utils.js';

const router: Router = Router();

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
