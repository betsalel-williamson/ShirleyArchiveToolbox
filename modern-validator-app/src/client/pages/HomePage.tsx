import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";

interface FileStatus {
  filename: string;
  status: "validated" | "in_progress" | "source";
}

const statusStyles = {
  validated: "text-green-600 font-semibold",
  in_progress: "text-blue-600",
  source: "text-gray-500",
};

const statusText = {
  validated: "Validated ✓",
  in_progress: "In Progress...",
  source: "",
};


const HomePage: React.FC = () => {
  const [files, setFiles] = useState<FileStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        setLoading(true);
        const response = await fetch("/api/files");
        if (!response.ok) {
          throw new Error("Failed to fetch files");
        }
        const data: FileStatus[] = await response.json();
        setFiles(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An unknown error occurred");
      } finally {
        setLoading(false);
      }
    };
    fetchFiles();
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl bg-white rounded-lg shadow-xl p-8">
        <h1 className="text-4xl font-bold text-gray-800 mb-2">
          Transcription Validation
        </h1>
        <p className="text-gray-600 mb-8">
          Select a file to validate. Status will be shown.
        </p>
        {loading && <p>Loading files...</p>}
        {error && <p className="text-red-500">{error}</p>}
        {!loading && !error && (
          <ul className="divide-y divide-gray-200">
            {files.length > 0 ? (
              files.map((file) => (
                <li key={file.filename} className="py-4 flex justify-between items-center">
                  <Link
                    to={`/validate/${file.filename}`}
                    className="text-lg text-blue-700 hover:text-blue-900 hover:underline font-medium"
                  >
                    {file.filename}
                  </Link>
                  <span className={`text-sm ${statusStyles[file.status]}`}>
                    {statusText[file.status]}
                  </span>
                </li>
              ))
            ) : (
              <li className="py-4 text-gray-500">
                No JSON files found in any data directory.
              </li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
};

export default HomePage;
