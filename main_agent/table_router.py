"""
Table Router - Automatically selects the best partitioned table for each query type
"""

def select_best_table(user_question: str, focus_state: dict = None) -> str:
    """
    Select the optimal table based on query pattern.
    
    Args:
        user_question: The user's question in natural language
        focus_state: Optional focus state from FocusAgent with detected dimensions
        
    Returns:
        Full table name to use (e.g., 'practicode-2025.clicks_data_prac.encoded_clicks_by_app')
    """
    question_lower = user_question.lower()
    
    # Default balanced table
    default_table = "practicode-2025.clicks_data_prac.encoded_clicks_partitioned"
    
    # If focus_state provided, use it for intelligent routing
    if focus_state and isinstance(focus_state, dict):
        missing = focus_state.get("missing_fields", [])
        # If only one dimension is being asked, route to optimized table
        if len(missing) == 1:
            if "app_id" in missing:
                return "practicode-2025.clicks_data_prac.encoded_clicks_by_app"
            elif "media_source" in missing:
                return "practicode-2025.clicks_data_prac.encoded_clicks_by_media"
            elif "partner" in missing:
                return "practicode-2025.clicks_data_prac.encoded_clicks_by_partner"
            elif "site_id" in missing:
                return "practicode-2025.clicks_data_prac.encoded_clicks_by_site"
    
    # Keyword-based routing (Hebrew + English)
    
    # APP-optimized table
    app_keywords = [
        "app", "אפליקציה", "אפליקציות", "איזה אפ", "which app", "top app",
        "app performance", "ביצועי אפליקציה", "אפ הכי", "הכי טוב אפ"
    ]
    if any(keyword in question_lower for keyword in app_keywords):
        # Check if it's really app-focused (not just mentioning app)
        if "top" in question_lower or "which" in question_lower or "איזה" in question_lower or "הכי" in question_lower:
            return "practicode-2025.clicks_data_prac.encoded_clicks_by_app"
    
    # MEDIA_SOURCE-optimized table
    media_keywords = [
        "media source", "מקור מדיה", "מקורות מדיה", "traffic source", "מקור תעבורה",
        "which source", "top source", "מקור הכי", "איזה מקור"
    ]
    if any(keyword in question_lower for keyword in media_keywords):
        return "practicode-2025.clicks_data_prac.encoded_clicks_by_media"
    
    # PARTNER-optimized table
    partner_keywords = [
        "partner", "שותף", "שותפים", "agency", "סוכנות", "which partner",
        "top partner", "שותף הכי", "איזה שותף", "partner performance"
    ]
    if any(keyword in question_lower for keyword in partner_keywords):
        return "practicode-2025.clicks_data_prac.encoded_clicks_by_partner"
    
    # SITE-optimized table
    site_keywords = [
        "site", "אתר", "אתרים", "publisher", "מפרסם", "which site",
        "top site", "אתר הכי", "איזה אתר"
    ]
    if any(keyword in question_lower for keyword in site_keywords):
        return "practicode-2025.clicks_data_prac.encoded_clicks_by_site"
    
    # RETARGETING-optimized table
    retargeting_keywords = [
        "retargeting", "ריטרגטינג", "re-targeting", "retarget",
        "ua only", "רק ua", "without retarget", "בלי ריטרגטינג",
        "retargeting vs", "ua vs retargeting"
    ]
    if any(keyword in question_lower for keyword in retargeting_keywords):
        return "practicode-2025.clicks_data_prac.encoded_clicks_by_retargeting"
    
    # Default: balanced table
    return default_table


# Example usage and tests
if __name__ == "__main__":
    test_questions = [
        ("Which app had the most clicks on 2025-10-24?", "encoded_clicks_by_app"),
        ("איזה אפליקציה הכי טובה ב-24 אוקטובר?", "encoded_clicks_by_app"),
        ("Show me top media sources", "encoded_clicks_by_media"),
        ("מה המקורות מדיה הכי טובים?", "encoded_clicks_by_media"),
        ("Partner performance analysis", "encoded_clicks_by_partner"),
        ("Only retargeting traffic", "encoded_clicks_by_retargeting"),
        ("Which site had most clicks?", "encoded_clicks_by_site"),
        ("Total clicks on 2025-10-24", "encoded_clicks_partitioned"),  # general
    ]
    
    print("Testing table router:")
    print("=" * 80)
    for question, expected_suffix in test_questions:
        result = select_best_table(question)
        table_name = result.split(".")[-1]
        status = "✓" if expected_suffix in result else "✗"
        print(f"{status} {question[:50]:<50} -> {table_name}")
