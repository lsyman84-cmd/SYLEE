import { PSTFile } from "pst-extractor";
import path from "node:path";

export function parsePstFile(filePath) {
  const pst = new PSTFile(path.resolve(filePath));
  const mailboxName = pst.getMessageStore()?.displayName ?? "Unknown mailbox";
  const root = pst.getRootFolder();
  const messages = [];
  walkFolder(root, "", messages);
  return {
    mailboxName,
    messages,
  };
}

function walkFolder(folder, folderPath, output) {
  const displayName = folder.displayName || "Root";
  const currentPath = folderPath ? `${folderPath}/${displayName}` : displayName;

  if (folder.contentCount > 0) {
    let item = folder.getNextChild();
    while (item) {
      if (typeof item.subject !== "undefined" || typeof item.body !== "undefined") {
        output.push({
          folderPath: currentPath,
          subject: safeString(item.subject),
          senderName: safeString(item.senderName),
          senderEmail: safeString(item.senderEmailAddress),
          displayTo: safeString(item.displayTo),
          body: safeString(item.body),
          date: normalizeDate(item.clientSubmitTime),
          hasAttachments: Boolean(item.hasAttachments),
        });
      }
      item = folder.getNextChild();
    }
  }

  if (folder.hasSubfolders) {
    const children = folder.getSubFolders();
    for (const child of children) {
      walkFolder(child, currentPath, output);
    }
  }
}

function normalizeDate(value) {
  if (!value) {
    return null;
  }
  const asDate = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(asDate.getTime())) {
    return null;
  }
  return asDate.toISOString();
}

function safeString(value) {
  return value == null ? "" : String(value);
}
