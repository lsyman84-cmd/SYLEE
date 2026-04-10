import { useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { StatusBar } from "expo-status-bar";

const DEFAULT_BACKEND_URL = "http://localhost:4000";

export default function App() {
  const [backendUrl, setBackendUrl] = useState(DEFAULT_BACKEND_URL);
  const [dataset, setDataset] = useState(null);
  const [question, setQuestion] = useState("");
  const [queryResult, setQueryResult] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState("");

  const canSearch = useMemo(
    () => Boolean(dataset?.id) && question.trim().length > 0 && !isSearching,
    [dataset?.id, question, isSearching]
  );

  async function pickAndUploadPst() {
    try {
      setError("");
      setQueryResult(null);
      const picked = await DocumentPicker.getDocumentAsync({
        multiple: false,
        copyToCacheDirectory: true,
      });

      if (picked.canceled) {
        return;
      }

      const file = picked.assets?.[0];
      if (!file) {
        setError("파일을 찾을 수 없습니다. / Could not read selected file.");
        return;
      }

      setIsUploading(true);
      const form = new FormData();
      form.append("pstFile", {
        uri: file.uri,
        name: file.name || "mailbox.pst",
        type: file.mimeType || "application/octet-stream",
      });

      const response = await fetch(`${backendUrl}/api/pst/upload`, {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Upload failed");
      }
      setDataset(payload.dataset);
    } catch (uploadError) {
      setError(
        `업로드 실패 / Upload failed: ${
          uploadError instanceof Error ? uploadError.message : String(uploadError)
        }`
      );
    } finally {
      setIsUploading(false);
    }
  }

  async function submitQuery() {
    if (!canSearch) {
      return;
    }
    try {
      setError("");
      setIsSearching(true);
      const response = await fetch(`${backendUrl}/api/pst/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          datasetId: dataset.id,
          question: question.trim(),
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Search failed");
      }
      setQueryResult(payload);
    } catch (queryError) {
      setError(
        `검색 실패 / Query failed: ${
          queryError instanceof Error ? queryError.message : String(queryError)
        }`
      );
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.title}>PST 메일 질의 앱 / PST Mail Query App</Text>
        <Text style={styles.caption}>
          한글/영어로 질문하면 PST 메일에서 필요한 정보를 찾아줍니다.
        </Text>
        <Text style={styles.caption}>
          Ask in Korean or English to find emails in a PST file.
        </Text>

        <Text style={styles.label}>Backend URL</Text>
        <TextInput
          style={styles.input}
          value={backendUrl}
          onChangeText={setBackendUrl}
          autoCapitalize="none"
          autoCorrect={false}
          placeholder="http://localhost:4000"
        />
        <Text style={styles.tip}>
          Android emulator: http://10.0.2.2:4000
        </Text>

        <TouchableOpacity
          style={[styles.button, isUploading && styles.buttonDisabled]}
          onPress={pickAndUploadPst}
          disabled={isUploading}
        >
          {isUploading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>PST 파일 선택 & 업로드</Text>
          )}
        </TouchableOpacity>

        {dataset ? (
          <View style={styles.datasetBox}>
            <Text style={styles.datasetTitle}>Loaded Dataset</Text>
            <Text>File: {dataset.sourceFileName}</Text>
            <Text>Mailbox: {dataset.mailboxName}</Text>
            <Text>Messages: {dataset.messageCount}</Text>
            <Text>ID: {dataset.id}</Text>
          </View>
        ) : null}

        <Text style={styles.label}>질문 / Question</Text>
        <TextInput
          style={[styles.input, styles.queryInput]}
          value={question}
          onChangeText={setQuestion}
          placeholder={'예: 최근 "회의" 메일 찾아줘 / Show latest mail about "invoice"'}
          multiline
        />
        <TouchableOpacity
          style={[styles.button, !canSearch && styles.buttonDisabled]}
          onPress={submitQuery}
          disabled={!canSearch}
        >
          {isSearching ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>검색 / Search</Text>
          )}
        </TouchableOpacity>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        {queryResult ? (
          <View style={styles.resultBox}>
            <Text style={styles.resultTitle}>
              Result: {queryResult.intent} ({queryResult.totalMatched} matched)
            </Text>
            <Text style={styles.resultExplanation}>{queryResult.explanation}</Text>
            <FlatList
              data={queryResult.results}
              keyExtractor={(item, index) =>
                `${item.subject || "no-subject"}-${item.date || "no-date"}-${index}`
              }
              scrollEnabled={false}
              renderItem={({ item }) => (
                <View style={styles.mailItem}>
                  <Text style={styles.mailSubject}>{item.subject || "(no subject)"}</Text>
                  <Text>
                    {item.senderName} {item.senderEmail ? `<${item.senderEmail}>` : ""}
                  </Text>
                  <Text>{item.date || "unknown date"}</Text>
                  <Text numberOfLines={2}>{item.body || "(no body)"}</Text>
                </View>
              )}
              ListEmptyComponent={<Text>표시할 결과가 없습니다.</Text>}
            />
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f8f9fb",
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 32,
    gap: 10,
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    marginBottom: 4,
  },
  caption: {
    color: "#4c5764",
  },
  label: {
    marginTop: 8,
    fontWeight: "600",
  },
  input: {
    borderWidth: 1,
    borderColor: "#cfd6de",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: "#fff",
  },
  queryInput: {
    minHeight: 80,
    textAlignVertical: "top",
  },
  tip: {
    color: "#68717d",
    fontSize: 12,
  },
  button: {
    backgroundColor: "#1363df",
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
    marginTop: 6,
  },
  buttonDisabled: {
    opacity: 0.55,
  },
  buttonText: {
    color: "#fff",
    fontWeight: "700",
  },
  datasetBox: {
    marginTop: 8,
    backgroundColor: "#eef5ff",
    borderRadius: 10,
    padding: 12,
    gap: 2,
  },
  datasetTitle: {
    fontWeight: "700",
    marginBottom: 4,
  },
  error: {
    color: "#b00020",
    marginTop: 4,
  },
  resultBox: {
    marginTop: 12,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#dde3ea",
    borderRadius: 10,
    padding: 12,
  },
  resultTitle: {
    fontSize: 16,
    fontWeight: "700",
  },
  resultExplanation: {
    marginTop: 4,
    color: "#56606d",
  },
  mailItem: {
    marginTop: 10,
    borderTopWidth: 1,
    borderTopColor: "#edf1f5",
    paddingTop: 10,
    gap: 2,
  },
  mailSubject: {
    fontWeight: "700",
  },
});
