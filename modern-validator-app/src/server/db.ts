// server/src/db.ts
import { Kysely, SqliteDialect } from 'kysely';
import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';
import type { Database as DB } from './types.db'; // <-- CORRECTED PATH

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Path to DB is now three levels up from server/src/
const dbPath = path.join(__dirname, '..', 'database.sqlite');

const dialect = new SqliteDialect({
  database: new Database(dbPath),
});

export const db = new Kysely<DB>({
  dialect,
});

export async function setupDatabase() {
  await db.schema
    .createTable('documents')
    .ifNotExists()
    .addColumn('id', 'integer', col => col.primaryKey().autoIncrement())
    .addColumn('filename', 'text', col => col.notNull().unique())
    .addColumn('imageSource', 'text', col => col.notNull())
    .addColumn('status', 'text', col => col.notNull().defaultTo('source'))
    .addColumn('sourceData', 'text', col => col.notNull())
    .addColumn('currentData', 'text', col => col.notNull())
    .execute();

  console.log('Database table "documents" is ready.');
}