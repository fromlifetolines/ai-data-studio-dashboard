import logging

logger = logging.getLogger(__name__)

def generate_positioning_map(matrix_data: list, x_axis: str, y_axis: str) -> list:
    """
    Extract specified coordinates and sizes for all competitors to build the market positioning bubble chart.
    X-axis & Y-axis options: 'traffic' (visits), 'seo_keywords', 'social_posts', 'sentiment' (positive_ratio), 'geo_mention' (mention_rate).
    """
    points = []
    
    for c in matrix_data:
        # Resolve coordinates
        x_val = 0
        if x_axis == "traffic":
            x_val = c.get("monthly_visits", 0)
        elif x_axis == "seo_keywords":
            x_val = c.get("organic_keywords", 0)
        elif x_axis == "social_posts":
            x_val = c.get("social_post_count", 0)
        elif x_axis == "sentiment":
            x_val = round(c.get("positive_ratio", 0.0) * 100, 2)
        elif x_axis == "geo_mention":
            x_val = c.get("geo", {}).get("mention_rate", 0)
            
        y_val = 0
        if y_axis == "traffic":
            y_val = c.get("monthly_visits", 0)
        elif y_axis == "seo_keywords":
            y_val = c.get("organic_keywords", 0)
        elif y_axis == "social_posts":
            y_val = c.get("social_post_count", 0)
        elif y_axis == "sentiment":
            y_val = round(c.get("positive_ratio", 0.0) * 100, 2)
        elif y_axis == "geo_mention":
            y_val = c.get("geo", {}).get("mention_rate", 0)
            
        # Bubble size proportional to monthly visits (min size 15px, max 80px)
        max_visits = max([comp.get("monthly_visits", 0) for comp in matrix_data]) if matrix_data else 1
        max_visits = max(max_visits, 1)
        
        visits = c.get("monthly_visits", 0)
        bubble_size = round(15 + (visits / max_visits) * 65, 1)
        
        points.append({
            "name": c["name"],
            "domain": c["domain"],
            "type": c["type"],
            "is_own_company": c["is_own_company"],
            "x": x_val,
            "y": y_val,
            "size": bubble_size,
            "monthly_visits": visits
        })
        
    return points
