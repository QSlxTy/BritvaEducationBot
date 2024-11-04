async def generate_progress_bar(correct_answers, total_tasks):
    max_score = 100
    progress = (correct_answers / total_tasks) * max_score
    total_blocks = 10
    filled_blocks = int(total_blocks * (progress / 100))
    empty_blocks = total_blocks - filled_blocks
    progress_bar = '|' + '🟩' * filled_blocks + '🟥' * empty_blocks + '|'
    return f"{progress_bar} {round(progress, 1)}%"
