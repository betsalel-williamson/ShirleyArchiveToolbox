import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from 'url';
import { Request } from "express";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, '..', '..');

// Directory paths
export const SOURCE_DATA_DIR = path.join(ROOT_DIR, 'data_source');
export const IN_PROGRESS_DATA_DIR = path.join(ROOT_DIR, 'data_in_progress');
export const VALIDATED_DATA_DIR = path.join(ROOT_DIR, 'data_validated');


export const getJsonFiles = async (): Promise<string[]> => {
    // Reading directories can throw if they don't exist, so we handle that.
    const readDirSafe = async (dir: string) => {
        try {
            return await fs.readdir(dir);
        } catch (error: any) {
            if (error.code === 'ENOENT') return []; // Directory doesn't exist
            throw error; // Other errors
        }
    }
    const sourceFiles = await readDirSafe(SOURCE_DATA_DIR);
    const inProgressFiles = await readDirSafe(IN_PROGRESS_DATA_DIR);
    const validatedFiles = await readDirSafe(VALIDATED_DATA_DIR);

    const allFiles = new Set([
        ...sourceFiles,
        ...inProgressFiles,
        ...validatedFiles,
    ]);

    return Array.from(allFiles)
        .filter(f => f.endsWith(".json"))
        .sort();
};

export const getFileStatus = async (jsonFilename: string): Promise<'validated' | 'in_progress' | 'source'> => {
    const validatedPath = path.join(VALIDATED_DATA_DIR, jsonFilename);
    const inProgressPath = path.join(IN_PROGRESS_DATA_DIR, jsonFilename);

    try {
        await fs.access(validatedPath);
        return "validated";
    } catch (e) { /* Not validated */ }

    try {
        await fs.access(inProgressPath);
        return "in_progress";
    } catch (e) { /* Not in progress */ }

    return "source";
};

const fileExists = async (filePath: string): Promise<boolean> => {
    try {
        await fs.access(filePath);
        return true;
    } catch {
        return false;
    }
}

export const loadData = async (jsonFilename: string): Promise<any | null> => {
    const inProgressPath = path.join(IN_PROGRESS_DATA_DIR, jsonFilename);
    const validatedPath = path.join(VALIDATED_DATA_DIR, jsonFilename);
    const sourcePath = path.join(SOURCE_DATA_DIR, jsonFilename);

    let loadPath: string | null = null;
    if (await fileExists(inProgressPath)) {
        loadPath = inProgressPath;
    } else if (await fileExists(validatedPath)) {
        loadPath = validatedPath;
    } else if (await fileExists(sourcePath)) {
        loadPath = sourcePath;
    }

    if (!loadPath) {
        return null;
    }

    const fileContent = await fs.readFile(loadPath, 'utf-8');
    return JSON.parse(fileContent);
};

/**
 * Applies transformations from a delta object to a base data object.
 * @param baseData The original, unmodified data object loaded from disk.
 * @param delta The request body containing only the changes.
 * @returns A new data object with the transformations applied.
 */
export const applyTransformationsToData = (baseData: any, delta: Request['body']) => {
    // Create a deep copy to avoid mutating the original object
    const data = JSON.parse(JSON.stringify(baseData));

    const offsetX = parseFloat(delta.offsetX as string || "0");
    const offsetY = parseFloat(delta.offsetY as string || "0");
    const rotationDeg = parseFloat(delta.rotation as string || "0");
    const scale = parseFloat(delta.scale as string || "1.0");

    const isTransformed = offsetX !== 0 || offsetY !== 0 || rotationDeg !== 0 || scale !== 1.0;

    let cosRad = 1, sinRad = 0;
    const imgDims = data.image_dimensions || {};
    const cx = (imgDims.width || 0) / 2;
    const cy = (imgDims.height || 0) / 2;

    if (isTransformed) {
        const rotationRad = Math.PI / 180 * rotationDeg;
        cosRad = Math.cos(rotationRad);
        sinRad = Math.sin(rotationRad);
    }

    const allWords: { [id: string]: any } = {};
    for (const line of data.lines || []) {
        for (const word of line.words || []) {
            // Ensure ID exists for mapping
            if (word.id) {
                allWords[word.id] = word;
            }
        }
    }

    for (const [key, value] of Object.entries(delta)) {
        if (key.startsWith("text_")) {
            const wordId = key.replace("text_", "");
            if (allWords[wordId]) {
                allWords[wordId].text = value;
            }
        }
    }

    if (isTransformed) {
        for (const word of Object.values(allWords)) {
            if (!word.bounding_box) continue;
            const bbox = word.bounding_box;
            const corners = [
                { x: bbox.x_min, y: bbox.y_min },
                { x: bbox.x_max, y: bbox.y_min },
                { x: bbox.x_max, y: bbox.y_max },
                { x: bbox.x_min, y: bbox.y_max },
            ];

            const transformedCorners = corners.map(({ x, y }) => {
                const xScaled = cx + (x - cx) * scale;
                const yScaled = cy + (y - cy) * scale;
                const xRot = cx + (xScaled - cx) * cosRad - (yScaled - cy) * sinRad;
                const yRot = cy + (xScaled - cx) * sinRad + (yScaled - cy) * cosRad;
                return { x: xRot + offsetX, y: yRot + offsetY };
            });

            word.bounding_box = {
                x_min: Math.round(Math.min(...transformedCorners.map(p => p.x))),
                y_min: Math.round(Math.min(...transformedCorners.map(p => p.y))),
                x_max: Math.round(Math.max(...transformedCorners.map(p => p.x))),
                y_max: Math.round(Math.max(...transformedCorners.map(p => p.y))),
            };
        }
    }
    return data;
};
