def build_user_friendly_answer(user_question: str, db_result):
    """
    Converts raw DB results + user question to a friendly explanation.
    """

    # 1. פתיחה
    answer = f"User question: {user_question}\n"

    # 2. אם אין תוצאות
    if not db_result or db_result == [] or db_result is None:
        answer += "Answer: No results were found for this query."
        return answer

    # 3. אם זו תוצאה מספרית יחידה
    if isinstance(db_result, dict) and len(db_result.keys()) == 1:
        key = list(db_result.keys())[0]
        value = db_result[key]
        answer += f"Answer: The {key} is {value}."
        return answer

    # 4. אם זו רשימת שורות (טבלה)
    if isinstance(db_result, list) and isinstance(db_result[0], dict):
        headers = list(db_result[0].keys())

        # בניית טבלת Markdown
        table = "| " + " | ".join(headers) + " |\n"
        table += "| " + " | ".join(["---"] * len(headers)) + " |\n"

        for row in db_result:
            row_vals = [str(row[h]) for h in headers]
            table += "| " + " | ".join(row_vals) + " |\n"

        answer += "Answer:\n" + table
        return answer

    # 5. כל דבר אחר
    answer += f"Answer: {str(db_result)}"
    return answer
