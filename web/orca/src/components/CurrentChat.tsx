import React, { useState, useEffect } from 'react';

function CurrentChat({query}: {query: string}) {
  const [streamData, setStreamData] = useState('');

  useEffect(() => {
    const getData = async () => {
      try {
        const response = await fetch('/v1/chat', {
          method: 'POST',
          headers: {
            Accept: "application/json, text/plain, */*", // indicates which files we are able to understand
            "Content-Type": "application/json", // indicates what the server actually sent
          },
          body: JSON.stringify({
            chat_id: "1",
            query: query,
            category: "finance",
            file_name: "",
            keyword: "",
            collection_name: "test_rag_llm",
            persist_dir: "test_persist"
          }),
        });
        if (!response.ok || !response.body) {
          throw response.statusText;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const isDone = false;
        let newAnswer = "";
        while (!isDone) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }
          const decodedChunk = decoder.decode(value, { stream: true });
          newAnswer+= decodedChunk;

          setStreamData(newAnswer);
        }
      } catch (error) {
        console.error(error);
      }
    };

    getData();
  }, []);

  return (
    <pre>{streamData}</pre>
  );
}

export default CurrentChat;