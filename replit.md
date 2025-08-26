# Overview

Phronisis is a critical thinking learning application built with Flask that provides a modular content system for teaching critical thinking skills. The app features interactive lessons, peer review functionality, progress tracking, and comprehensive analytics. It uses a mobile-first design approach with a focus on accessibility and user engagement through gamified learning experiences.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Template Engine**: Jinja2 for server-side rendering
- **CSS Framework**: Bootstrap with dark theme via CDN for responsive design
- **Icons**: Feather Icons for consistent iconography
- **JavaScript**: Vanilla JS for client-side interactivity (no heavy frameworks)
- **Design Philosophy**: Mobile-first, accessible design with semantic HTML and keyboard navigation

## Backend Architecture
- **Framework**: Flask with SQLAlchemy ORM for database operations
- **Database**: SQLite for development with configurable DATABASE_URL for production
- **Authentication**: Session-based auth with password hashing using Werkzeug
- **Content System**: JSON-based modular content loaded from `/content/perspectives/` directory
- **Event Tracking**: Built-in analytics system for learning behavior monitoring

## Data Models
- **User**: Core user management with admin flags and relationships
- **Progress**: Tracks lesson completion status and scores per user/perspective/lesson
- **Artifact**: Stores user-submitted work for peer review
- **PeerReview**: Structured feedback system with rubric scoring (clarity, logic, fairness)
- **Event**: Analytics tracking for user interactions and learning patterns

## Content Architecture
- **Perspectives**: Learning modules defined in JSON files with lessons and creator challenges
- **Lessons**: Structured learning content with key ideas, examples, quick checks, and mini-games
- **Creator Challenges**: Writing prompts that generate artifacts for peer review
- **Peer Review System**: Asynchronous review queue with structured rubrics

## Security & Configuration
- **Environment Variables**: SECRET_KEY, ADMIN_CODE, DATABASE_URL via python-dotenv
- **Admin Access**: Two-tier admin system (user.is_admin flag + ADMIN_CODE for sensitive operations)
- **File Upload Security**: Secure filename handling for content uploads
- **Password Security**: Werkzeug password hashing with salt

# External Dependencies

## Core Dependencies
- **Flask**: Web framework and routing
- **SQLAlchemy**: Database ORM and migrations
- **python-dotenv**: Environment variable management
- **Werkzeug**: Security utilities and file handling

## Frontend Dependencies (CDN)
- **Bootstrap**: CSS framework with dark theme
- **Feather Icons**: Icon library for UI consistency

## Development Tools
- **SQLite**: Default database for development and testing
- **Flask Development Server**: Built-in development server with debug mode

## Deployment Considerations
- **ProxyFix**: Configured for deployment behind reverse proxies
- **Database**: Configurable via DATABASE_URL for production databases
- **Static Files**: Served via Flask in development, can be offloaded in production