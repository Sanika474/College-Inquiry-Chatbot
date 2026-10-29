"""Standalone CLI script to run CampusIQ Knowledge Base Ingestion Pipeline."""

import sys
import os

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.chatbot.ingestion import KnowledgeIngestionPipeline


def main():
    print("===================================================================")
    print("  CampusIQ — Knowledge Base Ingestion Pipeline (JDCOEM MCA)")
    print("===================================================================")

    db = SessionLocal()
    try:
        pipeline = KnowledgeIngestionPipeline(db=db)
        print(f"Target Knowledge Base directory: {pipeline.kb_dir}")
        print("Starting ingestion scan...\n")

        summary = pipeline.run_ingestion(force_reprocess=False)

        print("\n-------------------------------------------------------------------")
        print("  Ingestion Job Summary:")
        print(f"    Job ID:                 {summary.job_id}")
        print(f"    Total Files Discovered: {summary.total_discovered}")
        print(f"    Newly Indexed:          {summary.indexed_count}")
        print(f"    Skipped (Unchanged):    {summary.skipped_count}")
        print(f"    Scanned (OCR Required): {summary.scanned_count}")
        print(f"    Failed Files:           {summary.failed_count}")
        print(f"    Total Chunks Created:   {summary.total_chunks_created}")
        print("-------------------------------------------------------------------")

        print("\nDocument Breakdown:")
        for doc in summary.document_summaries:
            status = doc.get("status", "unknown")
            fname = doc.get("filename", "")
            chunks = doc.get("chunks", 0)
            pages = doc.get("pages", 0)
            note = f" - {doc.get('note')}" if "note" in doc else ""
            print(f"  • {fname:45} | Status: {status:15} | Pages: {pages:2} | Chunks: {chunks:3}{note}")

        print("\n[SUCCESS] Knowledge Base is synchronized with PostgreSQL!")

    except Exception as e:
        print(f"\n[ERROR] Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
