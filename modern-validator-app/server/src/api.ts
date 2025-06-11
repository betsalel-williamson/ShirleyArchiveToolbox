// server/src/api.ts
import express, { Request, Response } from 'express';
import Document from './models/Document.js';
import { applyTransformationsToData } from './utils.js';
import { Op } from './database.js';

const router = express.Router();

// GET /api/documents - List all documents
router.get('/documents', async (req: Request, res: Response) => {
  try {
    const documents = await Document.findAll({
      attributes: ['id', 'filename', 'status'],
      order: [['filename', 'ASC']],
    });
    res.json(documents);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch documents' });
  }
});

// GET /api/documents/:id - Get a single document's data for validation
router.get('/documents/:id', async (req: Request, res: Response) => {
  try {
    const document = await Document.findByPk(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found', status: 404 });
    }
    res.json(document);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch document' });
  }
});

// GET /api/documents/:id/source - Get original source data
router.get('/documents/:id/source', async (req: Request, res: Response) => {
    try {
        const document = await Document.findByPk(req.params.id, {
            attributes: ['sourceData'],
        });
        if (!document) {
            return res.status(404).json({ error: 'Document not found' });
        }
        res.json(document.sourceData);
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch source data' });
    }
});

// POST /api/documents/:id/autosave
router.post('/documents/:id/autosave', async (req: Request, res: Response) => {
  try {
    const document = await Document.findByPk(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }
    const transformedData = applyTransformationsToData(req.body);

    document.currentData = transformedData;
    if (document.status === 'source') {
      document.status = 'in_progress';
    }
    await document.save();

    res.json({ status: 'ok', message: 'Draft saved.' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Failed to save draft' });
  }
});

// POST /api/documents/:id/commit
router.post('/documents/:id/commit', async (req: Request, res: Response) => {
  try {
    const document = await Document.findByPk(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }
    const transformedData = applyTransformationsToData(req.body);
    transformedData.validated = true;

    document.currentData = transformedData;
    document.status = 'validated';
    await document.save();

    const nextDocument = await Document.findOne({
        where: { status: { [Op.ne]: 'validated' } },
        order: [['filename', 'ASC']],
        attributes: ['id'],
    });

    res.json({ status: 'ok', message: 'Committed successfully.', nextDocumentId: nextDocument?.id || null });

  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Failed to commit changes' });
  }
});

// POST /api/documents/:id/revert
router.post('/documents/:id/revert', async (req: Request, res: Response) => {
    try {
        const document = await Document.findByPk(req.params.id);
        if (!document) {
            return res.status(404).json({ error: 'Document not found' });
        }
        document.currentData = document.sourceData;
        if (document.status === 'validated') {
          document.status = 'in_progress';
        }
        await document.save();
        res.json({ status: 'ok', message: 'Reverted to source.', data: document.currentData });
    } catch (error) {
        res.status(500).json({ error: 'Failed to revert document' });
    }
});

export default router;
