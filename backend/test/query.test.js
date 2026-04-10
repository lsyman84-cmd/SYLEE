import test from "node:test";
import assert from "node:assert/strict";
import { runQuery } from "../src/query.js";

const MESSAGES = [
  {
    subject: "Invoice April",
    senderName: "Alice",
    senderEmail: "alice@example.com",
    displayTo: "bob@example.com",
    body: "Please review April invoice.",
    date: "2026-04-01T09:00:00.000Z",
    folderPath: "Inbox",
    hasAttachments: false,
  },
  {
    subject: "프로젝트 회의 일정",
    senderName: "김철수",
    senderEmail: "chulsoo@example.com",
    displayTo: "team@example.com",
    body: "다음 주 화요일 오전 10시 회의",
    date: "2026-04-02T03:00:00.000Z",
    folderPath: "Inbox",
    hasAttachments: true,
  },
];

test("count query works in English", () => {
  const result = runQuery(MESSAGES, 'How many emails with "invoice"?');
  assert.equal(result.intent, "count");
  assert.equal(result.totalMatched, 1);
});

test("latest query works in Korean", () => {
  const result = runQuery(MESSAGES, '최근 "회의" 메일 찾아줘');
  assert.equal(result.intent, "latest");
  assert.equal(result.totalMatched, 1);
  assert.equal(result.results[0].subject, "프로젝트 회의 일정");
});

test("sender field filter works", () => {
  const result = runQuery(MESSAGES, '발신자 "alice" 메일 보여줘');
  assert.equal(result.intent, "list");
  assert.equal(result.totalMatched, 1);
  assert.equal(result.results[0].senderName, "Alice");
});
