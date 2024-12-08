# Use the official AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies required for Pillow
RUN yum install -y \
    gcc \
    libjpeg-devel \
    zlib-devel \
    libtiff-devel \
    libpng-devel \
    freetype-devel \
    lcms2-devel \
    libffi-devel \
    tk-devel \
    tcl-devel \
    make \
    && yum clean all

# Set up working directory
WORKDIR /var/task

# Copy your Lambda function code
COPY ../src/lambda_function.py ./lambda_function.py
COPY ../src/SourceImage.py ./SourceImage.py
COPY ../src/Processors.py ./Processors.py
COPY ../src/Evaluator.py ./Evaluator.py

# Copy additional directories and files
COPY ../prompts ./prompts

# Copy these file ins to test functionality in the cloud
COPY ../data/aggregated_answer_data.json ./data/answer_keys.json
COPY ../data/student_assessment_images/media_0_MEc26c0f087a170ee977e9126f27c2de1a_1732593820049.jpeg ./data/quiz1_sample.jpeg

# Install Python dependencies
RUN pip install pillow beautifulsoup4 twilio requests

# Set the Lambda function handler
CMD ["lambda_function.handler"]
