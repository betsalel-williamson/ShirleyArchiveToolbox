// server/src/db/types.ts
import { Generated, ColumnType } from 'kysely';

// Kysely uses interfaces to model table schemas.

export interface DocumentsTable {
  id: Generated<number>; // `Generated` means the DB creates this value
  filename: string;
  imageSource: string;
  status: 'source' | 'in_progress' | 'validated';

  // JSON columns are typed as strings but we can use a special
  // ColumnType to tell Kysely how to serialize/deserialize them.
  sourceData: ColumnType<string, string, string>;
  currentData: ColumnType<string, string, string>;
}

// This interface is the master schema for the database.
export interface Database {
  documents: DocumentsTable;
}
