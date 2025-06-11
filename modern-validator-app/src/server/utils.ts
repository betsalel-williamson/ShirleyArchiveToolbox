import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from 'url';
import { ParsedQs } from "qs";
import { Request } from "express";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, '..', '..');

// Directory paths
export const SOURCE_DATA_DIR = path.join(ROOT_DIR, 'data_source');
export const IN_PROGRESS_DATA_DIR = path.join(ROOT_DIR, 'data_in_progress');
export const VALIDATED_DATA_DIR = path.join(ROOT_DIR, 'data_validated');


export const getJsonFiles = async (): Promise<string[]> => {
    const sourceFiles = await fs.readdir(SOURCE_DATA_DIR);
    const inProgressFiles = await fs.readdir(IN_PROGRESS_DATA_DIR);
    const validatedFiles = await fs.readdir(VALIDATED_DATA_DIR);

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
    } catch (e) {
        // Not validated, check in progress
    }

    try {
        await fs.access(inProgressPath);
        return "in_progress";
    } catch (e) {
        // Not in progress, must be source
    }

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

// Define a type for Form Data
type FormData = { [key: string]: string | string[] | ParsedQs | ParsedQs[] | undefined }

export const applyTransformationsToData = (form: Request['body']) => {
    const data = JSON.parse(form.json_data as string);
    const offsetX = parseFloat(form.offsetX as string || "0");
    const offsetY = parseFloat(form.offsetY as string || "0");
    const rotationDeg = parseFloat(form.rotation as string || "0");
    const scale = parseFloat(form.scale as string || "1.0");

    const isTransformed = offsetX !== 0 || offsetY !== 0 || rotationDeg !== 0 || scale !== 1.0;

    let cosRad: number, sinRad: number;
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
            allWords[word.id] = word;
        }
    }

    for (const [key, value] of Object.entries(form)) {
        if (key.startsWith("text_")) {
            const wordId = key.replace("text_", "");
            if (wordId in allWords) {
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
