import os
import json
from pathlib import Path
from datetime import datetime
from werkzeug.security import generate_password_hash

from app import app, db
from models import User

def create_seed_users():
    """Create seed users if they don't exist"""
    users_data = [
        {
            'email': 'admin@phronisis.test',
            'password': 'admin123',
            'display_name': 'Admin User',
            'is_admin': True
        },
        {
            'email': 'learner@phronisis.test',
            'password': 'learn123',
            'display_name': 'Test Learner',
            'is_admin': False
        }
    ]
    
    for user_data in users_data:
        existing_user = User.query.filter_by(email=user_data['email']).first()
        if not existing_user:
            user = User(
                email=user_data['email'],
                password_hash=generate_password_hash(user_data['password']),
                display_name=user_data['display_name'],
                is_admin=user_data['is_admin'],
                created_at=datetime.utcnow()
            )
            db.session.add(user)
            print(f"Created user: {user_data['email']}")
        else:
            print(f"User already exists: {user_data['email']}")
    
    db.session.commit()

def create_seed_perspectives():
    """Create seed perspective JSON files if they don't exist"""
    content_dir = Path("content/perspectives")
    content_dir.mkdir(parents=True, exist_ok=True)
    
    # Understanding Arguments perspective
    understanding_args_file = content_dir / "understanding-arguments.json"
    if not understanding_args_file.exists():
        understanding_args = {
            "slug": "understanding-arguments",
            "title": "Understanding Arguments",
            "summary": "Learn to identify, analyze, and construct logical arguments in everyday reasoning.",
            "order": 1,
            "lessons": [
                {
                    "id": "what-is-an-argument",
                    "title": "What is an Argument?",
                    "key_ideas": [
                        "Arguments have premises and conclusions",
                        "Not all statements are arguments",
                        "Arguments aim to persuade through reasoning",
                        "Good arguments provide evidence for their claims"
                    ],
                    "examples": [
                        "Argument: 'It's raining outside, so you should bring an umbrella.'",
                        "Not an argument: 'I love pizza.' (just a statement of preference)",
                        "Argument: 'Students who study regularly perform better on tests. You want good grades, so you should study regularly.'"
                    ],
                    "quick_checks": [
                        {
                            "question": "Which of these is an argument?",
                            "choices": [
                                "The weather is nice today.",
                                "Since it's sunny, we should go to the park.",
                                "I really enjoy reading books."
                            ],
                            "answer_index": 1,
                            "feedback": [
                                "This is just a statement about the weather, not an argument.",
                                "Correct! This gives a reason (sunny weather) for a conclusion (should go to park).",
                                "This is just a personal preference, not an argument."
                            ]
                        }
                    ],
                    "minigame": {
                        "type": "choice",
                        "title": "Spot the Argument",
                        "prompt": "Look at this social media post: 'Everyone should vote because democracy depends on participation.' Is this an argument?",
                        "options": ["Yes, it's an argument", "No, it's just an opinion"],
                        "correct_option": "Yes, it's an argument",
                        "explanation": "This is an argument because it provides a reason (democracy depends on participation) to support a conclusion (everyone should vote)."
                    }
                }
            ],
            "creator_challenge": {
                "title": "Build Your Argument Detector",
                "instructions": "Think of a recent conversation or social media post where someone was trying to convince you of something. Write a short analysis identifying: 1) What they wanted you to believe (conclusion), 2) What reasons they gave (premises), and 3) Whether you found their reasoning convincing and why."
            },
            "resources": [
                {"label": "Stanford Encyclopedia: Argument", "url": "https://plato.stanford.edu/entries/argument/"},
                {"label": "Critical Thinking Web", "url": "https://www.criticalthinking.org/"}
            ]
        }
        
        with open(understanding_args_file, 'w') as f:
            json.dump(understanding_args, f, indent=2)
        print(f"Created perspective: {understanding_args_file}")
    else:
        print(f"Perspective already exists: {understanding_args_file}")
    
    # Digital Media Literacy perspective
    digital_media_file = content_dir / "digital-media-literacy.json"
    if not digital_media_file.exists():
        digital_media = {
            "slug": "digital-media-literacy",
            "title": "Digital Media Literacy",
            "summary": "Spot manipulation, verify sources, recognize AI-generated content.",
            "order": 2,
            "lessons": [
                {
                    "id": "signals-of-reliability",
                    "title": "Signals of Reliability",
                    "key_ideas": [
                        "Source transparency",
                        "Evidence and citations",
                        "Corrections and retractions policy",
                        "Understanding incentives and biases"
                    ],
                    "examples": [
                        "Opinion vs reporting side-by-side comparison",
                        "News site with a corrections page vs one without",
                        "Article with multiple sources vs single anonymous source",
                        "Sponsored content vs editorial content"
                    ],
                    "quick_checks": [
                        {
                            "question": "Which is a better first signal of reliability?",
                            "choices": [
                                "Has a professional-looking logo",
                                "Lists sources and has a corrections policy",
                                "Has lots of advertisements"
                            ],
                            "answer_index": 1,
                            "feedback": [
                                "Logos can be easily faked and don't indicate factual accuracy.",
                                "Correct — traceable evidence and accountability mechanisms matter most.",
                                "Advertisements say nothing about the quality of evidence or fact-checking."
                            ]
                        }
                    ],
                    "minigame": {
                        "type": "choice",
                        "title": "Source Radar",
                        "prompt": "You see a news snippet that cites 'government officials' but doesn't name them or link to original documents. How would you rate its reliability?",
                        "options": ["Low", "Medium", "High"],
                        "correct_option": "Medium",
                        "explanation": "This shows some transparency (citing sources) but lacks full accountability (no names or links). It's not terrible, but not ideal either."
                    }
                }
            ],
            "creator_challenge": {
                "title": "Build Your Sharing Checklist",
                "instructions": "Draft a 5-step checklist you'll use before sharing a headline or article on social media. Consider what you'll look for to verify reliability, check for bias, and avoid spreading misinformation. Submit your checklist as your artifact."
            },
            "resources": [
                {"label": "Ground News", "url": "https://ground.news"},
                {"label": "Snopes Fact Checking", "url": "https://snopes.com"},
                {"label": "AllSides Media Bias Chart", "url": "https://www.allsides.com/media-bias/media-bias-chart"}
            ]
        }
        
        with open(digital_media_file, 'w') as f:
            json.dump(digital_media, f, indent=2)
        print(f"Created perspective: {digital_media_file}")
    else:
        print(f"Perspective already exists: {digital_media_file}")

def main():
    """Run idempotent seeding"""
    with app.app_context():
        # Create tables
        db.create_all()
        print("Database tables created/verified")
        
        # Create seed users
        create_seed_users()
        
        # Create seed perspectives
        create_seed_perspectives()
        
        print("Seeding completed successfully!")

if __name__ == '__main__':
    main()
