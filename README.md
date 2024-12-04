# assessment_evaluator

docker build . -t assessment_lambda_function
docker tag assessment_lambda_function:latest 446240042470.dkr.ecr.us-east-1.amazonaws.com/assessment-lambda-repo:latest
docker push 446240042470.dkr.ecr.us-east-1.amazonaws.com/assessment-lambda-repo:latest