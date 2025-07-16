#!/bin/bash

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('averaged_perceptron_tagger')"

# Download spaCy model
python -m spacy download en_core_web_sm

# Create necessary directories
mkdir -p data/input data/output models

echo "Setup completed successfully!" 