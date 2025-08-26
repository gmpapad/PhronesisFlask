# Phronisis - Critical Thinking Learning App

A modular web application for teaching critical thinking skills through interactive lessons, peer review, and collaborative learning.

## Features

- **Modular Content System**: Add new learning perspectives by dropping JSON files into the content folder
- **Interactive Lessons**: Key ideas, examples, quick checks, and choice-based mini-games
- **Peer Review System**: Submit artifacts and review others' work with structured rubrics
- **Progress Tracking**: Monitor learning progress across perspectives and lessons
- **Analytics**: Comprehensive event tracking for learning insights
- **Mobile-First Design**: Responsive design optimized for all devices
- **Admin Panel**: Upload new content via web interface

## Quick Start

### Local Development

1. **Install Dependencies**
   ```bash
   pip install flask flask-sqlalchemy python-dotenv werkzeug
   ```

2. **Set Up Environment**
   Create a `.env` file in the project root:
   ```
   SECRET_KEY=your-secret-key-here
   ADMIN_CODE=your-admin-code-here
   DATABASE_URL=sqlite:///phronisis.db
   