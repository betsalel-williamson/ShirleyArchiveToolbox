// server/src/data.ts
import { db } from './db';

// --- Data fetching for the Document List ---
export async function getDocumentList() {
  try {
    const documents = await db
      .selectFrom('documents')
      .select(['id', 'filename', 'status'])
      .orderBy('filename', 'asc')
      .execute();
    return documents;
  } catch (error) {
    console.error("Failed to fetch documents from DB:", error);
    throw new Error('Failed to fetch documents');
  }
}

// Helper to parse JSON columns from the DB
const parseDoc = (doc: any) => {
  if (!doc) return null;
  return {
    ...doc,
    sourceData: JSON.parse(doc.sourceData as string),
    currentData: JSON.parse(doc.currentData as string),
  };
};

// --- Data fetching for a single Document by ID ---
export async function getDocumentById(id: number | string) {
  try {
    const document = await db
      .selectFrom('documents')
      .selectAll()
      .where('id', '=', Number(id))
      .executeTakeFirst();

    if (!document) {
      return { error: 'Document not found', status: 404 };
    }
    return parseDoc(document);
  } catch (error) {
    console.error(`Failed to fetch document ${id} from DB:`, error);
    throw new Error(`Failed to fetch document ${id}`);
  }
}
