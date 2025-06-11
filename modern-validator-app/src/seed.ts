// server/src/seed.ts
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { db, setupDatabase } from './db.js'; // <-- CORRECTED PATH

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
// Path to data is now three levels up from server/src/
const SOURCE_DATA_DIR = path.join(__dirname, '..', 'data', 'source_json');

async function seedDatabase() {
  // ... (rest of the seed function is the same)
  console.log('Setting up database...');
  await setupDatabase();

  console.log('Clearing existing documents...');
  await db.deleteFrom('documents').execute();

  console.log(`Reading from ${SOURCE_DATA_DIR}...`);
  const files = await fs.readdir(SOURCE_DATA_DIR);
  const jsonFiles = files.filter(f => f.endsWith('.json'));

  if (jsonFiles.length === 0) {
    console.log('No JSON files found in source directory. Nothing to seed.');
    return;
  }

  for (const filename of jsonFiles) {
    console.log(`Processing ${filename}...`);
    const filePath = path.join(SOURCE_DATA_DIR, filename);
    const fileContent = await fs.readFile(filePath, 'utf-8');
    const data = JSON.parse(fileContent);

    let wordCounter = 0;
    data.lines.forEach((line: any, line_idx: number) => {
        line.words.forEach((word: any, word_idx: number) => {
            word.id = `${line_idx}_${word_idx}`;
            word.display_id = ++wordCounter;
        });
    });

    await db.insertInto('documents').values({
      filename,
      imageSource: data.image_source,
      status: 'source',
      sourceData: JSON.stringify(data),
      currentData: JSON.stringify(data),
    }).execute();

    console.log(`  - Seeded ${filename} into the database.`);
  }

  console.log('Database seeding complete!');
}

seedDatabase().catch(error => {
  console.error('Seeding failed:', error);
  process.exit(1);
});