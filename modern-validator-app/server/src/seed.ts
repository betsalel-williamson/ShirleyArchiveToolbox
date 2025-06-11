// server/src/seed.ts
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { connectDB, sequelize } from './database.js';
import Document from './models/Document.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SOURCE_DATA_DIR = path.join(__dirname, '..', '..', 'data', 'source_json');

async function seedDatabase() {
  console.log('Connecting to database...');
  await connectDB();

  console.log('Clearing existing documents...');
  await Document.destroy({ where: {}, truncate: true });

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

    // Add unique IDs to the data
    let wordCounter = 0;
    data.lines.forEach((line: any, line_idx: number) => {
        line.words.forEach((word: any, word_idx: number) => {
            word.id = `${line_idx}_${word_idx}`;
            word.display_id = ++wordCounter;
        });
    });

    await Document.create({
      filename,
      imageSource: data.image_source,
      status: 'source',
      sourceData: data,
      currentData: data,
    });
    console.log(`  - Seeded ${filename} into the database.`);
  }

  console.log('Database seeding complete!');
  await sequelize.close();
}

seedDatabase().catch(error => {
  console.error('Seeding failed:', error);
  process.exit(1);
});
