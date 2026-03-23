#!/usr/bin/env python3
"""
Script to clear all data from the transcriptions table
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app import create_app
from app.models.transcriptionModel import TranscriptionsModel
from app.extension import db

def clear_transcriptions():
    """Clear all data from the transcriptions table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Count records before deletion
            count_before = TranscriptionsModel.query.count()
            print(f"Found {count_before} transcription records")
            
            if count_before == 0:
                print("No transcription records to delete")
                return
            
            # Confirm deletion
            confirm = input(f"Are you sure you want to delete all {count_before} transcription records? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Deletion cancelled")
                return
            
            # Delete all records
            TranscriptionsModel.query.delete()
            db.session.commit()
            
            # Verify deletion
            count_after = TranscriptionsModel.query.count()
            print(f"Successfully deleted {count_before - count_after} transcription records")
            print(f"Remaining records: {count_after}")
            
        except Exception as e:
            print(f"Error clearing transcriptions: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    clear_transcriptions()
