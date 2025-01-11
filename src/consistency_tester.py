from driver import execute_grading_pipeline
from collections import defaultdict
from typing import List, Dict, Any
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import json
from datetime import datetime
import time
import os

def analyze_grading_results(results: List[Dict[str, Any]], image_jsons: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze the consistency of grading results and student answer detection across multiple runs.
    
    Args:
        results (List[Dict[str, Any]]): The list of grading results to analyze
        image_jsons (List[Dict[str, Any]]): The list of image processing results to analyze
    
    Returns:
        Dict[str, Any]: The analysis results
    """
    # Filter out failed results
    valid_results = [r for r in results if r and "grade" in r and "questions" in r]
    valid_image_jsons = [j for j in image_jsons if j and "questions" in j]
    
    if not valid_results or not valid_image_jsons:
        return {
            "error": "No valid results to analyze",
            "total_runs": len(results),
            "valid_runs": len(valid_results),
            "failed_runs": len(results) - len(valid_results)
        }
    
    grades = [result["grade"] for result in valid_results]
    question_results = defaultdict(lambda: defaultdict(int))
    
    # Get max points possible for each question from first valid result
    question_points = {q_num: q_data["value"] for q_num, q_data in valid_results[0]["questions"].items()}
    
    # Analyze each question's consistency
    for result in valid_results:
        for q_num, q_data in result["questions"].items():
            earned = q_data["value"] if q_data["correct"] else (
                q_data["value"] / 2 if q_data["partial_credit"] else 0
            )
            question_results[q_num][earned] += 1
    
    # Analyze student answer consistency
    student_answer_results = defaultdict(lambda: defaultdict(int))
    
    # Analyze each question's student answer consistency
    for image_json in valid_image_jsons:
        for question in image_json["questions"]:
            q_num = str(question["number"])
            student_answer = question["student_answer"]
            student_answer_results[q_num][student_answer] += 1
    
    # Identify inconsistent student answers
    inconsistent_answers = {}
    total_runs = len(valid_image_jsons)
    
    for q_num, answers in student_answer_results.items():
        if len(answers) > 1:  # More than one unique answer means inconsistency
            answer_details = {
                "answer_distribution": {
                    str(answer): {
                        "count": count,
                        "percentage": (count / total_runs) * 100
                    }
                    for answer, count in answers.items()
                }
            }
            inconsistent_answers[q_num] = answer_details
    
    # Identify inconsistent questions with more detailed information
    inconsistent_questions = {}
    
    for q_num, answers in question_results.items():
        if len(answers) > 1:
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
            "is_consistent": len(set(grades)) == 1,
            "questions_with_inconsistent_answers": len(inconsistent_answers)
        },
        "inconsistent_questions": inconsistent_questions,
        "inconsistent_answers": inconsistent_answers
    }
    
    return analysis

def run_single_pipeline():
    """
    Execute a single grading pipeline run and return the results.
    
    Returns:
        tuple: (image_json, graded_quiz) or (None, None) if failed
    """
    try:
        image_json, graded_quiz, _ = execute_grading_pipeline(
            source_image_file="data/student_assessment_images/media_0_MEc26c0f087a170ee977e9126f27c2de1a_1732593820049.jpeg",
            answer_key_file="data/transformed_answer_keys.json",
            asssessment_name="quiz 1",
            debug_mode=True
        )
        
        # Validate the returned data
        if not image_json or "questions" not in image_json:
            print("Warning: Invalid image_json structure returned from pipeline")
            return None, None
            
        if not graded_quiz or "questions" not in graded_quiz:
            print("Warning: Invalid graded_quiz structure returned from pipeline")
            return None, None
            
        return image_json, graded_quiz
        
    except Exception as e:
        print(f"Error in pipeline execution: {str(e)}")
        return None, None

def test_consistency(num_runs: int = 5) -> Dict[str, Any]:
    """
    Run the grading pipeline multiple times in parallel and analyze consistency.
    
    Args:
        num_runs (int): Number of times to run the grading pipeline
    
    Returns:
        Dict containing the analysis results
    """
    start_time = time.time()
    results = []
    image_jsons = []
    failed_runs = 0
    completed_count = 0
    count_lock = Lock()
    
    # Open file for writing results
    with open("outputs/consistency_results.txt", "w") as f:
        # Write header with datetime
        f.write(f"Consistency Test Results\n")
        f.write(f"========================\n")
        f.write(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Number of Threads: {num_runs}\n")
        f.write(f"Failed Threads: 0 of {num_runs}\n\n")  # Initial count, will update later
    
    print(f"\nRunning {num_runs} Grading Pipelines in parallel...")
    
    def run_pipeline_with_counter(run_index: int):
        nonlocal completed_count
        try:
            image_json, graded_quiz = run_single_pipeline()
            with count_lock:
                completed_count += 1
                if image_json and graded_quiz:
                    print(f"Completed Grading Pipeline {completed_count} of {num_runs} (Thread {run_index})")
                    return run_index, image_json, graded_quiz
                else:
                    print(f"Pipeline {completed_count} failed to produce valid results (Thread {run_index})")
                    return run_index, None, None
        except Exception as e:
            with count_lock:
                completed_count += 1
                print(f"Pipeline {completed_count} generated an exception: {e} (Thread {run_index})")
            return run_index, None, None
    
    thread_results = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_pipeline_with_counter, i) for i in range(num_runs)]
        
        for future in futures:
            try:
                thread_index, image_json, graded_quiz = future.result()
                thread_results.append((thread_index, image_json, graded_quiz))
                if image_json and graded_quiz:
                    results.append(graded_quiz)
                    image_jsons.append(image_json)
                else:
                    failed_runs += 1
            except Exception:
                failed_runs += 1
    
    # Update the failed threads information in the file
    with open("outputs/consistency_results.txt", "r") as f:
        lines = f.readlines()
    
    # Find and update the Failed Threads line
    failed_thread_indices = [idx for idx, (_, img, quiz) in enumerate(thread_results) if img is None or quiz is None]
    for i, line in enumerate(lines):
        if line.startswith("Failed Threads:"):
            lines[i] = f"Failed Threads: {failed_runs} of {num_runs}\n"
            if failed_thread_indices:
                lines.insert(i + 1, "Failed Thread Numbers: " + ", ".join(map(str, failed_thread_indices)) + "\n")
            break
    
    # Write the updated content back to the file
    with open("outputs/consistency_results.txt", "w") as f:
        f.writelines(lines)
    
    # Calculate execution time
    execution_time = time.time() - start_time
    
    # Append execution time and results to file
    with open("outputs/consistency_results.txt", "a") as f:
        f.write(f"Total Execution Time: {execution_time:.2f} seconds\n")
        
        # Add failed threads information
        failed_thread_indices = [idx for idx, (_, img, quiz) in enumerate(thread_results) if img is None or quiz is None]
        f.write(f"Failed Threads: {failed_runs} of {num_runs}\n")
        if failed_thread_indices:
            f.write("Failed Thread Numbers: " + ", ".join(map(str, failed_thread_indices)) + "\n")
        
        f.write("\nThread Results\n")
        f.write("==============\n\n")
        
        # Write results for each thread
        for thread_index, image_json, graded_quiz in sorted(thread_results):
            f.write(f"\nThread {thread_index}\n")
            f.write("-" * (len(f"Thread {thread_index}")) + "\n")
            
            # Always write both JSON objects, even if they're None
            f.write("\nImage JSON:\n")
            f.write(json.dumps(image_json, indent=2) if image_json is not None else "None")
            
            f.write("\n\nGraded Quiz:\n")
            f.write(json.dumps(graded_quiz, indent=2) if graded_quiz is not None else "None")
            f.write("\n\n")
    
    if not results:
        print("\nError: All pipeline runs failed. No results to analyze.")
        return {
            "error": "All runs failed",
            "total_runs": num_runs,
            "failed_runs": failed_runs
        }
    
    analysis = analyze_grading_results(results, image_jsons)
    
    # Write analysis results to file
    with open("outputs/consistency_results.txt", "a") as f:
        f.write("\nAnalysis Results\n")
        f.write("===============\n")
        f.write(json.dumps(analysis, indent=2))
    
    # Update summary printing to handle potential errors
    print("\n====================================")
    print("Pipeline Execution Summary")
    print("------------------------------------")
    print(f"Number of runs: {len(results)} (Failed runs: {failed_runs})")
    print("====================================")
    
    if "error" in analysis:
        print(f"\nError: {analysis['error']}")
        return analysis
        
    print("\n====================================")
    print("Grade Statistics")
    print("------------------------------------")
    print(f"Mean: {analysis['grade_statistics']['mean']:.2f}")
    print(f"Median: {analysis['grade_statistics']['median']:.2f}")
    print(f"Standard Deviation: {analysis['grade_statistics']['std_dev']:.2f}")
    print(f"Range: {analysis['grade_statistics']['min']:.2f} - {analysis['grade_statistics']['max']:.2f}")
    print("====================================")
    
    # Print all inconsistencies or consistency message
    if not analysis["inconsistent_questions"] and not analysis["inconsistent_answers"]:
        print("\n====================================")
        print("Consistency Analysis")
        print("------------------------------------")
        print("All questions were processed consistently across runs.")
        print("====================================")
    
    # Always print OCR section
    print("\n====================================")
    print("Inconsistent Questions (OCR)")
    print("------------------------------------")
    if not analysis["inconsistent_answers"]:
        print("No OCR inconsistencies detected.")
    else:   
        is_first_question = True
        for q_num in sorted(analysis["inconsistent_answers"].keys(), key=lambda x: int(x)):
            details = analysis["inconsistent_answers"][q_num]
            if is_first_question:
                print(f"Question {q_num}:")
                is_first_question = False
            else:
                print(f"\nQuestion {q_num}:")
            sorted_answers = sorted(
                details["answer_distribution"].items(),
                key=lambda x: x[1]["percentage"],
                reverse=True
            )
            for answer, stats in sorted_answers:
                print(f"  Answer '{answer}': {stats['count']} times ({stats['percentage']:.1f}% of runs)")
    print("====================================")

    # Print grading inconsistencies section
    print("\n====================================")
    print("Inconsistent Questions (Grading)")
    print("------------------------------------")
    if not analysis["inconsistent_questions"]:
        print("No grading inconsistencies detected.")
    else:
        is_first_question = True
        for q_num in sorted(analysis["inconsistent_questions"].keys(), key=lambda x: int(x)):
            details = analysis["inconsistent_questions"][q_num]
            if is_first_question:
                print(f"Question {q_num} (max points: {details['max_points']}):")
                is_first_question = False
            else:
                print(f"\nQuestion {q_num} (max points: {details['max_points']}):")
            sorted_scores = sorted(
                details["score_distribution"].items(),
                key=lambda x: float(x[0].split('/')[0]),
                reverse=True
            )
            for score, stats in sorted_scores:
                print(f"  {score}: {stats['count']} times ({stats['percentage']:.1f}% of runs)")
    print("====================================")
    
    # Add summary metrics
    print("\n====================================")
    print("Summary Metrics")
    print("------------------------------------")
    print(f"Total Questions with OCR Inconsistencies: {len(analysis['inconsistent_answers'])}")
    print(f"Total Questions with Grading Inconsistencies: {len(analysis['inconsistent_questions'])}")
    print(f"Grade Consistency: {'Consistent' if analysis['consistency_metrics']['is_consistent'] else 'Inconsistent'}")
    print(f"Grade Range: {analysis['consistency_metrics']['grade_range']:.2f} points")
    print("====================================")
            
    return analysis

if __name__ == "__main__":
    test_consistency(20)