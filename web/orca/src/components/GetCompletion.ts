async function* getCompletion(
    prompt: string,
    chatId: string,
    signal?: AbortSignal,
  ) {
    // Same-origin relative path (nginx proxies /v1/ -> retrieval_api:8080).
    const url = new URL("/v1/chat", window.location.origin);
    url.searchParams.append("prompt", prompt);
  
    const res = await fetch(url, {
        method: "post",
        headers: {
          Accept: "application/json, text/plain, */*", // indicates which files we are able to understand
          "Content-Type": "application/json", // indicates what the server actually sent
        },
        body: JSON.stringify({
          userPrompt: prompt,
          chat_id: chatId,
          query: prompt,
          category: "Finance",
          file_name: "msft-q1-24-press_persist",
          keyword: ""
        }),
    });
  
    const reader = res.body?.getReader();
    if (!reader) throw new Error("No reader");
    const decoder = new TextDecoder();
  
    let i = 0;
    while (i < 1000) {
      i++;
      const { done, value } = await reader.read();
      if (done) return;
      const token = decoder.decode(value);
      yield token;
  
      if (signal?.aborted) {
        await reader.cancel();
        return;
      }
    }
  }
  
  export default getCompletion;