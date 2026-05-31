import { useCallback, useState } from "react";
import getCompletion from "./GetCompletion";

export default function useCompletion() {
  const [tokens, setTokens] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<unknown>();
  const [abortController, setAbortController] =
    useState<AbortController | null>(null);

  const mutate = useCallback(
    async (prompt: string) => {
      setIsLoading(true);
      setTokens([]);

      if (abortController) {
        abortController.abort();
      }
      const controller = new AbortController();
      const signal = controller.signal;
      setAbortController(controller);

      try {
        for await (const token of getCompletion(
          prompt,
          "1",
          signal
        )) {
          console.log("token", token);
          setTokens((prev) => [...prev, token]);
        }
      } catch (err) {
        if (
          err instanceof Error &&
          err.name === "AbortError"
        ) {
          return; // abort errors are expected
        }
        setError(err);
      }
      setIsLoading(false);
      setAbortController(null);
    },
    [abortController],
  );

  const data = tokens.join("");
  return [mutate, { data, isLoading, error }] as const;
}