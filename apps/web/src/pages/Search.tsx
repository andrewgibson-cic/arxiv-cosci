import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { searchApi } from '../api/client';
import { Loader2 } from 'lucide-react';

export function Search() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') || '';

  const { data, isLoading, error } = useQuery({
    queryKey: ['search', query],
    queryFn: () => searchApi.semantic(query, 20),
    enabled: !!query,
  });

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">
        Search Results
        {query && <span className="text-gray-600"> for "{query}"</span>}
      </h1>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          <span className="ml-2 text-gray-600">Searching...</span>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Error: {error.message}</p>
        </div>
      )}

      {data && (
        <div>
          <p className="text-gray-600 mb-4">
            Found {data.total} results ({data.search_type} search)
          </p>

          <div className="space-y-4">
            {data.results.map((result) => (
              <div
                key={result.paper.arxiv_id}
                className="bg-white p-6 rounded-lg shadow hover:shadow-md transition"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="text-xl font-bold text-blue-600 hover:text-blue-800">
                      <a href={`/paper/${result.paper.arxiv_id}`}>
                        {result.paper.title}
                      </a>
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">
                      {result.paper.authors.join(', ')}
                    </p>
                    {result.paper.abstract && (
                      <p className="text-gray-700 mt-2 line-clamp-3">
                        {result.paper.abstract}
                      </p>
                    )}
                    <div className="flex items-center space-x-4 mt-3 text-sm text-gray-500">
                      <span>{result.paper.published_date}</span>
                      <span>{result.paper.categories.join(', ')}</span>
                      {result.paper.citation_count && (
                        <span>{result.paper.citation_count} citations</span>
                      )}
                    </div>
                  </div>
                  <div className="ml-4 text-right">
                    <div className="text-lg font-bold text-gray-700">
                      {(result.score * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-gray-500">relevance</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!query && (
        <div className="text-center py-12 text-gray-500">
          Enter a search query to find papers
        </div>
      )}
    </div>
  );
}