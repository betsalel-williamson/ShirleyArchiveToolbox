import React, { Suspense } from 'react';
import { Link } from 'react-router-dom';
import { fetchData } from '../data-wrapper';
import { getDocumentList } from '../data';

export interface DocumentInfo {
  id: number;
  filename: string;
  status: 'source' | 'in_progress' | 'validated';
}

function DocumentList() {
  // This will either return data or throw a promise, triggering the Suspense fallback.
  const files = fetchData('documents', getDocumentList).read();

  return (
    <ul>
      {files.length > 0 ? (
        files.map((file: DocumentInfo) => (
          <li key={file.id}>
            <Link to={`/validate/${file.id}`}>{file.filename}</Link>
            {file.status === 'validated' && <span className="validated-check">Validated ✓</span>}
            {file.status === 'in_progress' && <span className="status-progress">In Progress...</span>}
          </li>
        ))
      ) : (
        <li>No JSON files found in the database. Run `pnpm run seed` to populate it.</li>
      )}
    </ul>
  );
}

export default function IndexPage() {
  return (
    <div className="container">
      <h1>Transcription Validation</h1>
      <p>Select a file to validate. Status will be shown.</p>
      <Suspense fallback={<h2>🌀 Loading documents...</h2>}>
        <DocumentList />
      </Suspense>
    </div>
  );
}
