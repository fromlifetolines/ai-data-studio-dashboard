import asyncio
import uuid
import json
import logging
from database import get_db_connection
from data_collectors.similarweb_client import fetch_similarweb_data
from data_collectors.semrush_client import fetch_semrush_data
from data_collectors.social_scraper import fetch_social_data
from data_collectors.geo_checker import check_geo_visibility

logger = logging.getLogger(__name__)

def add_competitor_to_db(project_id: str, name: str, domain: str, comp_type: str, is_own: bool = False) -> str:
    comp_id = str(uuid.uuid4())
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO competitors (id, project_id, name, domain, type, is_own_company) VALUES (?, ?, ?, ?, ?, ?)",
            (comp_id, project_id, name, domain, comp_type, 1 if is_own else 0)
        )
        conn.commit()
    return comp_id

async def fetch_competitor_snapshot(
    competitor_id: str,
    name: str,
    domain: str,
    industry: str,
    gemini_key: str = None,
    similarweb_key: str = None,
    semrush_key: str = None
):
    """
    Run collectors in parallel for a single competitor and insert snapshots.
    """
    # Run API calls sequentially with throttle delays to prevent hitting Gemini API free tier rate limits (5 RPM)
    similarweb = await fetch_similarweb_data(domain, similarweb_key, gemini_key)
    await asyncio.sleep(4.0)
    semrush = await fetch_semrush_data(domain, semrush_key, gemini_key)
    await asyncio.sleep(4.0)
    social = await fetch_social_data(domain, name)
    await asyncio.sleep(4.0)
    geo = await check_geo_visibility(name, industry, gemini_key)
    
    snapshot_id = str(uuid.uuid4())
    
    with get_db_connection() as conn:
        # Save Traffic snapshot
        conn.execute(
            """
            INSERT INTO traffic_snapshots (id, competitor_id, monthly_visits, bounce_rate, avg_visit_duration, traffic_sources)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                competitor_id,
                similarweb.get("monthly_visits", 0),
                similarweb.get("bounce_rate", 0.0),
                similarweb.get("avg_visit_duration", 0),
                json.dumps(similarweb.get("traffic_sources", {}))
            )
        )
        
        # Save SEO snapshot
        conn.execute(
            """
            INSERT INTO seo_snapshots (id, competitor_id, organic_keywords, organic_traffic_value, top_keywords, paid_keywords)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                competitor_id,
                semrush.get("organic_keywords", 0),
                semrush.get("organic_traffic_value", 0),
                json.dumps(semrush.get("top_keywords", [])),
                json.dumps(semrush.get("paid_keywords", []))
            )
        )
        
        # Save Social snapshot (include geo info inside top_posts or as part of social cloud metadata)
        # We save geo citation findings in top_posts or format it
        extended_social_posts = social.get("top_posts", [])
        extended_social_posts.append({
            "title": f"[AI Visibility] Mention Rate: {geo.get('mention_rate', 0)}% (Rank #{geo.get('rank', 0)})",
            "url": "AI Search Engine Citation",
            "sentiment": "positive" if geo.get("mentioned") else "neutral",
            "snippet": f"{geo.get('eval_summary')} | Reason: {geo.get('citation_reason')}"
        })
        
        conn.execute(
            """
            INSERT INTO social_snapshots (id, competitor_id, platform, post_count, positive_ratio, negative_ratio, word_cloud, top_posts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                competitor_id,
                social.get("platform", "PTT / Dcard"),
                social.get("post_count", 0),
                social.get("positive_ratio", 0.0),
                social.get("negative_ratio", 0.0),
                json.dumps(social.get("word_cloud", [])),
                json.dumps(extended_social_posts)
            )
        )
        
        conn.commit()
    
    return {
        "competitor_id": competitor_id,
        "name": name,
        "traffic": similarweb,
        "seo": semrush,
        "social": social,
        "geo": geo
    }

async def fetch_project_competitors_all(
    project_id: str,
    gemini_key: str = None,
    similarweb_key: str = None,
    semrush_key: str = None
):
    """
    Get all competitors under a project, fetch their statistics, and return results.
    """
    with get_db_connection() as conn:
        project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        industry = project["industry"] if project else "生技醫療儀器"
        competitors = conn.execute("SELECT * FROM competitors WHERE project_id = ?", (project_id,)).fetchall()
    
    if not competitors:
        return []
        
    results = []
    for c in competitors:
        res = await fetch_competitor_snapshot(
            competitor_id=c["id"],
            name=c["name"],
            domain=c["domain"],
            industry=industry,
            gemini_key=gemini_key,
            similarweb_key=similarweb_key,
            semrush_key=semrush_key
        )
        results.append(res)
        await asyncio.sleep(4.0)
    return results

def get_comparison_matrix_data(project_id: str) -> list:
    """
    Query the latest snapshot values for all competitors in a project to display in the comparison table.
    """
    with get_db_connection() as conn:
        competitors = conn.execute("SELECT * FROM competitors WHERE project_id = ?", (project_id,)).fetchall()
        matrix = []
        for c in competitors:
            # Get latest traffic snapshot
            t = conn.execute(
                "SELECT * FROM traffic_snapshots WHERE competitor_id = ? ORDER BY fetched_at DESC LIMIT 1",
                (c["id"],)
            ).fetchone()
            # Get latest seo snapshot
            s = conn.execute(
                "SELECT * FROM seo_snapshots WHERE competitor_id = ? ORDER BY fetched_at DESC LIMIT 1",
                (c["id"],)
            ).fetchone()
            # Get latest social snapshot
            soc = conn.execute(
                "SELECT * FROM social_snapshots WHERE competitor_id = ? ORDER BY fetched_at DESC LIMIT 1",
                (c["id"],)
            ).fetchone()
            
            # Format results
            sources = json.loads(t["traffic_sources"]) if (t and t["traffic_sources"]) else {}
            keywords = json.loads(s["top_keywords"]) if (s and s["top_keywords"]) else []
            ads = json.loads(s["paid_keywords"]) if (s and s["paid_keywords"]) else []
            word_cloud = json.loads(soc["word_cloud"]) if (soc and soc["word_cloud"]) else []
            posts = json.loads(soc["top_posts"]) if (soc and soc["top_posts"]) else []
            
            # Extract GEO from posts
            geo_info = {"mentioned": False, "mention_rate": 0, "rank": 0, "eval_summary": "無數據"}
            for p in posts:
                if p["url"] == "AI Search Engine Citation":
                    match = re.search(r"Mention Rate: (\d+)% \(Rank #(\d+)\)", p["title"])
                    if match:
                        geo_info = {
                            "mentioned": p["sentiment"] == "positive",
                            "mention_rate": int(match.group(1)),
                            "rank": int(match.group(2)),
                            "eval_summary": p["snippet"]
                        }
                    break
            
            matrix.append({
                "competitor_id": c["id"],
                "name": c["name"],
                "domain": c["domain"],
                "type": c["type"],
                "is_own_company": bool(c["is_own_company"]),
                "monthly_visits": t["monthly_visits"] if t else 0,
                "bounce_rate": t["bounce_rate"] if t else 0.0,
                "avg_visit_duration": t["avg_visit_duration"] if t else 0,
                "traffic_sources": sources,
                "organic_keywords": s["organic_keywords"] if s else 0,
                "organic_traffic_value": s["organic_traffic_value"] if s else 0,
                "top_keywords": keywords,
                "paid_keywords": ads,
                "social_post_count": soc["post_count"] if soc else 0,
                "positive_ratio": soc["positive_ratio"] if soc else 0.0,
                "negative_ratio": soc["negative_ratio"] if soc else 0.0,
                "word_cloud": word_cloud,
                "top_posts": posts,
                "geo": geo_info
            })
            
    return matrix

import re
