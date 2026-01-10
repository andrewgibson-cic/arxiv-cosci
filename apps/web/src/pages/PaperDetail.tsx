import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { papersApi } from '../api/client';
import { Loader2, ExternalLink, Network } from 'lucide-react';

export function PaperDetail() {
  const { arxivId } = useParams<{ arxivId: string }>();

  const { data: paper, isLoading, error } = useQuery({
    queryKey: ['paper', arxivId],
    queryFn: () => papersApi.get(arxivId!, {
      include_citations: true,
      include_references: true,
    }),
    enabled: !!arxivId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading paper...</span>
      </div>
    );
  }

  if (error || !paper) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error loading paper: {error?.message || 'Not found'}</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Paper Header */}
      <div className="bg-white p-8 rounded-lg shadow-lg mb-6">
        <h1 className="text-3xl font-bold mb-4">{paper.title}</h1>
        
        <div className="space-y-2 text-gray-600">
          <p><strong>Authors:</strong> {paper.authors.join(', ')}</p>
          <p><strong>Published:</strong> {paper.published_date}</p>
          <p><strong>Categories:</strong> {paper.categories.join(', ')}</p>
          <p><strong>arXiv ID:</strong> {paper.arxiv_id}</p>
        </div>

        <div className="flex items-center space-x-4 mt-4">
          <a
            href={`https://arxiv.org/abs/${paper.arxiv_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center space-x-1 text-blue-600 hover:text-blue-800"
          >
            <ExternalLink className="w-4 h-4" />
            <span>View on arXiv</span>
          </a>
          <a
            href={`/graph/${paper.arxiv_id}`}
            className="flex items-center space-x-1 text-green-600 hover:text-green-800"
          >
            <Network className="w-4 h-4" />
            <span>Citation Network</span>
          </a>
        </div>
      </div>

      {/* Abstract */}
      {paper.abstract && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-xl font-bold mb-3">Abstract</h2>
          <p className="text-gray-700 leading-relaxed">{paper.abstract}</p>
        </div>
      )}

      {/* TL;DR */}
      {paper.tl_dr && (
        <div className="bg-blue-50 p-4 rounded-lg mb-6">
          <h3 className="font-bold text-blue-900 mb-2">TL;DR (Semantic Scholar)</h3>
          <p className="text-blue-800">{paper.tl_dr}</p>
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {paper.citation_count !== undefined && (
          <div className="bg-white p-4 rounded-lg shadow text-center">
            <div className="text-2xl font-bold text-blue-600">{paper.citation_count}</div>
            <div className="text-sm text-gray-600">Citations</div>
          </div>
        )}
        {paper.reference_count !== undefined && (
          <div className="bg-white p-4 rounded-lg shadow text-center">
            <div className="text-2xl font-bold text-green-600">{paper.reference_count}</div>
            <div className="text-sm text-gray-600">References</div>
          </div>
        )}
        {paper.influential_citation_count !== undefined && (
          <div className="bg-white p-4 rounded-lg shadow text-center">
            <div className="text-2xl font-bold text-purple-600">{paper.influential_citation_count}</div>
            <div className="text-sm text-gray-600">Influential</div>
          </div>
        )}
      </div>

      {/* Citations */}
      {paper.citations && paper.citations.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-xl font-bold mb-4">Cited By ({paper.citations.length})</h2>
          <div className="space-y-3">
            {paper.citations.slice(0, 10).map((citing) => (
              <div key={citing.arxiv_id} className="border-l-4 border-blue-400 pl-4">
                <a
                  href={`/paper/${citing.arxiv_id}`}
                  className="font-medium text-blue-600 hover:text-blue-800"
                >
                  {citing.title}
                </a>
                <p className="text-sm text-gray-500">{citing.authors.join(', ')}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* References */}
      {paper.references && paper.references.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-bold mb-4">References ({paper.references.length})</h2>
          <div className="space-y-3">
            {paper.references.slice(0, 10).map((ref) => (
              <div key={ref.arxiv_id} className="border-l-4 border-green-400 pl-4">
                <a
                  href={`/paper/${ref.arxiv_id}`}
                  className="font-medium text-green-600 hover:text-green-800"
                >
                  {ref.title}
                </a>
                <p className="text-sm text-gray-500">{ref.authors.join(', ')}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}