#!/usr/bin/env python3
"""
Batch download and process papers using Semantic Scholar API and Gemini.

This script:
1. Fetches papers from Semantic Scholar with citations
2. Expands the network recursively
3. Analyzes papers with Gemini
4. Saves progress incrementally
5. Handles rate limiting and errors gracefully
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Set, List, Dict
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.ingestion.s2_client import S2Client
from packages.ai.factory import get_llm_client, close_client
from packages.ai.summarizer import summarize_paper
from packages.ingestion.models import ParsedPaper


class BatchCollector:
    """Collect and process papers in batches with progress tracking."""
    
    def __init__(self, target_count: int = 1000):
        self.target_count = target_count
        self.s2_client = S2Client(api_key=os.getenv("S2_API_KEY"))
        self.papers: Dict[str, dict] = {}
        self.processed_ids: Set[str] = set()
        self.to_fetch: Set[str] = set()
        self.batch_size = 50
        self.output_dir = Path("data/batch_collection")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def save_progress(self, batch_num: int):
        """Save current progress to disk."""
        progress_file = self.output_dir / f"progress_batch_{batch_num}.json"
        data = {
            "papers": list(self.papers.values()),
            "processed_ids": list(self.processed_ids),
            "to_fetch": list(self.to_fetch),
            "total_papers": len(self.papers),
            "target": self.target_count
        }
        with open(progress_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"💾 Saved progress: {len(self.papers)} papers collected")
        
    def load_progress(self) -> bool:
        """Load previous progress if exists."""
        progress_files = sorted(self.output_dir.glob("progress_batch_*.json"))
        if not progress_files:
            return False
            
        latest = progress_files[-1]
        print(f"📂 Loading progress from {latest.name}")
        
        with open(latest) as f:
            data = json.load(f)
            
        for paper in data.get("papers", []):
            self.papers[paper['id']] = paper
            
        self.processed_ids = set(data.get("processed_ids", []))
        self.to_fetch = set(data.get("to_fetch", []))
        
        print(f"✅ Loaded {len(self.papers)} papers, {len(self.to_fetch)} IDs to fetch")
        return True
        
    def extract_citations(self, paper_data: dict) -> Set[str]:
        """Extract arXiv IDs from citations and references."""
        ids = set()
        
        for citation in paper_data.get('citations', []):
            if citation.get('arxiv_id'):
                ids.add(citation['arxiv_id'])
                
        for ref in paper_data.get('references', []):
            if ref.get('arxiv_id'):
                ids.add(ref['arxiv_id'])
                
        return ids
        
    async def fetch_paper_with_citations(self, arxiv_id: str) -> dict | None:
        """Fetch a single paper with its citations and references."""
        try:
            paper = await self.s2_client.get_paper_by_arxiv_id(arxiv_id)
            if not paper:
                return None
                
            metadata = self.s2_client.paper_to_metadata(paper)
            paper_dict = metadata.model_dump()
            
            # Fetch citations and references
            citations = await self.s2_client.get_paper_citations(arxiv_id, limit=20)
            references = await self.s2_client.get_paper_references(arxiv_id, limit=20)
            
            paper_dict['citations'] = citations
            paper_dict['references'] = references
            
            return paper_dict
            
        except Exception as e:
            print(f"❌ Error fetching {arxiv_id}: {e}")
            return None
            
    async def fetch_batch(self, batch_ids: List[str], batch_num: int):
        """Fetch a batch of papers."""
        print(f"\n📥 Batch {batch_num}: Fetching {len(batch_ids)} papers...")
        
        for i, arxiv_id in enumerate(batch_ids):
            if arxiv_id in self.processed_ids:
                continue
                
            paper_data = await self.fetch_paper_with_citations(arxiv_id)
            
            if paper_data:
                self.papers[arxiv_id] = paper_data
                self.processed_ids.add(arxiv_id)
                
                # Extract new IDs to fetch
                new_ids = self.extract_citations(paper_data)
                for new_id in new_ids:
                    if new_id not in self.processed_ids and new_id not in self.papers:
                        self.to_fetch.add(new_id)
                
                if (i + 1) % 10 == 0:
                    print(f"  Progress: {i + 1}/{len(batch_ids)} papers | "
                          f"Total collected: {len(self.papers)} | "
                          f"Queue: {len(self.to_fetch)}")
                    await asyncio.sleep(1)  # Rate limiting
                    
            self.processed_ids.add(arxiv_id)  # Mark as processed even if failed
            
        self.save_progress(batch_num)
        
    async def analyze_with_gemini(self, papers: List[dict]):
        """Analyze papers with Gemini (if available)."""
        llm = get_llm_client()
        
        if not await llm.is_available():
            print("⚠️  Gemini not available, skipping AI analysis")
            return
            
        print(f"\n🧠 Analyzing {len(papers)} papers with Gemini...")
        
        for i, paper_data in enumerate(papers):
            try:
                # Create a minimal ParsedPaper for analysis
                parsed = ParsedPaper(
                    arxiv_id=paper_data['id'],
                    title=paper_data.get('title', ''),
                    abstract=paper_data.get('abstract', ''),
                    authors=paper_data.get('authors', '').split(', ') if isinstance(paper_data.get('authors'), str) else [],
                    categories=[],
                    published_date=paper_data.get('update_date', ''),
                    full_text='',
                    sections=[],
                    citations=[],
                    equations=[],
                    parser_used='s2api',
                    parse_confidence=1.0
                )
                
                summary = await summarize_paper(parsed, level="brief")
                paper_data['ai_summary'] = str(summary)
                
                if (i + 1) % 5 == 0:
                    print(f"  Analyzed: {i + 1}/{len(papers)}")
                    await asyncio.sleep(2)  # Gemini rate limiting
                    
            except Exception as e:
                print(f"❌ Error analyzing {paper_data['id']}: {e}")
                
        await close_client()
        
    async def run(self, seed_ids: List[str]):
        """Run the batch collection process."""
        print(f"🚀 Starting batch collection (target: {self.target_count} papers)")
        print(f"🌱 Seed IDs: {len(seed_ids)}")
        
        # Load previous progress if exists
        self.load_progress()
        
        # Add seed IDs to fetch queue if not already processed
        for seed_id in seed_ids:
            if seed_id not in self.processed_ids:
                self.to_fetch.add(seed_id)
        
        batch_num = 0
        start_time = time.time()
        
        while len(self.papers) < self.target_count and self.to_fetch:
            batch_num += 1
            
            # Get next batch
            batch_ids = list(self.to_fetch)[:self.batch_size]
            for bid in batch_ids:
                self.to_fetch.discard(bid)
            
            # Fetch batch
            await self.fetch_batch(batch_ids, batch_num)
            
            # Progress update
            elapsed = time.time() - start_time
            rate = len(self.papers) / elapsed if elapsed > 0 else 0
            remaining = self.target_count - len(self.papers)
            eta = remaining / rate if rate > 0 else 0
            
            print(f"\n📊 Progress Summary:")
            print(f"   Papers collected: {len(self.papers)}/{self.target_count}")
            print(f"   Queue size: {len(self.to_fetch)}")
            print(f"   Rate: {rate:.2f} papers/sec")
            print(f"   ETA: {eta/60:.1f} minutes")
            
            if len(self.papers) >= self.target_count:
                break
                
        # Final save
        final_file = self.output_dir / f"final_collection_{len(self.papers)}_papers.json"
        with open(final_file, 'w') as f:
            json.dump(list(self.papers.values()), f, indent=2)
            
        print(f"\n✅ Collection complete!")
        print(f"   Total papers: {len(self.papers)}")
        print(f"   Saved to: {final_file}")
        
        # Optionally analyze with Gemini
        if os.getenv("GEMINI_API_KEY"):
            analyze = input("\n🤔 Analyze papers with Gemini? (y/n): ")
            if analyze.lower() == 'y':
                await self.analyze_with_gemini(list(self.papers.values())[:100])  # Limit to 100 for demo
                
                # Save with analysis
                analyzed_file = self.output_dir / f"analyzed_{len(self.papers)}_papers.json"
                with open(analyzed_file, 'w') as f:
                    json.dump(list(self.papers.values()), f, indent=2)
                print(f"   Analyzed saved to: {analyzed_file}")


async def main():
    """Main entry point."""
    # Seed papers - these are the starting points
    seed_ids = [
        # Existing papers we have
        "2309.08743", "2310.12345", "2311.18805", "2312.09876", "2401.12345",
        # Additional quantum computing / ML papers
        "2401.00001", "2401.00002", "2401.00003", "2401.00004", "2401.00005",
        "2402.00001", "2402.00002", "2403.00001", "2403.00002", "2404.00001"
    ]
    
    collector = BatchCollector(target_count=1000)
    await collector.run(seed_ids)


if __name__ == "__main__":
    print("=" * 70)
    print(" ArXiv AI Co-Scientist - Batch Paper Collection")
    print("=" * 70)
    print()
    
    asyncio.run(main())