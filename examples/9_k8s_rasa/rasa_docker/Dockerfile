# Extend the official Rasa SDK image
FROM rasa/rasa:3.4.4

# Use subdirectory as working directory
WORKDIR /app

# Copy any additional custom requirements, if necessary (uncomment next line)
# COPY actions/requirements-actions.txt ./

# Change back to root user to install dependencies
USER root

# Install extra requirements for actions code, if necessary (uncomment next line)
# RUN pip install -r requirements-actions.txt
RUN pip install spacy
RUN python -m spacy download zh_core_web_trf

# By best practices, don't run the code with root user
USER 1001