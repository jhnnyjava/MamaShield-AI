"""
Export metrics to CSV for pitch presentations.
Run with: python export_metrics.py
"""
import asyncio
import pandas as pd
from sqlalchemy.future import select

from database import AsyncSessionLocal, Metrics


async def export_metrics():
    """Export all metrics from database to CSV file."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Metrics))
        metrics = result.scalars().all()
        
        # Convert to list of dicts
        data = []
        for m in metrics:
            data.append({
                'id': m.id,
                'timestamp': m.timestamp,
                'event_type': m.event_type,
                'count': m.count,
                'details': str(m.details)
            })
        
        # Create DataFrame and export
        df = pd.DataFrame(data)
        df.to_csv('metrics_export.csv', index=False)
        
        print(f"✅ Exported {len(data)} metrics to metrics_export.csv")
        
        # Print summary stats
        print("\n📊 Metrics Summary:")
        print(df['event_type'].value_counts())


if __name__ == "__main__":
    asyncio.run(export_metrics())
