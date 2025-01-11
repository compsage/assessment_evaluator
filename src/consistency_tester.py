from driver import execute_grading_pipeline
from collections import defaultdict
from typing import List, Dict, Any
import statistics

def analyze_grading_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze the consistency of grading results across multiple runs.
    
    Args:
        results (List[Dict[str, Any]]): The list of grading results to analyze
    
    Returns:
        Dict[str, Any]: The analysis results
    """
    grades = [result["grade"] for result in results]
    question_results = defaultdict(lambda: defaultdict(int))
    
    # Get max points possible for each question from first result
    question_points = {q_num: q_data["value"] for q_num, q_data in results[0]["questions"].items()}
    
    # Analyze each question"s consistency
    for result in results:
        for q_num, q_data in result["questions"].items():
            earned = q_data["value"] if q_data["correct"] else (
                q_data["value"] / 2 if q_data["partial_credit"] else 0
            )
            question_results[q_num][earned] += 1
    
    # Identify inconsistent questions with more detailed information
    inconsistent_questions = {}
    total_runs = len(results)
    
    for q_num, answers in question_results.items():
        if len(answers) > 1:  # More than one unique score means inconsistency
            max_points = question_points[q_num]
            score_details = {
                "max_points": max_points,
                "score_distribution": {
                    f"{points}/{max_points} points": {
                        "count": count,
                        "percentage": (count / total_runs) * 100
                    }
                    for points, count in answers.items()
                }
            }
            inconsistent_questions[q_num] = score_details
    
    analysis = {
        "grade_statistics": {
            "mean": statistics.mean(grades),
            "median": statistics.median(grades),
            "std_dev": statistics.stdev(grades) if len(grades) > 1 else 0,
            "min": min(grades),
            "max": max(grades),
            "all_grades": grades
        },
        "consistency_metrics": {
            "total_runs": total_runs,
            "unique_final_grades": len(set(grades)),
            "grade_range": max(grades) - min(grades),
            "is_consistent": len(set(grades)) == 1
        },
        "inconsistent_questions": inconsistent_questions
    }
    
    return analysis

def test_consistency(num_runs: int = 5) -> Dict[str, Any]:
    """
    Run the grading pipeline multiple times and analyze consistency.
    
    Args:
        num_runs (int): Number of times to run the grading pipeline
    
    Returns:
        Dict containing the analysis results
    """
    results = []
    
    for runs_index in range(num_runs):
        print(f"\nRunning Grading Pipeline {runs_index + 1} of {num_runs}...")
        runs_index, graded_quiz, runs_index = execute_grading_pipeline(
            source_image_file="data/student_assessment_images/media_0_MEc26c0f087a170ee977e9126f27c2de1a_1732593820049.jpeg",
            answer_key_file="data/transformed_answer_keys.json",
            asssessment_name="quiz 1",
            debug_mode=True
        )
        results.append(graded_quiz)
    
    analysis = analyze_grading_results(results)
    
    print("\nConsistency Analysis:")
    print(f"Number of runs: {analysis["consistency_metrics"]["total_runs"]}")
    print(f"Grade Statistics:")
    print(f"  Mean: {analysis["grade_statistics"]["mean"]:.2f}")
    print(f"  Median: {analysis["grade_statistics"]["median"]:.2f}")
    print(f"  Standard Deviation: {analysis["grade_statistics"]["std_dev"]:.2f}")
    print(f"  Range: {analysis["grade_statistics"]["min"]:.2f} - {analysis["grade_statistics"]["max"]:.2f}")
    
    if analysis["inconsistent_questions"]:
        print("\nInconsistent Questions:")
        for q_num, details in analysis["inconsistent_questions"].items():
            print(f"\n  Question {q_num} (max points: {details["max_points"]}):")
            for score, stats in details["score_distribution"].items():
                print(f"    {score}: {stats["count"]} times ({stats["percentage"]:.1f}% of runs)")
    else:
        print("\nAll questions were graded consistently across runs.")
        
    print(f"\nAnalysis: {analysis}")
    
    return analysis

if __name__ == "__main__":
    test_consistency(5)