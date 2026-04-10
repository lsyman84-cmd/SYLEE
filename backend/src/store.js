import { randomUUID } from "node:crypto";

const datasets = new Map();

export function createDataset({ sourceFileName, mailboxName, messages }) {
  const id = randomUUID();
  datasets.set(id, {
    id,
    sourceFileName,
    mailboxName,
    messages,
    createdAt: new Date().toISOString(),
  });
  return datasets.get(id);
}

export function getDataset(datasetId) {
  return datasets.get(datasetId) ?? null;
}

export function getDatasetSummary(datasetId) {
  const dataset = getDataset(datasetId);
  if (!dataset) {
    return null;
  }

  return {
    id: dataset.id,
    sourceFileName: dataset.sourceFileName,
    mailboxName: dataset.mailboxName,
    createdAt: dataset.createdAt,
    messageCount: dataset.messages.length,
  };
}
