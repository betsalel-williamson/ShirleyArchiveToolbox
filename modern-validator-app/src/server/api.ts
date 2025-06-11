// server/src/api.ts
import express, { Request, Response } from 'express';
import { db } from '../db';
import { applyTransformationsToData } from '../utils.js';
import { sql } from 'kysely';
import { getDocumentList, getDocumentById } from '../data';

const router = express.Router();

// GET /api/documents - List all documents
router.get('/documents', async (req: Request, res: Response) => {
  try {
    const documents = await getDocumentList();
    res.json(documents);
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

// GET /api/documents/:id - Get a single document's data for validation
router.get('/documents/:id', async (req: Request, res: Response) => {
  try {
    const document = await getDocumentById(req.params.id);
    if ((document as any)?.status === 404) {
        return res.status(404).json(document);
    }
    res.json(document);
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});


// POST /api/documents/:id/autosave
router.post('/documents/:id/autosave', async (req: Request, res: Response) => {
    try {
        const transformedData = applyTransformationsToData(req.body);

        await db.updateTable('documents')
            .set({
                currentData: JSON.stringify(transformedData),
                status: sql`CASE WHEN status = 'source' THEN 'in_progress' ELSE status END`
            })
            .where('id', '=', Number(req.params.id))
            .execute();

        res.json({ status: 'ok', message: 'Draft saved.' });
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Failed to save draft' });
    }
});

// POST /api/documents/:id/commit
router.post('/documents/:id/commit', async (req: Request, res: Response) => {
    try {
        const transformedData = applyTransformationsToData(req.body);
        (transformedData as any).validated = true;

        await db.updateTable('documents')
            .set({
                currentData: JSON.stringify(transformedData),
                status: 'validated'
            })
            .where('id', '=', Number(req.params.id))
            .execute();

        const nextDocument = await db.selectFrom('documents')
            .select('id')
            .where('status', '!=', 'validated')
            .orderBy('filename', 'asc')
            .limit(1)
            .executeTakeFirst();

        res.json({ status: 'ok', message: 'Committed successfully.', nextDocumentId: nextDocument?.id || null });
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Failed to commit changes' });
    }
});


// POST /api/documents/:id/revert
router.post('/documents/:id/revert', async (req: Request, res: Response) => {
    try {
        const doc = await db.selectFrom('documents')
            .select('sourceData')
            .where('id', '=', Number(req.params.id))
            .executeTakeFirstOrThrow();

        await db.updateTable('documents')
            .set({
                currentData: doc.sourceData,
                status: sql`CASE WHEN status = 'validated' THEN 'in_progress' ELSE status END`
            })
            .where('id', '=', Number(req.params.id))
            .execute();

        const updatedDoc = await db.selectFrom('documents').selectAll().where('id', '=', Number(req.params.id)).executeTakeFirstOrThrow();

        res.json({ status: 'ok', message: 'Reverted to source.', data: JSON.parse(updatedDoc.currentData as string) });
    } catch (error) {
        res.status(500).json({ error: 'Failed to revert document' });
    }
});

export default router;
