import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export interface DocumentInfo {
  id: number;
  filename: string;
  status: 'source' | 'in_progress' | 'validated';
}

export default function IndexPage() {
  const [files, setFiles] = useState<DocumentInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    fetch('/api/documents')
      .then(res => {
        if (!res.ok) {
          throw new Error('Failed to fetch documents from API.');
        }
        return res.json();
      })
      .then(data => {
        if (isMounted) setFiles(data);
      })
      .catch(err => {
        if (isMounted) setError((err as Error).message);
      });
    return () => { isMounted = false; };
  }, []);

  if (error) return <div className="container"><h1>Error</h1><p>{error}</p></div>;
  if (!files) return <div className="container"><h1>🌀 Loading Documents...</h1></div>;

  return (
    <div className="container">
      <h1>Transcription Validation</h1>
      <p>Select a file to validate. Status will be shown.</p>
      <ul>
        {files.length > 0 ? (
          files.map(file => (
            <li key={file.id}>
              <Link to={`/validate/${file.id}`}>{file.filename}</Link>
              {file.status === 'validated' && <span className="validated-check"> ✓ Validated</span>}
              {file.status === 'in_progress' && <span className="status-progress"> ⏳ In Progress</span>}
            </li>
          ))
        ) : (
          <li>No documents found. Run `pnpm run seed` to populate the database.</li>
        )}
      </ul>
    </div>
  );
}