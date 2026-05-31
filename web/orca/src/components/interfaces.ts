export interface ChatResponse {
    response_id : string;
    type : string;
    text : string;
}

export interface ChatEntry {
    user : string,
    bot : string,
    citations : string,
    related?: string[],
    mode?: 'answer' | 'report'
}

export interface Chat {
    title: string,
    chatEntries: ChatEntry[];
}

export type ResponseChunk = {
    response_id: string;
    type: string;
    text: string;
    chat_id: string;
    metadata: {
      model: string;
      sources: any[];
    };
  };
