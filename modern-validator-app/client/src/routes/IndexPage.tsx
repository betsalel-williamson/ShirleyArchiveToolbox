import { useLoaderData, Link } from 'react-router-dom';

export interface DocumentInfo {
  id: number;
  filename: string;
  status: 'source' | 'in_progress' | 'validated';
}

export async function loader() {
  const res = await fetch('http://localhost:5173/api/documents');
  if (!res.ok) throw new Error('Failed to fetch documents');
  const documents: DocumentInfo[] = await res.json();
  return documents;
}

export default function IndexPage() {
  const files = useLoaderData() as DocumentInfo[];

  return (
    <div className="container">
      <h1>Transcription Validation</h1>
      <p>Select a file to validate. Status will be shown.</p>
      <ul>
        {files.length > 0 ? (
          files.map(file => (
            <li key={file.id}>
              <Link to={`/validate/${file.id}`}>{file.filename}</Link>
              {file.status === 'validated' && <span className="validated-check">Validated ✓</span>}
              {file.status === 'in_progress' && <span className="status-progress">In Progress...</span>}
            </li>
          ))
        ) : (
          <li>No JSON files found in the database. Run `npm run seed` to populate it.</li>
        )}
      </ul>
    </div>
  );
}
