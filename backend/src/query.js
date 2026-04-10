const FIELD_ALIASES = {
  subject: ["subject", "제목"],
  sender: ["sender", "from", "보낸사람", "발신자"],
  recipient: ["recipient", "to", "받는사람", "수신자"],
  body: ["body", "본문", "내용"],
  date: ["date", "날짜", "일자", "when"],
};

const ACTION_ALIASES = {
  count: ["count", "how many", "몇 개", "몇개", "개수", "수량"],
  latest: ["latest", "newest", "최근", "최신"],
  oldest: ["oldest", "earliest", "가장 오래된", "가장오래된"],
  list: ["find", "search", "show", "찾아", "검색", "보여", "목록"],
};

export function runQuery(messages, questionRaw) {
  const question = normalize(questionRaw);
  const action = detectAction(question);
  const filters = buildFilters(question);
  const filtered = messages.filter((m) => applyFilters(m, filters));

  if (action === "count") {
    return {
      intent: "count",
      totalMatched: filtered.length,
      results: [],
      explanation: `Matched ${filtered.length} message(s).`,
    };
  }

  if (action === "latest" || action === "oldest") {
    const sorted = [...filtered].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );
    const pick = action === "latest" ? sorted.at(-1) : sorted.at(0);
    return {
      intent: action,
      totalMatched: filtered.length,
      results: pick ? [pick] : [],
      explanation: pick
        ? `Returned the ${action} message in matched set.`
        : "No message matched the query.",
    };
  }

  return {
    intent: "list",
    totalMatched: filtered.length,
    results: filtered.slice(0, 30),
    explanation:
      filtered.length > 30
        ? "Showing first 30 matched messages."
        : `Showing ${filtered.length} matched message(s).`,
  };
}

function detectAction(question) {
  if (containsAny(question, ACTION_ALIASES.count)) {
    return "count";
  }
  if (containsAny(question, ACTION_ALIASES.latest)) {
    return "latest";
  }
  if (containsAny(question, ACTION_ALIASES.oldest)) {
    return "oldest";
  }
  return "list";
}

function buildFilters(question) {
  const filters = [];
  const quoted = getQuotedPhrases(question);
  if (quoted.length > 0) {
    filters.push({
      field: guessField(question),
      tokens: quoted.map(normalize),
    });
    return filters;
  }

  const keyword = extractKeyword(question);
  if (keyword) {
    filters.push({ field: guessField(question), tokens: [keyword] });
  }
  return filters;
}

function applyFilters(message, filters) {
  if (filters.length === 0) {
    return true;
  }

  return filters.every((f) => {
    const haystack = normalize(resolveField(message, f.field));
    return f.tokens.every((token) => haystack.includes(token));
  });
}

function resolveField(message, field) {
  const merged = {
    subject: message.subject ?? "",
    sender: `${message.senderName ?? ""} ${message.senderEmail ?? ""}`,
    recipient: message.displayTo ?? "",
    body: message.body ?? "",
    date: message.date ?? "",
  };

  if (!field || field === "any") {
    return Object.values(merged).join(" ");
  }
  return merged[field] ?? "";
}

function extractKeyword(question) {
  const patterns = [
    /(?:about|with|containing)\s+([a-z0-9@._\-가-힣]+)/i,
    /(?:키워드|내용)\s*[:은는이가]?\s*([a-z0-9@._\-가-힣]+)/i,
    /([a-z0-9@._\-가-힣]+)\s*(?:메일|mail|email)/i,
  ];
  for (const pattern of patterns) {
    const match = question.match(pattern);
    if (match?.[1]) {
      return normalize(match[1]);
    }
  }
  return null;
}

function guessField(question) {
  for (const [field, aliases] of Object.entries(FIELD_ALIASES)) {
    if (containsAny(question, aliases)) {
      return field;
    }
  }
  return "any";
}

function getQuotedPhrases(text) {
  const regex = /"([^"]+)"|'([^']+)'/g;
  const phrases = [];
  let match;
  while ((match = regex.exec(text)) !== null) {
    const value = match[1] || match[2];
    if (value) {
      phrases.push(value);
    }
  }
  return phrases;
}

function containsAny(text, words) {
  return words.some((w) => text.includes(normalize(w)));
}

function normalize(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}
