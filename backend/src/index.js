import express from "express";
import cors from "cors";
import multer from "multer";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parsePstFile } from "./pst.js";
import { createDataset, getDataset, getDatasetSummary } from "./store.js";
import { runQuery } from "./query.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const uploadDir = path.resolve(__dirname, "..", "uploads");
fs.mkdirSync(uploadDir, { recursive: true });

const app = express();
const upload = multer({ dest: uploadDir });
const port = Number(process.env.PORT ?? 4000);

app.use(cors());
app.use(express.json({ limit: "2mb" }));

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.post("/api/pst/upload", upload.single("pstFile"), (req, res) => {
  let uploadedPath = null;
  try {
    if (!req.file) {
      return res.status(400).json({ error: "pstFile is required." });
    }
    uploadedPath = req.file.path;
    const { mailboxName, messages } = parsePstFile(req.file.path);
    const dataset = createDataset({
      sourceFileName: req.file.originalname,
      mailboxName,
      messages,
    });

    return res.json({
      dataset: getDatasetSummary(dataset.id),
    });
  } catch (error) {
    return res.status(500).json({
      error: "Failed to parse PST file.",
      details: error instanceof Error ? error.message : String(error),
    });
  } finally {
    if (uploadedPath) {
      fs.promises.unlink(uploadedPath).catch(() => {});
    }
  }
});

app.get("/api/pst/:datasetId", (req, res) => {
  const summary = getDatasetSummary(req.params.datasetId);
  if (!summary) {
    return res.status(404).json({ error: "Dataset not found." });
  }
  return res.json({ dataset: summary });
});

app.post("/api/pst/query", (req, res) => {
  const { datasetId, question } = req.body ?? {};
  if (!datasetId || !question) {
    return res
      .status(400)
      .json({ error: "datasetId and question are required." });
  }

  const dataset = getDataset(datasetId);
  if (!dataset) {
    return res.status(404).json({ error: "Dataset not found." });
  }

  const queryResult = runQuery(dataset.messages, question);
  return res.json({
    dataset: getDatasetSummary(dataset.id),
    question,
    ...queryResult,
  });
});

app.listen(port, () => {
  console.log(`PST query backend listening on http://localhost:${port}`);
});
