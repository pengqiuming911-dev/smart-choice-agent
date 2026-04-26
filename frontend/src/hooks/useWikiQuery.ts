// Custom hook for wiki queries

import { useState, useCallback } from 'react';
import { queryWiki } from '@/lib/api/client';
import type { QueryResponse, SuggestionItem } from '@/types';

export function useWikiQuery() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const query = useCallback(async (question: string): Promise<QueryResponse | null> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await queryWiki(question);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed');
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { query, isLoading, error };
}